terraform {
  required_version = ">= 1.8.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Remote state backend — GCS bucket.
  # The bucket must exist before running 'terraform init'.
  # Create it manually once: gsutil mb -p <project> gs://<bucket>
  backend "gcs" {
    bucket = ""   # set via: terraform init -backend-config="bucket=<your-state-bucket>"
    prefix = "terraform/ingestion-dev"
  }
}

provider "google" {
  project = var.ingestion_project_id
  region  = var.region
}
