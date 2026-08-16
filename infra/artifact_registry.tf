resource "google_artifact_registry_repository" "cloud_run_source_deploy" {
  # checkov:skip=CKV_GCP_84: Google-managed encryption is accepted for this personal project.
  project       = var.project_id
  location      = var.region
  repository_id = "cloud-run-source-deploy"
  description   = "Cloud Run Source Deployments"
  format        = "DOCKER"
  mode          = "STANDARD_REPOSITORY"

  vulnerability_scanning_config {
    enablement_config = "INHERITED"
  }

  lifecycle {
    prevent_destroy = true
  }
}
