from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

SCHEMA = """
CREATE TABLE groups (
    id TEXT PRIMARY KEY,
    last_scraped_at TEXT
);
CREATE TABLE institution_categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY,
    mf_id TEXT NOT NULL,
    name TEXT NOT NULL,
    institution TEXT,
    category_id INTEGER,
    is_active INTEGER
);
CREATE TABLE group_accounts (
    group_id TEXT NOT NULL,
    account_id INTEGER NOT NULL
);
CREATE TABLE account_statuses (
    account_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    last_updated TEXT,
    error_message TEXT
);
CREATE TABLE asset_categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE holdings (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL,
    category_id INTEGER,
    name TEXT NOT NULL,
    code TEXT,
    type TEXT NOT NULL,
    liability_category TEXT
);
CREATE TABLE daily_snapshots (
    id INTEGER PRIMARY KEY,
    group_id TEXT NOT NULL,
    date TEXT NOT NULL,
    refresh_completed INTEGER,
    created_at TEXT NOT NULL
);
CREATE TABLE holding_values (
    holding_id INTEGER NOT NULL,
    snapshot_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    quantity REAL,
    unit_price REAL,
    avg_cost_price REAL,
    unrealized_gain INTEGER,
    unrealized_gain_pct REAL
);
CREATE TABLE asset_history (
    id INTEGER PRIMARY KEY,
    group_id TEXT NOT NULL,
    date TEXT NOT NULL,
    total_assets INTEGER NOT NULL
);
"""


@pytest.fixture
def financial_db(tmp_path: Path) -> Path:
    path = tmp_path / "moneyforward.db"
    connection = sqlite3.connect(path)
    connection.executescript(SCHEMA)
    connection.executescript(
        """
        INSERT INTO groups VALUES ('0', '2026-08-15T13:05:00.000Z');

        INSERT INTO institution_categories VALUES (1, '銀行');
        INSERT INTO institution_categories VALUES (2, '証券');
        INSERT INTO institution_categories VALUES (3, 'カード');

        INSERT INTO accounts VALUES (1, 'bank-a', 'Test Bank', 'Test Bank', 1, 1);
        INSERT INTO accounts VALUES (2, 'broker-a', 'Test Securities', 'Test Securities', 2, 1);
        INSERT INTO accounts VALUES (3, 'card-a', 'Test Card', 'Test Card', 3, 1);

        INSERT INTO group_accounts VALUES ('0', 1);
        INSERT INTO group_accounts VALUES ('0', 2);
        INSERT INTO group_accounts VALUES ('0', 3);

        INSERT INTO account_statuses VALUES (1, 'ok', '2026-08-15', NULL);
        INSERT INTO account_statuses VALUES (2, 'ok', '2026-08-15', NULL);
        INSERT INTO account_statuses VALUES (3, 'error', '2026-08-14', 'Authentication required');

        INSERT INTO asset_categories VALUES (1, '預金・現金');
        INSERT INTO asset_categories VALUES (2, '株式(現物)');
        INSERT INTO asset_categories VALUES (3, '投資信託');

        INSERT INTO daily_snapshots
            VALUES (10, '0', '2026-08-15', 0, '2026-08-15T13:04:59.000Z');
        INSERT INTO asset_history VALUES (20, '0', '2026-08-15', 400000);

        INSERT INTO holdings VALUES (101, 1, 1, 'Ordinary Deposit', NULL, 'asset', NULL);
        INSERT INTO holdings VALUES (102, 2, 2, 'Example Stock', '1234', 'asset', NULL);
        INSERT INTO holdings VALUES (103, 2, 3, 'Example Fund', NULL, 'asset', NULL);
        INSERT INTO holdings VALUES (104, 3, NULL, 'Card Balance', NULL, 'liability', 'カード');

        INSERT INTO holding_values VALUES
            (101, 10, 100000, NULL, NULL, NULL, NULL, NULL);
        INSERT INTO holding_values VALUES
            (102, 10, 180000, 10, 18000, 15000, 30000, 20.0);
        INSERT INTO holding_values VALUES
            (103, 10, 120000, NULL, NULL, NULL, NULL, NULL);
        INSERT INTO holding_values VALUES
            (104, 10, 50000, NULL, NULL, NULL, NULL, NULL);
        """
    )
    connection.commit()
    connection.close()
    return path
