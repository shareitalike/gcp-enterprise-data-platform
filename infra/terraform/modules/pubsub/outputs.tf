output "topic_id" {
  description = "Fully qualified Pub/Sub topic ID."
  value       = google_pubsub_topic.this.id
}

output "topic_name" {
  description = "Short name of the Pub/Sub topic."
  value       = google_pubsub_topic.this.name
}

output "dead_letter_topic_id" {
  description = "Fully qualified dead-letter topic ID (empty if not created)."
  value       = var.create_dead_letter_topic ? google_pubsub_topic.dead_letter[0].id : ""
}

output "subscription_id" {
  description = "Fully qualified subscription ID (empty if not created)."
  value       = var.create_subscription ? google_pubsub_subscription.this[0].id : ""
}
