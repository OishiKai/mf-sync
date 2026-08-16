"""Read-only access to the current mf-dashboard SQLite schema."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.errors import DatabaseReadError, RequiredDataMissingError

NO_GROUP_ID = "0"

REQUIRED_SCHEMA: dict[str, set[str]] = {
    "groups": {"id", "last_scraped_at"},
    "group_accounts": {"group_id", "account_id"},
    "accounts": {"id", "mf_id", "name", "institution", "category_id", "is_active"},
    "institution_categories": {"id", "name"},
    "account_statuses": {
        "account_id",
        "status",
        "last_updated",
    },
    "holdings": {
        "id",
        "account_id",
        "category_id",
        "name",
        "code",
        "type",
        "liability_category",
    },
    "asset_categories": {"id", "name"},
    "daily_snapshots": {
        "id",
        "group_id",
        "date",
        "refresh_completed",
        "created_at",
    },
    "holding_values": {
        "holding_id",
        "snapshot_id",
        "amount",
        "quantity",
        "unit_price",
        "avg_cost_price",
        "unrealized_gain",
        "unrealized_gain_pct",
    },
    "asset_history": {"id", "group_id", "date", "total_assets"},
}

VALID_ACCOUNT_STATUSES = {"ok", "error", "updating", "suspended", "unknown"}


@dataclass(frozen=True, slots=True)
class SnapshotRecord:
    id: int
    date: str
    refresh_completed: bool | None
    created_at: str


@dataclass(frozen=True, slots=True)
class AccountRecord:
    id: int
    mf_id: str
    name: str
    institution: str | None
    institution_category: str | None
    status: str
    last_updated: str | None


@dataclass(frozen=True, slots=True)
class HoldingRecord:
    id: int
    account_id: int
    account_mf_id: str
    account_name: str
    institution: str | None
    institution_category: str | None
    account_status: str
    account_last_updated: str | None
    name: str
    code: str | None
    holding_type: str
    raw_category: str | None
    liability_category: str | None
    amount: int | float
    quantity: float | None
    unit_price: int | float | None
    avg_cost_price: int | float | None
    unrealized_gain: int | float | None
    unrealized_gain_pct: float | None


@dataclass(frozen=True, slots=True)
class SummaryData:
    snapshot: SnapshotRecord
    last_scraped_at: str | None
    official_assets: int
    accounts: tuple[AccountRecord, ...]
    holdings: tuple[HoldingRecord, ...]


class SqliteSummaryRepository:
    """Loads a single, consistent snapshot using fixed read-only SQL."""

    def load(self, db_path: Path) -> SummaryData:
        connection: sqlite3.Connection | None = None
        try:
            uri = f"{db_path.resolve().as_uri()}?mode=ro&immutable=1"
            connection = sqlite3.connect(uri, uri=True, timeout=5)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")
            self._validate_schema(connection)

            group = connection.execute(
                "SELECT id, last_scraped_at FROM groups WHERE id = ? LIMIT 1",
                (NO_GROUP_ID,),
            ).fetchone()
            if group is None:
                raise RequiredDataMissingError("No no-group record exists")

            snapshot_row = connection.execute(
                """
                SELECT id, date, refresh_completed, created_at
                FROM daily_snapshots
                WHERE group_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (NO_GROUP_ID,),
            ).fetchone()
            if snapshot_row is None:
                raise RequiredDataMissingError("No current snapshot exists")

            assets_row = connection.execute(
                """
                SELECT total_assets
                FROM asset_history
                WHERE group_id = ?
                ORDER BY date DESC, id DESC
                LIMIT 1
                """,
                (NO_GROUP_ID,),
            ).fetchone()
            if assets_row is None:
                raise RequiredDataMissingError("No official asset total exists")

            account_rows = connection.execute(
                """
                SELECT
                    a.id,
                    a.mf_id,
                    a.name,
                    a.institution,
                    ic.name AS institution_category,
                    s.status,
                    s.last_updated
                FROM group_accounts AS ga
                JOIN accounts AS a ON a.id = ga.account_id
                LEFT JOIN institution_categories AS ic ON ic.id = a.category_id
                LEFT JOIN account_statuses AS s ON s.account_id = a.id
                WHERE ga.group_id = ?
                  AND a.is_active = 1
                  AND a.mf_id != 'unknown'
                ORDER BY a.id
                """,
                (NO_GROUP_ID,),
            ).fetchall()

            holding_rows = connection.execute(
                """
                SELECT
                    h.id,
                    h.account_id,
                    a.mf_id AS account_mf_id,
                    a.name AS account_name,
                    a.institution,
                    ic.name AS institution_category,
                    s.status AS account_status,
                    s.last_updated AS account_last_updated,
                    h.name,
                    h.code,
                    h.type AS holding_type,
                    ac.name AS raw_category,
                    h.liability_category,
                    v.amount,
                    v.quantity,
                    v.unit_price,
                    v.avg_cost_price,
                    v.unrealized_gain,
                    v.unrealized_gain_pct
                FROM holding_values AS v
                JOIN holdings AS h ON h.id = v.holding_id
                JOIN accounts AS a ON a.id = h.account_id
                LEFT JOIN asset_categories AS ac ON ac.id = h.category_id
                LEFT JOIN institution_categories AS ic ON ic.id = a.category_id
                LEFT JOIN account_statuses AS s ON s.account_id = a.id
                WHERE v.snapshot_id = ?
                ORDER BY h.type, h.account_id, h.id
                """,
                (snapshot_row["id"],),
            ).fetchall()

            snapshot = SnapshotRecord(
                id=snapshot_row["id"],
                date=snapshot_row["date"],
                refresh_completed=(
                    bool(snapshot_row["refresh_completed"])
                    if snapshot_row["refresh_completed"] is not None
                    else None
                ),
                created_at=snapshot_row["created_at"],
            )
            accounts = tuple(self._account_from_row(row) for row in account_rows)
            holdings = tuple(self._holding_from_row(row) for row in holding_rows)
            official_assets = int(assets_row["total_assets"])
            if official_assets != 0 and not any(
                holding.holding_type == "asset" for holding in holdings
            ):
                raise RequiredDataMissingError("Asset holdings are missing from the snapshot")

            return SummaryData(
                snapshot=snapshot,
                last_scraped_at=group["last_scraped_at"],
                official_assets=official_assets,
                accounts=accounts,
                holdings=holdings,
            )
        except RequiredDataMissingError:
            raise
        except (sqlite3.Error, OSError, TypeError, ValueError) as exc:
            raise DatabaseReadError("SQLite read failed") from exc
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def _validate_schema(connection: sqlite3.Connection) -> None:
        table_rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        available_tables = {row["name"] for row in table_rows}

        for table, required_columns in REQUIRED_SCHEMA.items():
            if table not in available_tables:
                raise RequiredDataMissingError(f"Required table is missing: {table}")
            column_rows = connection.execute(f'PRAGMA table_info("{table}")').fetchall()
            available_columns = {row["name"] for row in column_rows}
            if not required_columns.issubset(available_columns):
                raise RequiredDataMissingError(f"Required columns are missing from: {table}")

    @staticmethod
    def _normalize_status(value: str | None) -> str:
        return value if value in VALID_ACCOUNT_STATUSES else "unknown"

    @classmethod
    def _account_from_row(cls, row: sqlite3.Row) -> AccountRecord:
        return AccountRecord(
            id=row["id"],
            mf_id=row["mf_id"],
            name=row["name"],
            institution=row["institution"],
            institution_category=row["institution_category"],
            status=cls._normalize_status(row["status"]),
            last_updated=row["last_updated"],
        )

    @classmethod
    def _holding_from_row(cls, row: sqlite3.Row) -> HoldingRecord:
        return HoldingRecord(
            id=row["id"],
            account_id=row["account_id"],
            account_mf_id=row["account_mf_id"],
            account_name=row["account_name"],
            institution=row["institution"],
            institution_category=row["institution_category"],
            account_status=cls._normalize_status(row["account_status"]),
            account_last_updated=row["account_last_updated"],
            name=row["name"],
            code=row["code"],
            holding_type=row["holding_type"],
            raw_category=row["raw_category"],
            liability_category=row["liability_category"],
            amount=row["amount"],
            quantity=row["quantity"],
            unit_price=row["unit_price"],
            avg_cost_price=row["avg_cost_price"],
            unrealized_gain=row["unrealized_gain"],
            unrealized_gain_pct=row["unrealized_gain_pct"],
        )
