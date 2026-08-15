variable "project_id" {
  description = "Google Cloud project containing the Money Forward infrastructure."
  type        = string
  default     = "moneyforward-sync-20260815"
}

variable "region" {
  description = "Google Cloud region used by regional resources."
  type        = string
  default     = "asia-northeast1"
}

variable "api_image" {
  description = "Immutable container image used by the mf-sync Cloud Run service."
  type        = string
  default     = "asia-northeast1-docker.pkg.dev/moneyforward-sync-20260815/cloud-run-source-deploy/mf-sync@sha256:6b74438ff8c32b830dfa52034a458138c9bbfc1d999463432f03c331c1448f9d"
}

variable "crawler_image" {
  description = "Container image used by the mf-crawler Cloud Run job."
  type        = string
  default     = "asia-northeast1-docker.pkg.dev/moneyforward-sync-20260815/cloud-run-source-deploy/mf-crawler:gcp-secrets-2"
}
