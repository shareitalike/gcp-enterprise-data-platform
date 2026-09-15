# ─────────────────────────────────────────────────────────────────────────────
# Project A — Ingestion Dev Environment
#
# Resources owned by this stack:
#   - GCS raw bucket
#   - Pub/Sub topics (orders-created, clickstream-events) + DLQs
#   - Publisher service account
#   - Cross-project IAM bindings (granting Project B SA access to bucket + topics)
#
# Apply order:
#   1. terraform apply (this stack) with analytics_*_sa_email = ""
#   2. terraform apply analytics-dev stack → note output SA emails
#   3. terraform apply (this stack) again with SA emails filled in
# ─────────────────────────────────────────────────────────────────────────────

locals {
  labels = {
    environment = var.environment
    project     = "commerce360"
    managed_by  = "terraform"
    stack       = "ingestion"
  }
  raw_bucket_name = "c360-raw-${var.ingestion_project_id}"
}

# ── Enable required APIs ──────────────────────────────────────────────────────
resource "google_project_service" "apis" {
  for_each = toset([
    "storage.googleapis.com",
    "pubsub.googleapis.com",
    "logging.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
  ])
  project            = var.ingestion_project_id
  service            = each.value
  disable_on_destroy = false
}

# ── GCS Raw Bucket ────────────────────────────────────────────────────────────
module "raw_bucket" {
  source     = "../../modules/gcs_bucket"
  project_id = var.ingestion_project_id
  bucket_name = local.raw_bucket_name
  location   = "US"

  lifecycle_rules = [
    {
      action   = "Delete"
      age_days = 90
    }
  ]

  # Cross-project read access: Project B ingestion SA reads raw files
  iam_bindings = var.analytics_ingestion_sa_email != "" ? [
    {
      role   = "roles/storage.objectViewer"
      member = "serviceAccount:${var.analytics_ingestion_sa_email}"
    }
  ] : []

  labels = local.labels

  depends_on = [google_project_service.apis]
}

# ── Publisher Service Account (Project A internal) ────────────────────────────
module "publisher_sa" {
  source       = "../../modules/service_account"
  project_id   = var.ingestion_project_id
  account_id   = "synthetic-publisher-sa"
  display_name = "Synthetic Data Publisher"
  description  = "Publishes synthetic events to Pub/Sub topics in Project A"
  project_roles = ["roles/pubsub.publisher"]

  depends_on = [google_project_service.apis]
}

# ── Pub/Sub Topics ────────────────────────────────────────────────────────────
module "orders_topic" {
  source     = "../../modules/pubsub"
  project_id = var.ingestion_project_id
  topic_name = "orders-created"

  message_retention_duration        = "604800s"
  create_dead_letter_topic          = true
  dead_letter_max_delivery_attempts = 5

  # Cross-project subscriber: Project B streaming SA subscribes to this topic
  topic_iam_bindings = var.analytics_streaming_sa_email != "" ? [
    {
      role   = "roles/pubsub.subscriber"
      member = "serviceAccount:${var.analytics_streaming_sa_email}"
    }
  ] : []

  labels = local.labels

  depends_on = [google_project_service.apis]
}

module "clickstream_topic" {
  source     = "../../modules/pubsub"
  project_id = var.ingestion_project_id
  topic_name = "clickstream-events"

  message_retention_duration        = "604800s"
  create_dead_letter_topic          = true
  dead_letter_max_delivery_attempts = 5

  topic_iam_bindings = var.analytics_streaming_sa_email != "" ? [
    {
      role   = "roles/pubsub.subscriber"
      member = "serviceAccount:${var.analytics_streaming_sa_email}"
    }
  ] : []

  labels = local.labels

  depends_on = [google_project_service.apis]
}

# ── Outputs ───────────────────────────────────────────────────────────────────
output "raw_bucket_name" {
  value = module.raw_bucket.bucket_name
}

output "raw_bucket_url" {
  value = module.raw_bucket.bucket_url
}

output "publisher_sa_email" {
  value = module.publisher_sa.email
}

output "orders_topic_id" {
  value = module.orders_topic.topic_id
}

output "clickstream_topic_id" {
  value = module.clickstream_topic.topic_id
}
