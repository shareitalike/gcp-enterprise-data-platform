# ─────────────────────────────────────────────────────────────────────────────
# Module: service_account
# Creates a GCP service account and optional project-level IAM bindings.
# Cross-project bindings (e.g. bucket or topic access) are managed in the
# resource owner's Terraform stack, not here.
# ─────────────────────────────────────────────────────────────────────────────

resource "google_service_account" "this" {
  project      = var.project_id
  account_id   = var.account_id
  display_name = var.display_name
  description  = var.description
}

# ── Project-level IAM bindings for this SA ────────────────────────────────────
resource "google_project_iam_member" "roles" {
  for_each = toset(var.project_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.this.email}"
}
