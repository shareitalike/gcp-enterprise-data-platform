# ─────────────────────────────────────────────────────────────────────────────
# Module: bigquery_dataset
# Creates a BigQuery dataset with IAM bindings.
# ─────────────────────────────────────────────────────────────────────────────

resource "google_bigquery_dataset" "this" {
  project                     = var.project_id
  dataset_id                  = var.dataset_id
  friendly_name               = var.friendly_name
  description                 = var.description
  location                    = var.location
  default_table_expiration_ms = var.default_table_expiration_ms

  labels = var.labels

  # Prevent accidental deletion of datasets containing data
  lifecycle {
    prevent_destroy = false   # set to true in production environments
  }
}

# ── Dataset-level IAM bindings ────────────────────────────────────────────────
resource "google_bigquery_dataset_iam_member" "members" {
  for_each = { for b in var.iam_bindings : "${b.role}/${b.member}" => b }

  project    = var.project_id
  dataset_id = google_bigquery_dataset.this.dataset_id
  role       = each.value.role
  member     = each.value.member
}
