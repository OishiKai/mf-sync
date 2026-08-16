variable "project_id" {
  description = "Google Cloud project containing the Money Forward infrastructure."
  type        = string
}

variable "region" {
  description = "Google Cloud region used by regional resources."
  type        = string
  default     = "asia-northeast1"
}

variable "api_image" {
  description = "Immutable container image used by the mf-sync Cloud Run service."
  type        = string

  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.api_image))
    error_message = "api_image must use an immutable sha256 digest."
  }
}

variable "crawler_image" {
  description = "Container image used by the mf-crawler Cloud Run job."
  type        = string

  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.crawler_image))
    error_message = "crawler_image must use an immutable sha256 digest."
  }
}

variable "alert_email" {
  description = "Email address that receives production security and failure alerts."
  type        = string

  validation {
    condition     = can(regex("^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$", var.alert_email))
    error_message = "alert_email must be a valid email address."
  }
}

variable "terraform_operator" {
  description = "IAM member that may manage these two buckets and read/write Terraform state (for example, user:you@example.com)."
  type        = string

  validation {
    condition     = can(regex("^(user|group|serviceAccount):[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$", var.terraform_operator))
    error_message = "terraform_operator must be an IAM user, group, or serviceAccount member."
  }
}

variable "import_existing" {
  description = "Import the existing production resources into an empty Terraform state."
  type        = bool
  default     = false
}
