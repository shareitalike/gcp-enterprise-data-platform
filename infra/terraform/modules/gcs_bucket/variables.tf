variable "project_id" {
  description = "GCP project ID that will own this bucket."
  type        = string
}

variable "bucket_name" {
  description = "Globally unique GCS bucket name."
  type        = string
}

variable "location" {
  description = "GCS bucket location. Use 'US' for multi-region or 'us-central1' for regional."
  type        = string
  default     = "US"
}

variable "storage_class" {
  description = "Storage class: STANDARD, NEARLINE, COLDLINE, ARCHIVE."
  type        = string
  default     = "STANDARD"
}

variable "versioning_enabled" {
  description = "Enable object versioning. Disabled by default for raw ingestion buckets."
  type        = bool
  default     = false
}

variable "lifecycle_rules" {
  description = "List of lifecycle rules to apply to the bucket."
  type = list(object({
    action   = string  # "Delete" or "SetStorageClass"
    age_days = number
  }))
  default = []
}

variable "iam_bindings" {
  description = "List of IAM bindings to apply at the bucket level. Used for cross-project access."
  type = list(object({
    role   = string
    member = string  # e.g. "serviceAccount:sa@project.iam.gserviceaccount.com"
  }))
  default = []
}

variable "labels" {
  description = "Labels to apply to the bucket."
  type        = map(string)
  default     = {}
}
