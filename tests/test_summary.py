import sqlite3

from app.repository import SqliteSummaryRepository
from app.service import build_financial_summary


def load_summary(financial_db):
    data = SqliteSummaryRepository().load(financial_db)
    return build_financial_summary(data)


def test_summary_totals(financial_db):
    summary = load_summary(financial_db)

    assert summary.totals.assets == 400000
    assert summary.totals.liabilities == 50000
    assert summary.totals.net_worth == 350000


def test_cash_accounts_are_transformed(financial_db):
    summary = load_summary(financial_db)

    assert summary.cash.total == 100000
    assert len(summary.cash.accounts) == 1
    account = summary.cash.accounts[0]
    assert account.institution == "Test Bank"
    assert account.account == "Test Bank"
    assert account.total == 100000
    assert account.status == "ok"
    assert account.holdings[0].raw_category == "預金・現金"


def test_securities_and_holdings_are_transformed(financial_db):
    summary = load_summary(financial_db)

    assert summary.securities.total == 300000
    assert len(summary.securities.accounts) == 1
    holdings = {holding.name: holding for holding in summary.securities.accounts[0].holdings}
    stock = holdings["Example Stock"]
    assert stock.type == "stock"
    assert stock.code == "1234"
    assert stock.amount == 180000
    assert stock.quantity == 10
    assert stock.unit_price == 18000
    assert stock.average_cost == 15000
    assert stock.unrealized_gain == 30000
    assert stock.unrealized_gain_pct == 20.0
    assert holdings["Example Fund"].type == "investment_trust"


def test_liabilities_are_transformed(financial_db):
    summary = load_summary(financial_db)

    assert summary.liabilities.total == 50000
    account = summary.liabilities.accounts[0]
    assert account.institution == "Test Card"
    assert account.status == "error"
    assert account.holdings[0].type == "liability"
    assert account.holdings[0].raw_category == "カード"


def test_null_values_remain_null(financial_db):
    summary = load_summary(financial_db)

    fund = next(
        holding
        for holding in summary.securities.accounts[0].holdings
        if holding.name == "Example Fund"
    )
    assert fund.code is None
    assert fund.quantity is None
    assert fund.unit_price is None
    assert fund.average_cost is None
    assert fund.unrealized_gain is None
    assert fund.unrealized_gain_pct is None


def test_zero_values_are_not_changed_to_null(financial_db):
    connection = sqlite3.connect(financial_db)
    connection.execute(
        """
        UPDATE holding_values
        SET unit_price = 0, avg_cost_price = 0, unrealized_gain = 0, unrealized_gain_pct = 0
        WHERE holding_id = 103
        """
    )
    connection.commit()
    connection.close()

    summary = load_summary(financial_db)
    fund = next(
        holding
        for holding in summary.securities.accounts[0].holdings
        if holding.name == "Example Fund"
    )
    assert fund.unit_price == 0
    assert fund.average_cost == 0
    assert fund.unrealized_gain == 0
    assert fund.unrealized_gain_pct == 0


def test_unclassified_assets_are_preserved_in_other_assets(financial_db):
    connection = sqlite3.connect(financial_db)
    connection.execute("INSERT INTO asset_categories VALUES (4, '貴金属')")
    connection.execute(
        "INSERT INTO holdings VALUES (105, 2, 4, 'Example Gold', NULL, 'asset', NULL)"
    )
    connection.execute(
        "INSERT INTO holding_values VALUES (105, 10, 25000, NULL, NULL, NULL, NULL, NULL)"
    )
    connection.execute("UPDATE asset_history SET total_assets = 425000 WHERE id = 20")
    connection.commit()
    connection.close()

    summary = load_summary(financial_db)

    assert summary.other_assets.total == 25000
    gold = summary.other_assets.accounts[0].holdings[0]
    assert gold.name == "Example Gold"
    assert gold.type == "other_asset"
    assert gold.raw_category == "貴金属"


def test_sync_uses_snapshot_and_account_statuses(financial_db):
    summary = load_summary(financial_db)

    assert summary.sync.refresh_completed is False
    assert summary.sync.incomplete_accounts == ["Test Card"]
    card = next(account for account in summary.sync.accounts if account.account == "Test Card")
    assert card.status == "error"
    assert not hasattr(card, "error_message")
