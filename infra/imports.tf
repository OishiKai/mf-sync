import {
  for_each = local.required_services
  to       = google_project_service.required[each.value]
  id       = "${var.project_id}/${each.value}"
}

import {
  for_each = local.service_accounts
  to       = google_service_account.app[each.key]
  id       = "projects/${var.project_id}/serviceAccounts/${each.value.account_id}@${var.project_id}.iam.gserviceaccount.com"
}

import {
  for_each = local.active_secrets
  to       = google_secret_manager_secret.active[each.key]
  id       = "projects/${var.project_id}/secrets/${each.value.secret_id}"
}

import {
  to = google_storage_bucket.data
  id = local.data_bucket_name
}

import {
  to = google_storage_bucket.terraform_state
  id = local.state_bucket_name
}

import {
  to = google_artifact_registry_repository.cloud_run_source_deploy
  id = "projects/${var.project_id}/locations/${var.region}/repositories/cloud-run-source-deploy"
}

import {
  to = google_cloud_run_v2_service.api
  id = "projects/${var.project_id}/locations/${var.region}/services/mf-sync"
}

import {
  to = google_cloud_run_v2_job.crawler
  id = "projects/${var.project_id}/locations/${var.region}/jobs/mf-crawler"
}

import {
  to = google_cloud_scheduler_job.crawler
  id = "projects/${var.project_id}/locations/${var.region}/jobs/mf-crawler-daily"
}

import {
  to = google_project_iam_member.api_build
  id = "${var.project_id} roles/run.builder serviceAccount:${local.service_accounts["api_build"].account_id}@${var.project_id}.iam.gserviceaccount.com"
}

import {
  to = google_cloud_run_v2_service_iam_member.api_public_invoker
  id = "projects/${var.project_id}/locations/${var.region}/services/mf-sync roles/run.invoker allUsers"
}

import {
  to = google_cloud_run_v2_job_iam_member.scheduler_invoker
  id = "projects/${var.project_id}/locations/${var.region}/jobs/mf-crawler roles/run.invoker serviceAccount:${local.service_accounts["crawler_scheduler"].account_id}@${var.project_id}.iam.gserviceaccount.com"
}

import {
  to = google_storage_bucket_iam_member.api_data_reader
  id = "b/${local.data_bucket_name} roles/storage.objectViewer serviceAccount:${local.service_accounts["api_runtime"].account_id}@${var.project_id}.iam.gserviceaccount.com"
}

import {
  to = google_storage_bucket_iam_member.crawler_data_writer
  id = "b/${local.data_bucket_name} roles/storage.objectUser serviceAccount:${local.service_accounts["crawler_runtime"].account_id}@${var.project_id}.iam.gserviceaccount.com moneyforward-db-only"
}

import {
  for_each = local.active_secrets
  to       = google_secret_manager_secret_iam_member.accessor[each.key]
  id       = "projects/${var.project_id}/secrets/${each.value.secret_id} roles/secretmanager.secretAccessor serviceAccount:${local.service_accounts[each.value.accessor_sa_key].account_id}@${var.project_id}.iam.gserviceaccount.com"
}
