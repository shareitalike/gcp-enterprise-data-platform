# ─────────────────────────────────────────────────────────────────────────────
# Project B — Analytics Dev Environment
#
# Resources owned by this stack:
#   - BigQuery datasets: bronze, silver, silver_quarantine, gold,
#                        control, audit, quality
#   - Service accounts: analytics-ingestion-sa, analytics-streaming-sa, analytics-deploy-sa
#   - Project-level IAM for each SA
#   - Pub/Sub subscriptions (pulling from Project A topics)
#   - Dataflow temp GCS bucket
# ─────────────────────────────────────────────────────────────────────────────

locals {
  labels = {
    environment = var.environment
    project     = "commerce360"
    managed_by  = "terraform"
    stack       = "analytics"
  }
  df_temp_bucket = "c360-df-temp-${var.analytics_project_id}"
}

# ── Enable required APIs ──────────────────────────────────────────────────────
resource "google_project_service" "apis" {
  for_each = toset([
    "bigquery.googleapis.com",
    "bigquerystorage.googleapis.com",
    "dataflow.googleapis.com",
    "pubsub.googleapis.com",
    "storage.googleapis.com",
    "secretmanager.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",    # required for SA impersonation
    "sts.googleapis.com",               # required for Workload Identity Federation
  ])
  project            = var.analytics_project_id
  service            = each.value
  disable_on_destroy = false
}

# ── Service Accounts ──────────────────────────────────────────────────────────
module "ingestion_sa" {
  source       = "../../modules/service_account"
  project_id   = var.analytics_project_id
  account_id   = "analytics-ingestion-sa"
  display_name = "Analytics Ingestion SA"
  description  = "Reads cross-project GCS files and runs BigQuery batch load jobs"
  project_roles = [
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
  ]
  depends_on = [google_project_service.apis]
}

module "streaming_sa" {
  source       = "../../modules/service_account"
  project_id   = var.analytics_project_id
  account_id   = "analytics-streaming-sa"
  display_name = "Analytics Streaming SA"
  description  = "Runs Dataflow streaming jobs; reads cross-project Pub/Sub subscription"
  project_roles = [
    "roles/dataflow.worker",
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/storage.objectAdmin",    # Dataflow temp bucket access
  ]
  depends_on = [google_project_service.apis]
}

module "deploy_sa" {
  source       = "../../modules/service_account"
  project_id   = var.analytics_project_id
  account_id   = "analytics-deploy-sa"
  display_name = "Analytics Deploy SA"
  description  = "Used by CI/CD (via WIF) for Terraform deployments"
  project_roles = [
    "roles/bigquery.admin",
    "roles/pubsub.admin",
    "roles/storage.admin",
    "roles/iam.securityAdmin",
    "roles/dataflow.admin",
  ]
  depends_on = [google_project_service.apis]
}

# ── BigQuery Datasets ─────────────────────────────────────────────────────────
module "bronze" {
  source      = "../../modules/bigquery_dataset"
  project_id  = var.analytics_project_id
  dataset_id  = "bronze"
  description = "Immutable raw landing tables loaded from Project A GCS"
  location    = "US"
  iam_bindings = [
    { role = "roles/bigquery.dataEditor", member = module.ingestion_sa.member },
    { role = "roles/bigquery.dataEditor", member = module.streaming_sa.member },
  ]
  labels     = local.labels
  depends_on = [google_project_service.apis]
}

module "silver" {
  source      = "../../modules/bigquery_dataset"
  project_id  = var.analytics_project_id
  dataset_id  = "silver"
  description = "Validated, typed, deduplicated tables"
  location    = "US"
  iam_bindings = [
    { role = "roles/bigquery.dataEditor", member = module.ingestion_sa.member },
  ]
  labels     = local.labels
  depends_on = [google_project_service.apis]
}

module "silver_quarantine" {
  source                      = "../../modules/bigquery_dataset"
  project_id                  = var.analytics_project_id
  dataset_id                  = "silver_quarantine"
  description                 = "Records failing Silver validation"
  location                    = "US"
  default_table_expiration_ms = 2592000000  # 30 days
  iam_bindings = [
    { role = "roles/bigquery.dataEditor", member = module.ingestion_sa.member },
  ]
  labels     = local.labels
  depends_on = [google_project_service.apis]
}

module "gold" {
  source      = "../../modules/bigquery_dataset"
  project_id  = var.analytics_project_id
  dataset_id  = "gold"
  description = "Business-ready dimensional models and fact tables"
  location    = "US"
  iam_bindings = [
    { role = "roles/bigquery.dataEditor", member = module.ingestion_sa.member },
  ]
  labels     = local.labels
  depends_on = [google_project_service.apis]
}

module "control" {
  source      = "../../modules/bigquery_dataset"
  project_id  = var.analytics_project_id
  dataset_id  = "control"
  description = "File manifests, idempotency tracking, pipeline state"
  location    = "US"
  iam_bindings = [
    { role = "roles/bigquery.dataEditor", member = module.ingestion_sa.member },
    { role = "roles/bigquery.dataEditor", member = module.streaming_sa.member },
  ]
  labels     = local.labels
  depends_on = [google_project_service.apis]
}

module "audit" {
  source      = "../../modules/bigquery_dataset"
  project_id  = var.analytics_project_id
  dataset_id  = "audit"
  description = "Pipeline run records, record counts, duration, status"
  location    = "US"
  iam_bindings = [
    { role = "roles/bigquery.dataEditor", member = module.ingestion_sa.member },
    { role = "roles/bigquery.dataEditor", member = module.streaming_sa.member },
  ]
  labels     = local.labels
  depends_on = [google_project_service.apis]
}

module "quality" {
  source      = "../../modules/bigquery_dataset"
  project_id  = var.analytics_project_id
  dataset_id  = "quality"
  description = "Data quality check results"
  location    = "US"
  iam_bindings = [
    { role = "roles/bigquery.dataEditor", member = module.ingestion_sa.member },
  ]
  labels     = local.labels
  depends_on = [google_project_service.apis]
}

# ── Dataflow Temp Bucket ──────────────────────────────────────────────────────
module "dataflow_temp_bucket" {
  source      = "../../modules/gcs_bucket"
  project_id  = var.analytics_project_id
  bucket_name = local.df_temp_bucket
  location    = "US"

  lifecycle_rules = [
    { action = "Delete", age_days = 7 }   # temp files auto-cleaned
  ]

  iam_bindings = [
    { role = "roles/storage.objectAdmin", member = module.streaming_sa.member }
  ]

  labels     = local.labels
  depends_on = [google_project_service.apis]
}

# ── Cross-project Pub/Sub Subscriptions ───────────────────────────────────────
# Subscriptions are owned by Project B but pull from Project A topics.
resource "google_pubsub_subscription" "orders_sub" {
  project = var.analytics_project_id
  name    = "orders-created-sub"
  topic   = "projects/${var.ingestion_project_id}/topics/orders-created"

  ack_deadline_seconds       = 60
  message_retention_duration = "604800s"

  dead_letter_policy {
    dead_letter_topic     = "projects/${var.analytics_project_id}/topics/dlq-analytics-dev"
    max_delivery_attempts = 5
  }

  labels     = local.labels
  depends_on = [google_project_service.apis, google_pubsub_topic.dlq]
}

resource "google_pubsub_subscription" "clickstream_sub" {
  project = var.analytics_project_id
  name    = "clickstream-events-sub"
  topic   = "projects/${var.ingestion_project_id}/topics/clickstream-events"

  ack_deadline_seconds       = 30
  message_retention_duration = "604800s"

  dead_letter_policy {
    dead_letter_topic     = "projects/${var.analytics_project_id}/topics/dlq-analytics-dev"
    max_delivery_attempts = 5
  }

  labels     = local.labels
  depends_on = [google_project_service.apis, google_pubsub_topic.dlq]
}

# ── Analytics DLQ Topic ───────────────────────────────────────────────────────
resource "google_pubsub_topic" "dlq" {
  project = var.analytics_project_id
  name    = "dlq-analytics-dev"
  labels  = local.labels
}

# ── Outputs (used by ingestion-dev tfvars) ─────────────────────────────────────
output "ingestion_sa_email" {
  value       = module.ingestion_sa.email
  description = "Set this as analytics_ingestion_sa_email in ingestion-dev/terraform.tfvars"
}

output "streaming_sa_email" {
  value       = module.streaming_sa.email
  description = "Set this as analytics_streaming_sa_email in ingestion-dev/terraform.tfvars"
}

output "deploy_sa_email" {
  value = module.deploy_sa.email
}

output "dataflow_temp_bucket_url" {
  value = module.dataflow_temp_bucket.bucket_url
}
