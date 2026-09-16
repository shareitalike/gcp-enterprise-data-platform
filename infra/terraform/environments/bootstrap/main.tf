# ── Terraform State Bootstrap ─────────────────────────────────────────────────
# Run this ONCE before any other terraform environment.
# Creates the GCS bucket that will store all Terraform state files.
#
# Usage:
#   cd infra/terraform/environments/bootstrap
#   terraform init
#   terraform apply -auto-approve
# ─────────────────────────────────────────────────────────────────────────────

terraform {
  required_version = ">= 1.8.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  # Bootstrap has NO backend block — state is stored locally by design.
  # This is the only environment allowed to have local state.
}

provider "google" {
  project = var.analytics_project_id
  region  = var.region
}

variable "analytics_project_id" {
  description = "GCP Project ID for Project B (Analytics). The state bucket is created here."
  type        = string
}

variable "region" {
  description = "GCP region."
  type        = string
  default     = "us-central1"
}

locals {
  # Globally unique bucket name using the project ID
  state_bucket_name = "c360-tf-state-${var.analytics_project_id}"
}

# The single GCS bucket that stores all Terraform state
resource "google_storage_bucket" "terraform_state" {
  project                     = var.analytics_project_id
  name                        = local.state_bucket_name
  location                    = "US"
  uniform_bucket_level_access = true
  force_destroy               = false

  # Versioning is critical — it lets you roll back to previous state if corrupted
  versioning {
    enabled = true
  }

  # Keep old state versions for 90 days for disaster recovery
  lifecycle_rule {
    condition {
      num_newer_versions = 5
      with_state         = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    managed_by  = "terraform"
    purpose     = "terraform-state"
    environment = "shared"
  }
}

output "state_bucket_name" {
  value       = google_storage_bucket.terraform_state.name
  description = "Pass this value as -backend-config=\"bucket=<value>\" when running terraform init in other environments."
}
