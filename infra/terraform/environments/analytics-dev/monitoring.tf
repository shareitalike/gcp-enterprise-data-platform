# ── Cloud Monitoring Alerts for Streaming Pipeline ───────────────────────────
# These alert policies notify engineers when the streaming pipeline is degraded.
# All alerts send notifications via email to the configured notification channel.

# ── Notification Channel (Email) ─────────────────────────────────────────────
resource "google_monitoring_notification_channel" "email" {
  project      = var.analytics_project_id
  display_name = "On-Call Email Alert"
  type         = "email"

  labels = {
    email_address = var.alert_email
  }
}

# ── Alert 1: DLQ messages are piling up ──────────────────────────────────────
# Fires when any message has been sitting in the DLQ for more than 5 minutes.
# This means a bad message arrived AND no one has acknowledged it.
resource "google_monitoring_alert_policy" "dlq_messages_aging" {
  project      = var.analytics_project_id
  display_name = "DLQ: Messages aging beyond 5 minutes"
  combiner     = "OR"

  conditions {
    display_name = "DLQ subscription oldest unacked message age > 5 min"

    condition_threshold {
      filter          = "resource.type=\"pubsub_subscription\" AND resource.labels.subscription_id=\"dlq-analytics-dev-sub\" AND metric.type=\"pubsub.googleapis.com/subscription/oldest_unacked_message_age\""
      duration        = "0s"
      comparison      = "COMPARISON_GT"
      threshold_value = 300 # 5 minutes in seconds

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MAX"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.name]

  documentation {
    content   = "Messages are sitting in the Pub/Sub DLQ. Check the BigQuery `dead_letter_queue` table and `dataflow_pipeline.py` logs."
    mime_type = "text/markdown"
  }

  depends_on = [google_monitoring_notification_channel.email]
}

# ── Alert 2: Orders subscription backlog is growing ──────────────────────────
# Fires when there are more than 10,000 undelivered messages in the orders subscription.
# This means Dataflow is too slow, crashed, or not running.
resource "google_monitoring_alert_policy" "orders_subscription_backlog" {
  project      = var.analytics_project_id
  display_name = "Orders Sub: Message backlog > 10,000"
  combiner     = "OR"

  conditions {
    display_name = "orders-created-sub undelivered message count high"

    condition_threshold {
      filter          = "resource.type=\"pubsub_subscription\" AND resource.labels.subscription_id=\"orders-created-sub\" AND metric.type=\"pubsub.googleapis.com/subscription/num_undelivered_messages\""
      duration        = "300s" # Must persist for 5 minutes before alerting
      comparison      = "COMPARISON_GT"
      threshold_value = 10000

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MAX"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.name]

  documentation {
    content   = "The orders subscription has a large message backlog. Verify the Dataflow streaming pipeline is running and healthy."
    mime_type = "text/markdown"
  }

  depends_on = [google_monitoring_notification_channel.email]
}
