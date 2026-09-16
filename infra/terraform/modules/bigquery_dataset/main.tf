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
    prevent_destroy = true
  }
}

# ── Dataset-level IAM bindings ────────────────────────────────────────────────
resource "google_bigquery_dataset_iam_member" "members" {
  count = length(var.iam_bindings)

  project    = var.project_id
  dataset_id = google_bigquery_dataset.this.dataset_id
  role       = var.iam_bindings[count.index].role
  member     = var.iam_bindings[count.index].member
}
