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
