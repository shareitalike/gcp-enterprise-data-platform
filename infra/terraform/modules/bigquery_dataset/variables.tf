variable "project_id" {
  description = "GCP project ID that owns this BigQuery dataset."
  type        = string
}

variable "dataset_id" {
  description = "BigQuery dataset ID. Must be unique within the project."
  type        = string
}

variable "friendly_name" {
  description = "Human-readable name shown in the BigQuery console."
  type        = string
  default     = ""
}

variable "description" {
  description = "Description of the dataset's purpose."
  type        = string
  default     = ""
}

variable "location" {
  description = "Dataset location. Use 'US' for multi-region or 'us-central1' for regional."
  type        = string
  default     = "US"
}

variable "default_table_expiration_ms" {
  description = "Default expiration time for tables in milliseconds. null = no expiration."
  type        = number
  default     = null
}

variable "iam_bindings" {
  description = "IAM bindings to apply to the dataset."
  type = list(object({
    role   = string
    member = string
  }))
  default = []
}

variable "labels" {
  description = "Labels to apply to the dataset."
  type        = map(string)
  default     = {}
}
