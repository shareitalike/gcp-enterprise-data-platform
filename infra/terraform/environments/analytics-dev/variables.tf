variable "analytics_project_id" {
  description = "GCP Project ID for Project B (Analytics)."
  type        = string
}

variable "ingestion_project_id" {
  description = "GCP Project ID for Project A (Ingestion). Used for cross-project subscription references."
  type        = string
}

variable "region" {
  description = "Primary GCP region."
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name used in labels."
  type        = string
  default     = "dev"
}

variable "github_repo" {
  description = "GitHub repository in 'owner/repo' format used to scope WIF access (e.g. 'myuser/gcp-enterprise-data-platform')."
  type        = string
}

variable "alert_email" {
  description = "Email address to receive Cloud Monitoring alert notifications."
  type        = string
}
