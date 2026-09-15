# ─────────────────────────────────────────────────────────────────────────────
# Module: gcs_bucket
# Creates a GCS bucket with uniform bucket-level access, lifecycle rules,
# and optional cross-project IAM bindings.
# ─────────────────────────────────────────────────────────────────────────────

resource "google_storage_bucket" "this" {
  project                     = var.project_id
  name                        = var.bucket_name
  location                    = var.location
  storage_class               = var.storage_class
  uniform_bucket_level_access = true   # enforce; no ACLs

  versioning {
    enabled = var.versioning_enabled
  }

  dynamic "lifecycle_rule" {
    for_each = var.lifecycle_rules
    content {
      action {
        type = lifecycle_rule.value.action
      }
      condition {
        age = lifecycle_rule.value.age_days
      }
    }
  }

  labels = var.labels
}

# ── Cross-project IAM bindings ────────────────────────────────────────────────
# Grant specified identities access to this bucket.
# Used to give Project B service accounts read access to a Project A bucket.
resource "google_storage_bucket_iam_member" "members" {
  count = length(var.iam_bindings)

  bucket = google_storage_bucket.this.name
  role   = var.iam_bindings[count.index].role
  member = var.iam_bindings[count.index].member
}
