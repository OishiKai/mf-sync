"""Financial summary transformation and aggregation."""

from __future__ import annotations

import logging
import math
import time
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Protocol

from app.errors import DatabaseReadError, MfSyncError
from app.models import (
    AccountSummary,
    AccountSyncStatus,
    CategorySummary,
    FinancialSummary,
    HoldingSummary,
    SyncSummary,
    Totals,
)
from app.repository import HoldingRecord, SqliteSummaryRepository, SummaryData

logger = logging.getLogger(__name__)

CASH_CATEGORIES = {"預金・現金", "電子マネー・プリペイド"}
SECURITIES_CATEGORIES = {
    "株式(現物)",
    "株式",
    "投資信託",
    "ETF",
    "債券",
    "FX",
    "先物",
}
PENSION_CATEGORIES = {"年金"}
INSURANCE_CATEGORIES = {"保険"}
POINT_CATEGORIES = {"ポイント・マイル", "ポイント"}

NORMALIZED_HOLDING_TYPES = {
    "預金・現金": "cash",
    "電子マネー・プリペイド": "electronic_money",
    "株式(現物)": "stock",
    "株式": "stock",
    "投資信託": "investment_trust",
    "ETF": "etf",
    "債券": "bond",
    "FX": "fx",
    "先物": "futures",
    "暗号資産": "crypto_asset",
    "暗号資産・FX・貴金属": "crypto_fx_precious_metal",
    "保険": "insurance",
    "年金": "pension",
    "ポイント・マイル": "points",
    "ポイント": "points",
}


class DatabaseCache(Protocol):
    def ensure_current(self) -> Path: ...


def _jpy(value: float | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        raise DatabaseReadError("Non-finite monetary value")
    try:
        return int(Decimal(str(value)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError) as exc:
        raise DatabaseReadError("Invalid monetary value") from exc


def _bucket_for(holding: HoldingRecord) -> str:
    if holding.holding_type == "liability":
        return "liabilities"
    if holding.holding_type != "asset":
        raise DatabaseReadError("Unknown holding type")

    raw_category = holding.raw_category
    if raw_category in CASH_CATEGORIES:
        return "cash"
    if raw_category in SECURITIES_CATEGORIES:
        return "securities"
    if raw_category in PENSION_CATEGORIES:
        return "pension"
    if raw_category in INSURANCE_CATEGORIES:
        return "insurance"
    if raw_category in POINT_CATEGORIES:
        return "points"
    return "other_assets"


def _holding_model(holding: HoldingRecord) -> HoldingSummary:
    raw_category = (
        holding.liability_category if holding.holding_type == "liability" else holding.raw_category
    )
    normalized_type = (
        "liability"
        if holding.holding_type == "liability"
        else NORMALIZED_HOLDING_TYPES.get(holding.raw_category or "", "other_asset")
    )
    amount = _jpy(holding.amount)
    if amount is None:
        raise DatabaseReadError("Holding amount is missing")

    return HoldingSummary(
        name=holding.name,
        code=holding.code,
        type=normalized_type,
        amount=amount,
        quantity=holding.quantity,
        unit_price=_jpy(holding.unit_price),
        average_cost=_jpy(holding.avg_cost_price),
        unrealized_gain=_jpy(holding.unrealized_gain),
        unrealized_gain_pct=holding.unrealized_gain_pct,
        raw_category=raw_category,
    )


def _category_models(data: SummaryData) -> dict[str, CategorySummary]:
    grouped: dict[tuple[str, int], list[HoldingRecord]] = {}
    for holding in data.holdings:
        grouped.setdefault((_bucket_for(holding), holding.account_id), []).append(holding)

    categories: dict[str, list[AccountSummary]] = {
        "cash": [],
        "securities": [],
        "pension": [],
        "insurance": [],
        "points": [],
        "other_assets": [],
        "liabilities": [],
    }
    accounts_by_id = {account.id: account for account in data.accounts}

    for (bucket, account_id), holdings in grouped.items():
        account = accounts_by_id.get(account_id)
        first = holdings[0]
        is_unknown_account = first.account_mf_id == "unknown"
        holding_models = [_holding_model(holding) for holding in holdings]
        holding_models.sort(key=lambda item: (-item.amount, item.name))
        total = sum(item.amount for item in holding_models)

        categories[bucket].append(
            AccountSummary(
                institution=None if is_unknown_account else first.institution,
                account=None if is_unknown_account else first.account_name,
                total=total,
                last_updated_at=(account.last_updated if account else first.account_last_updated),
                status=(account.status if account else first.account_status),
                raw_institution_category=(
                    account.institution_category if account else first.institution_category
                ),
                holdings=holding_models,
            )
        )

    result: dict[str, CategorySummary] = {}
    for bucket, accounts in categories.items():
        accounts.sort(key=lambda item: (-item.total, item.institution or "", item.account or ""))
        result[bucket] = CategorySummary(
            total=sum(account.total for account in accounts),
            accounts=accounts,
        )
    return result


def _sync_model(data: SummaryData) -> SyncSummary:
    accounts = [
        AccountSyncStatus(
            institution=account.institution,
            account=account.name,
            last_updated_at=account.last_updated,
            status=account.status,
            error_message=account.error_message,
        )
        for account in data.accounts
    ]
    accounts.sort(key=lambda item: (item.institution or "", item.account))
    incomplete_accounts = sorted(
        {account.name for account in data.accounts if account.status != "ok"}
    )
    return SyncSummary(
        last_scraped_at=data.last_scraped_at,
        refresh_completed=data.snapshot.refresh_completed,
        incomplete_accounts=incomplete_accounts,
        accounts=accounts,
    )


def build_financial_summary(data: SummaryData) -> FinancialSummary:
    categories = _category_models(data)
    liabilities = categories["liabilities"].total
    assets = _jpy(data.official_assets)
    if assets is None:
        raise DatabaseReadError("Official asset total is missing")

    return FinancialSummary(
        as_of=data.last_scraped_at or data.snapshot.created_at,
        sync=_sync_model(data),
        totals=Totals(
            assets=assets,
            liabilities=liabilities,
            net_worth=assets - liabilities,
        ),
        cash=categories["cash"],
        securities=categories["securities"],
        pension=categories["pension"],
        insurance=categories["insurance"],
        points=categories["points"],
        other_assets=categories["other_assets"],
        liabilities=categories["liabilities"],
    )


class FinancialSummaryService:
    def __init__(
        self,
        cache: DatabaseCache,
        repository: SqliteSummaryRepository | None = None,
    ) -> None:
        self._cache = cache
        self._repository = repository or SqliteSummaryRepository()

    def get_summary(self) -> FinancialSummary:
        start = time.perf_counter()
        try:
            db_path = self._cache.ensure_current()
            data = self._repository.load(db_path)
            summary = build_financial_summary(data)
        except MfSyncError:
            raise
        except (TypeError, ValueError) as exc:
            raise DatabaseReadError("Snapshot data validation failed") from exc
        duration_ms = round((time.perf_counter() - start) * 1000)
        logger.info("summary generated duration_ms=%s", duration_ms)
        return summary
