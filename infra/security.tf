resource "google_project_default_service_accounts" "disable" {
  project        = var.project_id
  action         = "DISABLE"
  restore_policy = "REVERT_AND_IGNORE_FAILURE"

  depends_on = [google_project_iam_binding.no_basic_editor]

  lifecycle {
    prevent_destroy = true
  }
}
