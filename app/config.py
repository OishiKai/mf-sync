"""Environment-backed service configuration."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from app.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class Settings:
    api_key: str
    gcs_bucket: str
    gcs_db_object: str = "moneyforward.db"
    local_db_path: Path = Path("/tmp/moneyforward.db")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        values = os.environ if env is None else env
        api_key = values.get("API_KEY", "").strip()
        bucket = values.get("GCS_BUCKET", "").strip()
        db_object = values.get("GCS_DB_OBJECT", "moneyforward.db").strip()

        if not api_key or not bucket or not db_object:
            raise ConfigurationError("Required environment variables are missing")

        return cls(api_key=api_key, gcs_bucket=bucket, gcs_db_object=db_object)
