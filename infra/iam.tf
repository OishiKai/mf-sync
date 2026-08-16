resource "google_project_iam_member" "api_build" {
  project = var.project_id
  role    = "roles/run.builder"
  member  = google_service_account.app["api_build"].member
}

resource "google_cloud_run_v2_service_iam_member" "api_public_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_job_iam_member" "scheduler_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.crawler.name
  role     = "roles/run.invoker"
  member   = google_service_account.app["crawler_scheduler"].member
}

resource "google_storage_bucket_iam_member" "api_data_reader" {
  bucket = google_storage_bucket.data.name
  role   = "roles/storage.objectViewer"
  member = google_service_account.app["api_runtime"].member

  condition {
    title       = "moneyforward-db-read-only"
    description = "Read only the crawler SQLite object"
    expression  = "resource.name == 'projects/_/buckets/${google_storage_bucket.data.name}/objects/moneyforward.db'"
  }
}

resource "google_storage_bucket_iam_member" "crawler_data_writer" {
  bucket = google_storage_bucket.data.name
  role   = "roles/storage.objectUser"
  member = google_service_account.app["crawler_runtime"].member

  condition {
    title       = "moneyforward-db-only"
    description = "Read and replace only the crawler SQLite object"
    expression  = "resource.name == 'projects/_/buckets/${google_storage_bucket.data.name}/objects/moneyforward.db'"
  }
}

resource "google_secret_manager_secret_iam_member" "accessor" {
  for_each = local.active_secrets

  project   = var.project_id
  secret_id = google_secret_manager_secret.active[each.key].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.app[each.value.accessor_sa_key].member
}

resource "google_project_iam_binding" "no_basic_editor" {
  # checkov:skip=CKV_GCP_49: This empty authoritative binding removes, rather than grants, Editor.
  # checkov:skip=CKV_GCP_117: This empty authoritative binding enforces that the basic role is unused.
  project = var.project_id
  role    = "roles/editor"
  members = []
}

resource "google_storage_bucket_iam_binding" "no_legacy_access" {
  for_each = local.legacy_bucket_bindings

  bucket  = each.value.bucket
  role    = each.value.role
  members = []
}

resource "google_project_iam_custom_role" "terraform_bucket_manager" {
  project     = var.project_id
  role_id     = "mfSyncTerraformBucketManager"
  title       = "MF Sync Terraform bucket manager"
  description = "Manages configuration and IAM for only the MF Sync data and state buckets."

  permissions = [
    "storage.buckets.get",
    "storage.buckets.getIamPolicy",
    "storage.buckets.setIamPolicy",
    "storage.buckets.update",
  ]
}

resource "google_project_iam_member" "terraform_bucket_manager" {
  project = var.project_id
  role    = google_project_iam_custom_role.terraform_bucket_manager.name
  member  = var.terraform_operator

  condition {
    title       = "mf-sync-buckets-only"
    description = "Manage only the MF Sync data and Terraform state buckets"
    expression = join(" || ", [
      "resource.name == 'projects/_/buckets/${google_storage_bucket.data.name}'",
      "resource.name == 'projects/_/buckets/${google_storage_bucket.terraform_state.name}'",
    ])
  }
}

resource "google_storage_bucket_iam_member" "terraform_state_user" {
  bucket = google_storage_bucket.terraform_state.name
  role   = "roles/storage.objectUser"
  member = var.terraform_operator
}
