locals {
  audit_log_types = {
    "secretmanager.googleapis.com" = toset(["ADMIN_READ", "DATA_READ", "DATA_WRITE"])
    "storage.googleapis.com"       = toset(["DATA_READ", "DATA_WRITE"])
  }
}

resource "google_project_iam_audit_config" "sensitive_services" {
  for_each = local.audit_log_types

  project = var.project_id
  service = each.key

  dynamic "audit_log_config" {
    for_each = each.value

    content {
      log_type = audit_log_config.value
    }
  }
}
