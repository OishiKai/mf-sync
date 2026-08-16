resource "google_cloud_run_v2_service" "api" {
  project             = var.project_id
  location            = var.region
  name                = "mf-sync"
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = true

  scaling {
    max_instance_count = 3
  }

  template {
    service_account                  = google_service_account.app["api_runtime"].email
    timeout                          = "60s"
    max_instance_request_concurrency = 20

    containers {
      image = var.api_image

      ports {
        name           = "http1"
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      startup_probe {
        failure_threshold     = 10
        initial_delay_seconds = 1
        period_seconds        = 2
        timeout_seconds       = 2

        http_get {
          path = "/healthz"
          port = 8080
        }
      }

      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.data.name
      }

      env {
        name  = "GCS_DB_OBJECT"
        value = "moneyforward.db"
      }

      env {
        name  = "UNAUTHORIZED_RATE_LIMIT"
        value = "120"
      }

      env {
        name  = "AUTHENTICATED_RATE_LIMIT"
        value = "60"
      }

      env {
        name  = "RATE_LIMIT_WINDOW_SECONDS"
        value = "60"
      }

      env {
        name = "API_KEY"

        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.active["api_key"].secret_id
            version = "1"
          }
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      build_config,
      client,
      client_version,
    ]
  }
}

resource "google_cloud_run_v2_job" "crawler" {
  project             = var.project_id
  location            = var.region
  name                = "mf-crawler"
  deletion_protection = true

  template {
    task_count  = 1
    parallelism = 1

    template {
      service_account       = google_service_account.app["crawler_runtime"].email
      timeout               = "7200s"
      max_retries           = 0
      execution_environment = "EXECUTION_ENVIRONMENT_GEN2"

      containers {
        image   = var.crawler_image
        command = ["/usr/bin/bash"]
        args    = ["/app/docker/crawler/cloud-run-job.sh"]

        resources {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
        }

        env {
          name  = "GCS_BUCKET"
          value = google_storage_bucket.data.name
        }

        env {
          name  = "GCS_DB_OBJECT"
          value = "moneyforward.db"
        }

        env {
          name  = "DB_PATH"
          value = "/tmp/moneyforward.db"
        }

        env {
          name  = "AUTH_STATE_PATH"
          value = "/tmp/auth-state.json"
        }

        env {
          name  = "MAX_WAIT_MINUTES"
          value = "5"
        }

        env {
          name = "MF_USERNAME"

          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.active["username"].secret_id
              version = "1"
            }
          }
        }

        env {
          name = "MF_PASSWORD"

          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.active["password"].secret_id
              version = "1"
            }
          }
        }

        env {
          name = "MF_TOTP_SECRET"

          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.active["totp"].secret_id
              version = "1"
            }
          }
        }
      }
    }
  }

  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      client,
      client_version,
    ]
  }
}
