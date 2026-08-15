resource "google_secret_manager_secret" "active" {
  for_each = local.active_secrets

  project             = var.project_id
  secret_id           = each.value.secret_id
  deletion_protection = true

  replication {
    auto {}
  }

  lifecycle {
    prevent_destroy = true
  }
}
