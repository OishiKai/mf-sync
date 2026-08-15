output "api_url" {
  description = "Cloud Run URL for the read-only summary API."
  value       = google_cloud_run_v2_service.api.uri
}

output "data_bucket" {
  description = "GCS bucket containing the Money Forward SQLite snapshot."
  value       = google_storage_bucket.data.url
}

output "crawler_job_name" {
  description = "Fully-qualified Cloud Run crawler job name."
  value       = google_cloud_run_v2_job.crawler.id
}

output "crawler_schedule" {
  description = "Crawler schedule and timezone."
  value       = "${google_cloud_scheduler_job.crawler.schedule} ${google_cloud_scheduler_job.crawler.time_zone}"
}
