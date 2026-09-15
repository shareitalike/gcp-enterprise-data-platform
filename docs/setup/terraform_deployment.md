# Phase 2: Terraform Infrastructure Deployment Runbook

This document tracks the exact commands executed to deploy the GCP foundation for both the Ingestion and Analytics environments.

## Prerequisites
You must have completed the steps in `project_creation.md` (created projects, linked billing, and authenticated via ADC).

## 1. Create the Terraform State Bucket
Terraform needs a central place to store its state file. We create this bucket in the Ingestion project.

```bash
gcloud storage buckets create gs://c360-tfstate-alvi \
  --project=commerce360-ingest-dev-alvi \
  --location=us-central1 \
  --uniform-bucket-level-access
```

## 2. Configure Environment Variables (`terraform.tfvars`)

### Ingestion Environment
File: `infra/terraform/environments/ingestion-dev/terraform.tfvars`
```hcl
ingestion_project_id         = "commerce360-ingest-dev-alvi"
analytics_ingestion_sa_email = ""   # fill in after analytics-dev stack is applied
analytics_streaming_sa_email = ""   # fill in after analytics-dev stack is applied
region                       = "us-central1"
environment                  = "dev"
```

### Analytics Environment
File: `infra/terraform/environments/analytics-dev/terraform.tfvars`
```hcl
analytics_project_id = "commerce360-analytics-dev-alvi"
ingestion_project_id = "commerce360-ingest-dev-alvi"
region               = "us-central1"
environment          = "dev"
```

## 3. Initialize and Plan Ingestion Environment
Initialize the backend to use the GCS bucket we created, then generate the plan.

```bash
cd infra/terraform/environments/ingestion-dev
terraform init -backend-config="bucket=c360-tfstate-alvi"
terraform plan
```

## 4. Initialize and Plan Analytics Environment
Repeat the process for the Analytics environment. It uses the same state bucket but a different prefix (handled internally by Terraform).

```bash
cd ../analytics-dev
terraform init -backend-config="bucket=c360-tfstate-alvi"
terraform plan
```

## 5. Apply the Infrastructure (Pending)
Once the plans are reviewed, we apply them in order (Ingestion first, then Analytics).

```bash
# Apply Ingestion
cd ../ingestion-dev
terraform apply -auto-approve

# Apply Analytics
cd ../analytics-dev
terraform apply -auto-approve
```
