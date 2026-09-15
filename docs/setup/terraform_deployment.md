# Phase 2: Terraform Infrastructure Deployment Runbook

This document tracks the exact commands executed to deploy the GCP foundation for both the Ingestion and Analytics environments.

## Prerequisites
You must have completed the steps in `project_creation.md` (created projects, linked billing, and authenticated via ADC).

## 1. Create the Terraform State Bucket
Terraform needs a central place to store its state file. We create this bucket in the Ingestion project.

```bash
# `gcloud storage buckets create` creates a new Google Cloud Storage (GCS) bucket.
# `gs://c360-tfstate-alvi` is the globally unique name of the bucket.
# `--project=...` tells GCP which project owns this bucket.
# `--location=us-central1` ensures data stays in a specific geographical region.
# `--uniform-bucket-level-access` forces all access control to use IAM (Identity and Access Management) 
#   rather than legacy per-file Access Control Lists (ACLs). This is a best practice for security.
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

## 5. Apply the Infrastructure

Because these two projects are deeply linked (Analytics creates Service Accounts that Ingestion needs, and Ingestion creates Pub/Sub topics that Analytics needs), we must apply them in a staggered order.

### Step 5a: Apply Analytics to create Service Accounts
This will fail halfway through (Error 404: Topic not found) because it tries to create Subscriptions for Topics that don't exist yet. That's expected! We just need it to create the Service Accounts first.
```bash
cd ../analytics-dev
terraform apply -auto-approve
```

### Step 5b: Update Ingestion Variables
Copy the Service Account emails generated from Step 5a into your Ingestion `terraform.tfvars`:
```hcl
analytics_ingestion_sa_email = "analytics-ingestion-sa@commerce360-analytics-dev-alvi.iam.gserviceaccount.com"
analytics_streaming_sa_email = "analytics-streaming-sa@commerce360-analytics-dev-alvi.iam.gserviceaccount.com"
```

### Step 5c: Apply Ingestion completely
This creates the Pub/Sub topics, the Raw GCS bucket, and grants the cross-project permissions to the Analytics Service Accounts.
```bash
cd ../ingestion-dev
terraform apply -auto-approve
```

### Step 5d: Finish applying Analytics
Run apply in Analytics one more time. Now that the Ingestion Pub/Sub topics exist, the Analytics subscriptions will be successfully created and attached to them.
```bash
cd ../analytics-dev
terraform apply -auto-approve
```
