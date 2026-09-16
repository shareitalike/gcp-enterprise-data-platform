# ── Workload Identity Federation for GitHub Actions ───────────────────────────
# This allows GitHub Actions to securely authenticate as the Analytics Deploy SA
# without needing to export or store a long-lived JSON service account key.

# 1. Create a Workload Identity Pool
resource "google_iam_workload_identity_pool" "github_pool" {
  project                   = var.analytics_project_id
  workload_identity_pool_id = "github-actions-pool"
  display_name              = "GitHub Actions Pool"
  description               = "Identity pool for GitHub Actions CI/CD"
  disabled                  = false
}

# 2. Create a Workload Identity Provider connected to GitHub
resource "google_iam_workload_identity_pool_provider" "github_provider" {
  project                            = var.analytics_project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_pool.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub Actions Provider"
  
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }
  
  # Ensure only our specific repository can use this provider
  attribute_condition = "assertion.repository == '${var.github_repo}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# 3. Bind the Pool to our Analytics Deploy Service Account
resource "google_service_account_iam_member" "github_actions_sa_binding" {
  service_account_id = module.deploy_sa.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_pool.name}/attribute.repository/${var.github_repo}"
}

# Output the exact string you need to put into GitHub Secrets
output "github_actions_workload_identity_provider_name" {
  value = google_iam_workload_identity_pool_provider.github_provider.name
}
