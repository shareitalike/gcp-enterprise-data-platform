terraform {
  required_version = ">= 1.8.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = ""   # set via: terraform init -backend-config="bucket=<your-state-bucket>"
    prefix = "terraform/analytics-dev"
  }
}

provider "google" {
  project = var.analytics_project_id
  region  = var.region
}
