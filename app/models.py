"""Pydantic response models exposed through OpenAPI."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AccountStatus = Literal["ok", "error", "updating", "suspended", "unknown"]


class HoldingSummary(BaseModel):
    name: str
    code: str | None = None
    type: str = Field(description="Normalized holding type, such as stock or investment_trust.")
    amount: int = Field(description="Current JPY valuation.")
    quantity: float | None = None
    unit_price: int | None = Field(default=None, description="Current JPY unit price when present.")
    average_cost: int | None = Field(
        default=None,
        description="Average JPY acquisition unit price from avg_cost_price when present.",
    )
    unrealized_gain: int | None = Field(default=None, description="Unrealized JPY gain or loss.")
    unrealized_gain_pct: float | None = None
    raw_category: str | None = Field(
        default=None,
        description="Original Money Forward asset or liability category.",
    )


class AccountSummary(BaseModel):
    institution: str | None
    account: str | None
    total: int = Field(description="Sum of holdings in this response category, in JPY.")
    last_updated_at: str | None = Field(
        default=None,
        description="Money Forward account update date or datetime, as stored in SQLite.",
    )
    status: AccountStatus
    raw_institution_category: str | None = None
    holdings: list[HoldingSummary] = Field(default_factory=list)


class CategorySummary(BaseModel):
    total: int
    accounts: list[AccountSummary] = Field(default_factory=list)


class AccountSyncStatus(BaseModel):
    institution: str | None
    account: str
    last_updated_at: str | None = None
    status: AccountStatus


class SyncSummary(BaseModel):
    last_scraped_at: str | None = Field(
        default=None,
        description="Crawler completion timestamp stored on the no-group record.",
    )
    refresh_completed: bool | None = Field(
        description="Value stored in daily_snapshots.refresh_completed; null means unknown."
    )
    incomplete_accounts: list[str] = Field(
        default_factory=list,
        description="Active accounts whose stored status is not ok.",
    )
    accounts: list[AccountSyncStatus] = Field(
        default_factory=list,
        description="Stored refresh state for every active Money Forward account.",
    )


class Totals(BaseModel):
    assets: int = Field(
        description="Official latest total from asset_history.total_assets, in JPY."
    )
    liabilities: int = Field(description="Sum of latest liability holding values, in JPY.")
    net_worth: int = Field(description="assets minus liabilities, in JPY.")


class FinancialSummary(BaseModel):
    as_of: str = Field(description="Timestamp of the SQLite snapshot represented by this response.")
    sync: SyncSummary
    totals: Totals
    cash: CategorySummary
    securities: CategorySummary
    pension: CategorySummary
    insurance: CategorySummary
    points: CategorySummary
    other_assets: CategorySummary
    liabilities: CategorySummary


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
