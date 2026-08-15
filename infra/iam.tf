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
