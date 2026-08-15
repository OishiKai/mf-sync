"""Generation-aware, atomic Cloud Storage SQLite cache."""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from google.cloud import storage

from app.config import Settings
from app.errors import DatabaseDownloadError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ObjectVersion:
    generation: str | None
    etag: str | None
    updated: str | None


class GcsSqliteCache:
    """Keeps a local DB while the source GCS object version is unchanged."""

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self._settings = settings
        try:
            self._client = client or storage.Client()
        except Exception as exc:
            raise DatabaseDownloadError("Could not initialize the GCS client") from exc
        self._cached_version: ObjectVersion | None = None
        self._lock = threading.Lock()

    def ensure_current(self) -> Path:
        """Return an atomically downloaded local file for the current GCS object."""
        with self._lock:
            try:
                bucket = self._client.bucket(self._settings.gcs_bucket)
                metadata_blob = bucket.blob(self._settings.gcs_db_object)
                metadata_blob.reload()
                version = ObjectVersion(
                    generation=(
                        str(metadata_blob.generation)
                        if metadata_blob.generation is not None
                        else None
                    ),
                    etag=metadata_blob.etag,
                    updated=(
                        metadata_blob.updated.isoformat()
                        if metadata_blob.updated is not None
                        else None
                    ),
                )
            except Exception as exc:
                raise DatabaseDownloadError("Could not read GCS object metadata") from exc

            local_path = self._settings.local_db_path
            if self._cached_version == version and local_path.is_file():
                return local_path

            local_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = local_path.with_name(f"{local_path.name}.new.{uuid4().hex}")

            try:
                download_blob = metadata_blob
                download_kwargs: dict[str, Any] = {"checksum": "auto"}
                if metadata_blob.generation is not None:
                    download_blob = bucket.blob(
                        self._settings.gcs_db_object,
                        generation=metadata_blob.generation,
                    )
                    download_kwargs["if_generation_match"] = metadata_blob.generation

                download_blob.download_to_filename(str(temporary_path), **download_kwargs)
                if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
                    raise OSError("Downloaded database is empty")
                os.replace(temporary_path, local_path)
            except Exception as exc:
                raise DatabaseDownloadError("Could not download GCS database object") from exc
            finally:
                temporary_path.unlink(missing_ok=True)

            self._cached_version = version
            logger.info("DB download succeeded generation=%s", version.generation or "unknown")
            return local_path
