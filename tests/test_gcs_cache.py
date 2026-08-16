from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.config import Settings
from app.errors import DatabaseDownloadError
from app.gcs_cache import GcsSqliteCache


class FakeObject:
    def __init__(self) -> None:
        self.generation = 1
        self.data = b"database-v1"
        self.downloads = 0
        self.fail_download = False


class FakeBlob:
    def __init__(self, source: FakeObject, requested_generation=None) -> None:
        self.source = source
        self.requested_generation = requested_generation
        self.generation = None
        self.etag = None
        self.updated = None

    def reload(self) -> None:
        self.generation = self.source.generation
        self.etag = f"etag-{self.source.generation}"
        self.updated = datetime(2026, 8, 15, tzinfo=UTC)

    def download_to_filename(self, filename, **kwargs) -> None:
        assert self.requested_generation == self.source.generation
        assert kwargs["if_generation_match"] == self.source.generation
        Path(filename).write_bytes(self.source.data)
        if self.source.fail_download:
            raise OSError("simulated interrupted download")
        self.source.downloads += 1


class FakeBucket:
    def __init__(self, source: FakeObject) -> None:
        self.source = source

    def blob(self, _name, generation=None):
        return FakeBlob(self.source, generation)


class FakeClient:
    def __init__(self, source: FakeObject) -> None:
        self.source = source

    def bucket(self, _name):
        return FakeBucket(self.source)


def make_cache(tmp_path):
    source = FakeObject()
    settings = Settings(
        api_key="test-secret",
        gcs_bucket="test-bucket",
        local_db_path=tmp_path / "moneyforward.db",
    )
    return source, GcsSqliteCache(settings, client=FakeClient(source))


def test_same_gcs_generation_reuses_local_database(tmp_path):
    source, cache = make_cache(tmp_path)

    first_path = cache.ensure_current()
    second_path = cache.ensure_current()

    assert first_path == second_path
    assert first_path.read_bytes() == b"database-v1"
    assert first_path.stat().st_mode & 0o777 == 0o600
    assert first_path.parent.stat().st_mode & 0o777 == 0o700
    assert source.downloads == 1


def test_new_gcs_generation_redownloads_database(tmp_path):
    source, cache = make_cache(tmp_path)
    local_path = cache.ensure_current()

    source.generation = 2
    source.data = b"database-v2"
    updated_path = cache.ensure_current()

    assert updated_path == local_path
    assert updated_path.read_bytes() == b"database-v2"
    assert source.downloads == 2
    assert list(tmp_path.glob("*.new.*")) == []


def test_reused_database_permissions_are_repaired(tmp_path):
    _source, cache = make_cache(tmp_path)
    local_path = cache.ensure_current()
    local_path.chmod(0o644)

    cache.ensure_current()

    assert local_path.stat().st_mode & 0o777 == 0o600


def test_failed_download_does_not_replace_current_database(tmp_path):
    source, cache = make_cache(tmp_path)
    local_path = cache.ensure_current()

    source.generation = 2
    source.data = b"partial-database-v2"
    source.fail_download = True

    with pytest.raises(DatabaseDownloadError):
        cache.ensure_current()

    assert local_path.read_bytes() == b"database-v1"
    assert list(tmp_path.glob("*.new.*")) == []
