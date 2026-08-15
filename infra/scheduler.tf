resource "google_cloud_scheduler_job" "crawler" {
  project          = var.project_id
  region           = var.region
  name             = "mf-crawler-daily"
  schedule         = "30 8 * * 1-5"
  time_zone        = "Asia/Tokyo"
  attempt_deadline = "300s"
  paused           = false

  retry_config {
    retry_count          = 0
    max_retry_duration   = "0s"
    min_backoff_duration = "5s"
    max_backoff_duration = "3600s"
    max_doublings        = 5
  }

  http_target {
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.crawler.name}:run"
    http_method = "POST"
    body        = base64encode("{}")

    headers = {
      "Content-Type" = "application/json"
    }

    oauth_token {
      service_account_email = google_service_account.app["crawler_scheduler"].email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}
