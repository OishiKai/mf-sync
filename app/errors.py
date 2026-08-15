"""Public, balance-safe application errors."""


class MfSyncError(RuntimeError):
    """Base error that can safely be returned without financial data."""

    code = "service_unavailable"
    public_message = "The financial summary is temporarily unavailable."


class ConfigurationError(MfSyncError):
    code = "configuration_error"
    public_message = "The service is not configured correctly."


class DatabaseDownloadError(MfSyncError):
    code = "database_download_failed"
    public_message = "The financial database could not be downloaded."


class DatabaseReadError(MfSyncError):
    code = "database_read_failed"
    public_message = "The financial database could not be read."


class RequiredDataMissingError(MfSyncError):
    code = "required_data_missing"
    public_message = "The financial database does not contain a complete current snapshot."
