variable "ingestion_project_id" {
  description = "GCP Project ID for Project A (Ingestion). Never hardcode this value."
  type        = string
}

variable "analytics_ingestion_sa_email" {
  description = "Email of the analytics-ingestion-sa from Project B. Used for cross-project GCS IAM binding."
  type        = string
  default     = ""  # set after Phase 2 analytics stack is applied
}

variable "analytics_streaming_sa_email" {
  description = "Email of the analytics-streaming-sa from Project B. Used for cross-project Pub/Sub IAM binding."
  type        = string
  default     = ""  # set after Phase 2 analytics stack is applied
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
