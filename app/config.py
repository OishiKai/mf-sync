"""Environment-backed service configuration."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from app.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class Settings:
    api_key: str
    gcs_bucket: str
    gcs_db_object: str = "moneyforward.db"
    local_db_path: Path = Path(tempfile.gettempdir()) / "mf-sync" / "moneyforward.db"
    unauthorized_rate_limit: int = 120
    authenticated_rate_limit: int = 60
    rate_limit_window_seconds: int = 60

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        values = os.environ if env is None else env
        api_key = values.get("API_KEY", "").strip()
        bucket = values.get("GCS_BUCKET", "").strip()
        db_object = values.get("GCS_DB_OBJECT", "moneyforward.db").strip()

        def positive_int(name: str, default: int) -> int:
            try:
                value = int(values.get(name, str(default)))
            except ValueError as exc:
                raise ConfigurationError(f"{name} must be a positive integer") from exc
            if value < 1:
                raise ConfigurationError(f"{name} must be a positive integer")
            return value

        if not api_key or not bucket or not db_object:
            raise ConfigurationError("Required environment variables are missing")

        return cls(
            api_key=api_key,
            gcs_bucket=bucket,
            gcs_db_object=db_object,
            unauthorized_rate_limit=positive_int("UNAUTHORIZED_RATE_LIMIT", 120),
            authenticated_rate_limit=positive_int("AUTHENTICATED_RATE_LIMIT", 60),
            rate_limit_window_seconds=positive_int("RATE_LIMIT_WINDOW_SECONDS", 60),
        )
