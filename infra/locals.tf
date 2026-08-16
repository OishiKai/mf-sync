locals {
  data_bucket_name  = "${var.project_id}-mf-data"
  state_bucket_name = "${var.project_id}-tfstate"

  required_services = toset([
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudscheduler.googleapis.com",
    "containerscanning.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
  ])

  service_accounts = {
    api_runtime = {
      account_id   = "mf-sync-runtime"
      display_name = "mf-sync Cloud Run runtime"
    }
    api_build = {
      account_id   = "mf-sync-build"
      display_name = "mf-sync Cloud Build"
    }
    crawler_runtime = {
      account_id   = "mf-crawler-runtime"
      display_name = "MF crawler runtime"
    }
    crawler_scheduler = {
      account_id   = "mf-crawler-scheduler"
      display_name = "MF crawler scheduler invoker"
    }
  }

  active_secrets = {
    api_key = {
      secret_id       = "mf-sync-api-key"
      accessor_sa_key = "api_runtime"
    }
    username = {
      secret_id       = "mf-username"
      accessor_sa_key = "crawler_runtime"
    }
    password = {
      secret_id       = "mf-password"
      accessor_sa_key = "crawler_runtime"
    }
    totp = {
      secret_id       = "mf-totp-secret"
      accessor_sa_key = "crawler_runtime"
    }
  }

  legacy_bucket_roles = toset([
    "roles/storage.legacyBucketOwner",
    "roles/storage.legacyBucketReader",
    "roles/storage.legacyObjectOwner",
    "roles/storage.legacyObjectReader",
  ])

  legacy_bucket_bindings = {
    for pair in setproduct(
      toset([local.data_bucket_name, local.state_bucket_name]),
      local.legacy_bucket_roles,
      ) : "${pair[0]} ${pair[1]}" => {
      bucket = pair[0]
      role   = pair[1]
    }
  }
}
