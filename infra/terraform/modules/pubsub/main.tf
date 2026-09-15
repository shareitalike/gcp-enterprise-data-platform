# ─────────────────────────────────────────────────────────────────────────────
# Module: pubsub
# Creates a Pub/Sub topic with optional schema, dead-letter topic, and
# cross-project IAM bindings (publisher or subscriber).
# ─────────────────────────────────────────────────────────────────────────────

resource "google_pubsub_topic" "this" {
  project                    = var.project_id
  name                       = var.topic_name
  message_retention_duration = var.message_retention_duration

  labels = var.labels
}

# ── Dead-letter topic ─────────────────────────────────────────────────────────
resource "google_pubsub_topic" "dead_letter" {
  count   = var.create_dead_letter_topic ? 1 : 0
  project = var.project_id
  name    = "${var.topic_name}-dlq"

  labels = var.labels
}

# ── Subscription (optional — only created if var.create_subscription = true) ──
# Note: subscriptions for cross-project consumers are created in the CONSUMER's
# project Terraform, not here. This optional subscription is for local consumers.
resource "google_pubsub_subscription" "this" {
  count   = var.create_subscription ? 1 : 0
  project = var.project_id
  name    = "${var.topic_name}-sub"
  topic   = google_pubsub_topic.this.id

  ack_deadline_seconds       = var.ack_deadline_seconds
  message_retention_duration = var.message_retention_duration
  retain_acked_messages      = false

  dynamic "dead_letter_policy" {
    for_each = var.create_dead_letter_topic ? [1] : []
    content {
      dead_letter_topic     = google_pubsub_topic.dead_letter[0].id
      max_delivery_attempts = var.dead_letter_max_delivery_attempts
    }
  }

  labels = var.labels
}

# ── Topic-level IAM bindings ──────────────────────────────────────────────────
# Used to grant cross-project identities (Project B) subscriber access
# on a Project A topic.
resource "google_pubsub_topic_iam_member" "members" {
  for_each = { for b in var.topic_iam_bindings : "${b.role}/${b.member}" => b }

  project = var.project_id
  topic   = google_pubsub_topic.this.name
  role    = each.value.role
  member  = each.value.member
}
