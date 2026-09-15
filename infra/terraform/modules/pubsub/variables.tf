variable "project_id" {
  description = "GCP project ID that owns the Pub/Sub topic."
  type        = string
}

variable "topic_name" {
  description = "Name of the Pub/Sub topic."
  type        = string
}

variable "message_retention_duration" {
  description = "How long Pub/Sub retains unacknowledged messages. e.g. '604800s' = 7 days."
  type        = string
  default     = "604800s"
}

variable "create_dead_letter_topic" {
  description = "Whether to create a dead-letter topic alongside the main topic."
  type        = bool
  default     = true
}

variable "dead_letter_max_delivery_attempts" {
  description = "Number of delivery attempts before routing to dead-letter topic."
  type        = number
  default     = 5
}

variable "create_subscription" {
  description = "Create a same-project subscription. Set false for cross-project consumers (they create their own subscription)."
  type        = bool
  default     = false
}

variable "ack_deadline_seconds" {
  description = "Acknowledgement deadline for the subscription, in seconds."
  type        = number
  default     = 60
}

variable "topic_iam_bindings" {
  description = "IAM bindings applied to the topic. Used to grant cross-project subscriber or publisher access."
  type = list(object({
    role   = string
    member = string
  }))
  default = []
}

variable "labels" {
  description = "Labels to apply to Pub/Sub resources."
  type        = map(string)
  default     = {}
}
