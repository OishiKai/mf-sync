resource "google_storage_bucket" "data" {
  # checkov:skip=CKV_GCP_62: Cloud Audit Logs Data Access is used instead of legacy Storage analytics logs.
  name                        = local.data_bucket_name
  project                     = var.project_id
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  soft_delete_policy {
    retention_duration_seconds = 604800
  }

  versioning {
    enabled = true
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_storage_bucket" "terraform_state" {
  # checkov:skip=CKV_GCP_62: Cloud Audit Logs Data Access is used instead of legacy Storage analytics logs.
  name                        = local.state_bucket_name
  project                     = var.project_id
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  soft_delete_policy {
    retention_duration_seconds = 604800
  }

  lifecycle {
    prevent_destroy = true
  }
}
