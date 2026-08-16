import sqlite3

from fastapi.testclient import TestClient

from app.config import Settings
from app.errors import DatabaseDownloadError
from app.main import create_app


class StaticCache:
    def __init__(self, path):
        self.path = path

    def ensure_current(self):
        return self.path


def make_client(financial_db):
    settings = Settings(
        api_key="test-secret",
        gcs_bucket="test-bucket",
        gcs_db_object="moneyforward.db",
        local_db_path=financial_db,
    )
    return TestClient(create_app(settings=settings, cache=StaticCache(financial_db)))


def test_api_key_missing_returns_401(financial_db):
    response = make_client(financial_db).get("/v1/summary")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_api_key_invalid_returns_401(financial_db):
    response = make_client(financial_db).get(
        "/v1/summary", headers={"Authorization": "Bearer wrong-secret"}
    )

    assert response.status_code == 401


def test_correct_api_key_returns_200(financial_db):
    response = make_client(financial_db).get(
        "/v1/summary", headers={"Authorization": "Bearer test-secret"}
    )

    assert response.status_code == 200
    assert response.json()["as_of"] == "2026-08-15T13:05:00.000Z"


def test_openapi_uses_custom_gpt_operation_id(financial_db):
    schema = make_client(financial_db).app.openapi()

    operation = schema["paths"]["/v1/summary"]["get"]
    assert operation["operationId"] == "getFinancialSummary"


def test_production_documentation_routes_are_disabled(financial_db):
    client = make_client(financial_db)

    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404


def test_health_check_is_public_and_data_free():
    response = TestClient(create_app()).get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_financial_response_disables_caching(financial_db):
    response = make_client(financial_db).get(
        "/v1/summary", headers={"Authorization": "Bearer test-secret"}
    )

    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_invalid_authentication_is_rate_limited(financial_db):
    settings = Settings(
        api_key="test-secret",
        gcs_bucket="test-bucket",
        local_db_path=financial_db,
        unauthorized_rate_limit=2,
    )
    client = TestClient(create_app(settings=settings, cache=StaticCache(financial_db)))

    assert client.get("/v1/summary").status_code == 401
    assert client.get("/v1/summary").status_code == 401
    limited = client.get("/v1/summary")
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "60"


def test_gcs_download_failure_returns_503(financial_db):
    class FailingCache:
        def ensure_current(self):
            raise DatabaseDownloadError("test failure")

    settings = Settings(api_key="test-secret", gcs_bucket="test-bucket")
    client = TestClient(create_app(settings=settings, cache=FailingCache()))

    response = client.get("/v1/summary", headers={"Authorization": "Bearer test-secret"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_download_failed"


def test_corrupt_sqlite_returns_503(tmp_path):
    corrupt_db = tmp_path / "moneyforward.db"
    corrupt_db.write_bytes(b"not a sqlite database")

    response = make_client(corrupt_db).get(
        "/v1/summary", headers={"Authorization": "Bearer test-secret"}
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_read_failed"


def test_missing_required_data_returns_503(financial_db):
    connection = sqlite3.connect(financial_db)
    connection.execute("DELETE FROM asset_history")
    connection.commit()
    connection.close()

    response = make_client(financial_db).get(
        "/v1/summary", headers={"Authorization": "Bearer test-secret"}
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "required_data_missing"
