resource "google_monitoring_notification_channel" "security_email" {
  project      = var.project_id
  display_name = "mf-sync security alerts"
  type         = "email"
  labels = {
    email_address = var.alert_email
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_logging_metric" "api_unauthorized" {
  project = var.project_id
  name    = "mf_sync_api_unauthorized"
  filter  = <<-EOT
    resource.type="cloud_run_revision"
    resource.labels.service_name="mf-sync"
    httpRequest.status=401
  EOT

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "INT64"
    unit         = "1"
    display_name = "mf-sync unauthorized requests"
  }
}

resource "google_logging_metric" "api_server_errors" {
  project = var.project_id
  name    = "mf_sync_api_server_errors"
  filter  = <<-EOT
    resource.type="cloud_run_revision"
    resource.labels.service_name="mf-sync"
    httpRequest.status>=500
  EOT

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "INT64"
    unit         = "1"
    display_name = "mf-sync server errors"
  }
}

resource "google_monitoring_alert_policy" "api_unauthorized" {
  project      = var.project_id
  display_name = "mf-sync repeated unauthorized requests"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "More than 30 unauthorized requests in 5 minutes"

    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.api_unauthorized.name}\" AND resource.type=\"cloud_run_revision\""
      comparison      = "COMPARISON_GT"
      threshold_value = 30
      duration        = "0s"

      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_SUM"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.security_email.name]
}

resource "google_monitoring_alert_policy" "api_server_errors" {
  project      = var.project_id
  display_name = "mf-sync API server errors"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "Any server error in 5 minutes"

    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.api_server_errors.name}\" AND resource.type=\"cloud_run_revision\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "0s"

      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_SUM"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.security_email.name]
}

resource "google_monitoring_alert_policy" "crawler_failed" {
  project      = var.project_id
  display_name = "mf-crawler execution failed"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "A crawler execution failed"

    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/job/completed_execution_count\" AND resource.type=\"cloud_run_job\" AND resource.labels.job_name=\"mf-crawler\" AND metric.labels.result=\"failed\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "0s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.security_email.name]
}
