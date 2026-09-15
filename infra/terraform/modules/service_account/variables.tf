variable "project_id" {
  description = "GCP project ID that owns this service account."
  type        = string
}

variable "account_id" {
  description = "Service account ID (short name, not the full email). Max 30 chars."
  type        = string
}

variable "display_name" {
  description = "Human-readable display name shown in the console."
  type        = string
}

variable "description" {
  description = "Description of the service account's purpose."
  type        = string
  default     = ""
}

variable "project_roles" {
  description = "List of project-level IAM roles to grant to this SA. Resource-level bindings are set in the resource module."
  type        = list(string)
  default     = []
}
