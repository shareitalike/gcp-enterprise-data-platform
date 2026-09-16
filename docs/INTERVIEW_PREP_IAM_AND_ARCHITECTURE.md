# Interview Prep: IAM, Service Accounts & Cross-Project Architecture

This document is specifically written to help you answer interview questions confidently. Read it, understand the "why", and practice explaining it out loud.

---

## Question: "What is a Service Account and how is it different from a normal IAM user?"

### The Simple Answer (say this first):
> *"A normal IAM user is a human with a Gmail or Google Workspace account — they log in with a username and password. A Service Account is a non-human identity — a robot account — used by applications, pipelines, and VMs to authenticate and call GCP APIs without any human typing a password."*

### The Deep Dive (follow up with this):

| Feature | Normal IAM User | Service Account |
|---|---|---|
| **Who uses it?** | A human logging in | An application / pipeline / VM |
| **How it authenticates** | Username + password + MFA | Cryptographic key or metadata server (no password) |
| **Lives in** | Google's identity system (outside GCP) | Directly inside a GCP Project |
| **Can be given roles?** | Yes | Yes |
| **Can be a Principal granting access to others?** | Yes | Yes — it can also *act as* a member |
| **Example** | `alvigeorge2@gmail.com` | `analytics-ingestion-sa@commerce360-analytics-dev-alvi.iam.gserviceaccount.com` |

### What we have in our project:
| Service Account | Project | Role It Has | Purpose |
|---|---|---|---|
| `synthetic-publisher-sa` | Ingestion (A) | `roles/pubsub.publisher` | Publishes fake order/clickstream events to Pub/Sub |
| `analytics-ingestion-sa` | Analytics (B) | `roles/bigquery.dataEditor`, `roles/storage.objectViewer` (cross-project) | Reads raw files from GCS (Project A) and loads them into BigQuery |
| `analytics-streaming-sa` | Analytics (B) | `roles/bigquery.dataEditor`, `roles/pubsub.subscriber` (cross-project) | Subscribes to Pub/Sub topics in Project A and writes stream to BigQuery |

---

## Question: "How do you create a Service Account?"

### 🖥️ CLI Steps (exactly what you type):
```bash
# Step 1: Create the Service Account
gcloud iam service-accounts create analytics-ingestion-sa \
    --display-name="Analytics Ingestion SA" \
    --description="Reads raw files from GCS and loads into BigQuery" \
    --project=commerce360-analytics-dev-alvi

# The above creates a service account with the email:
# analytics-ingestion-sa@commerce360-analytics-dev-alvi.iam.gserviceaccount.com

# Step 2: Grant it a project-level role (within the same project)
gcloud projects add-iam-policy-binding commerce360-analytics-dev-alvi \
    --member="serviceAccount:analytics-ingestion-sa@commerce360-analytics-dev-alvi.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataEditor"
```

### 🖱️ GUI Steps (step by step):
1. Go to **console.cloud.google.com** and make sure you're in the **`commerce360-analytics-dev-alvi`** project.
2. In the left sidebar: **IAM & Admin** -> **Service Accounts**.
3. Click **"+ CREATE SERVICE ACCOUNT"** (blue button at the top).
4. Fill in:
   - **Service account name**: `analytics-ingestion-sa`
   - **Description**: `Reads raw files from GCS and loads into BigQuery`
   - Click **CREATE AND CONTINUE**.
5. On the next screen, add the role `BigQuery Data Editor`. Click **CONTINUE** then **DONE**.

> **Interview Tip:** Tell the interviewer you prefer to manage service accounts via Terraform so they are version-controlled and reproducible. We did exactly this — the service account creation code is in `infra/terraform/modules/service_account/main.tf`.

---

## Question: "How do two separate GCP projects communicate securely? How does it work here vs in production?"

### Our Dev Setup (Shared VPC not required, IAM-only cross-project):
The two projects are completely isolated by default. To allow them to communicate, we use **cross-project IAM bindings**. No data physically travels between "networks" — everything goes through GCP's internal API layer.

Here's the exact flow for batch ingestion:

```
Project A (Ingestion)                     Project B (Analytics)
─────────────────────                     ──────────────────────
GCS Bucket                                analytics-ingestion-sa
  - IAM Policy says:        ────────────>   runs load_bronze.py
    "analytics-ingestion-sa               which reads from GCS
     can VIEW objects here"               and writes to BigQuery
```

**How the cross-project IAM binding was created (Terraform code):**
```hcl
# In infra/terraform/environments/ingestion-dev/main.tf
# This is in PROJECT A's Terraform, but it grants PROJECT B's SA access
resource "google_storage_bucket_iam_member" "cross_project_read" {
  bucket = module.raw_bucket.bucket_name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:analytics-ingestion-sa@commerce360-analytics-dev-alvi.iam.gserviceaccount.com"
}
```

**How the cross-project IAM binding was created (CLI equivalent):**
```bash
# You run this from the INGESTION project (Project A)
# You are granting Project B's service account access to Project A's bucket
gcloud storage buckets add-iam-policy-binding gs://c360-raw-commerce360-ingest-dev-alvi \
    --member="serviceAccount:analytics-ingestion-sa@commerce360-analytics-dev-alvi.iam.gserviceaccount.com" \
    --role="roles/storage.objectViewer"
```

> **Key Point:** The resource lives in Project A. The identity (SA) lives in Project B. You grant access in Project A's IAM policy to Project B's SA. This is cross-project IAM and it's a very common interview topic.

---

## Question: "How would this look in a real production environment?"

In production, the setup becomes more sophisticated on **three dimensions**:

### 1. Authentication: From ADC to Workload Identity Federation (WIF)
| Dev (Our Setup) | Production |
|---|---|
| We use `gcloud auth application-default login` (your personal laptop credentials) | VMs/Cloud Run/GKE pods authenticate using **Workload Identity Federation**. The compute resource's identity IS the Service Account — no key file is ever stored anywhere. |
| We use `GOOGLE_IMPERSONATE_SERVICE_ACCOUNT` env var to simulate a SA locally | In production, you never impersonate via env vars. The `metadata server` on the VM automatically provides SA tokens. |

**In production, a GCE VM gets its identity like this:**
```bash
# On a VM that is "running as" analytics-ingestion-sa, 
# you never need to set any env vars.
# The SDK automatically calls the metadata server:
# http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/

# On a GKE pod, you map the K8s ServiceAccount to a GCP Service Account:
gcloud iam service-accounts add-iam-policy-binding analytics-ingestion-sa@... \
    --member="serviceAccount:my-gcp-project.svc.id.goog[my-namespace/my-ksa]" \
    --role="roles/iam.workloadIdentityUser"
```

### 2. Network: VPC Service Controls
In production, companies add an additional security layer on top of IAM:
- **VPC Service Controls** creates an invisible "perimeter" around a group of projects.
- Even if you have the right IAM role, if your request comes from *outside the perimeter* (e.g. a different company's project or a suspicious IP), it is blocked.
- In our dev setup, we don't use VPC Service Controls because it requires an Organization and adds cost.

### 3. Project Structure: More Environments
In production, instead of just `ingestion-dev` and `analytics-dev`, you'd have:

```
commerce360-ingest-dev       <-- we have this
commerce360-ingest-staging
commerce360-ingest-prod

commerce360-analytics-dev    <-- we have this
commerce360-analytics-staging
commerce360-analytics-prod
```
Each environment is a completely separate GCP project with its own IAM, its own GCS buckets, and its own BigQuery datasets. CI/CD pipelines promote code from dev -> staging -> prod automatically.

---

## Quick Interview Answers Cheat Sheet

| Question | Answer |
|---|---|
| "What is a service account?" | A non-human robot identity used by applications to call GCP APIs without passwords. |
| "How does a service account authenticate?" | Via cryptographic short-lived tokens. In production, via the compute metadata server (no key files). |
| "What is Principle of Least Privilege?" | Each service account only has the minimum permissions needed. Our `publisher-sa` can only publish, it cannot read BigQuery. |
| "How do two GCP projects talk to each other?" | Through cross-project IAM bindings. Resource is in Project A, the identity (SA) is in Project B, you add the SA as a member in Project A's IAM policy. |
| "What is cross-project IAM?" | Granting a Service Account from one project a role on a resource in a different project. |
| "How does this differ from production?" | Production uses Workload Identity Federation instead of impersonation, VPC Service Controls for network-level isolation, and multiple environment projects (dev/staging/prod). |
