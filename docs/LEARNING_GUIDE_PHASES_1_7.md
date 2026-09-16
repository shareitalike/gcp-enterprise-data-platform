# Commerce360: Hands-On Learning Guide (Phases 1 - 7)

This document is your cheat sheet for interview preparation. It explains exactly what we did under the hood, providing both the **CLI commands** I ran and the **GUI steps** you would use to do the exact same things manually in the Google Cloud Console.

---

## 1. Project Creation & Authentication (Phases 1-2)
We created two separate projects to demonstrate a highly secure, enterprise-grade architecture where Ingestion and Analytics are isolated.

**What we did:**
- Created `commerce360-ingest-dev-alvi` and `commerce360-analytics-dev-alvi`.
- Linked them to your billing account.
- Enabled necessary APIs (BigQuery, GCS, Pub/Sub).

### 🖥️ CLI Approach:
```bash
# Create projects
gcloud projects create commerce360-ingest-dev-alvi
gcloud projects create commerce360-analytics-dev-alvi

# Link billing account
gcloud beta billing projects link commerce360-ingest-dev-alvi --billing-account=01C28A-FD425B-861407

# Enable APIs
gcloud services enable bigquery.googleapis.com storage.googleapis.com pubsub.googleapis.com --project=commerce360-ingest-dev-alvi
```

### 🖱️ GUI Approach:
1. Open GCP Console, click the Project Dropdown at the top -> **New Project**.
2. Go to **Billing** -> Account Management -> Link the new project.
3. Go to **APIs & Services** -> Library -> Search for "BigQuery" and click **Enable**.

---

## 2. Infrastructure as Code / Terraform (Phase 2)
Instead of clicking through the UI to create buckets and datasets, we used **Terraform**. This is a massive selling point in interviews because it shows you understand **DevOps/GitOps best practices** (reproducibility, version control, and infrastructure automation).

Our Terraform code is split into two environments to match our two projects:
1. `infra/terraform/environments/ingestion-dev`
2. `infra/terraform/environments/analytics-dev`

**The "Chicken and Egg" Problem & How We Solved It:**
We had a dependency loop: The Analytics project needs to subscribe to Pub/Sub topics that exist in the Ingestion project. But the Ingestion project needs to grant IAM access to a Service Account that exists in the Analytics project. 

Here is exactly what we ran, and why:

### 🖥️ CLI Approach:

**Step 1: Create the base Ingestion infrastructure**
```bash
cd infra/terraform/environments/ingestion-dev
terraform init
terraform apply -auto-approve
```
*What happens here?* Terraform talks to the GCP API and creates the `c360-raw-...` Cloud Storage bucket, the `synthetic-publisher-sa` service account, and the `orders-created` / `clickstream-events` Pub/Sub topics in Project A.

**Step 2: Create the Analytics infrastructure**
```bash
cd ../analytics-dev
terraform init
terraform apply -auto-approve
```
*What happens here?* Terraform creates the BigQuery datasets (`bronze`, `silver`, `gold`), the `analytics-ingestion-sa` and `analytics-streaming-sa` service accounts, and the Pub/Sub Subscriptions in Project B. Crucially, it links those subscriptions to the topics we created in Step 1.

**Step 3: Close the loop (Cross-Project IAM)**
```bash
cd ../ingestion-dev
# We updated the terraform.tfvars file here to paste in the emails of the 
# Service Accounts created in Step 2.
terraform apply -auto-approve
```
*What happens here?* Terraform runs again in Project A. It sees the new Service Account emails and attaches IAM policies granting Project B's `analytics-ingestion-sa` the `Storage Object Viewer` role on the GCS bucket, and `analytics-streaming-sa` the `Pub/Sub Subscriber` role on the topics.

### 🖱️ GUI Approach (How to verify it worked):
1. Go to **IAM & Admin** -> **IAM** in the `commerce360-ingest-dev-alvi` project.
2. Check the box for **"Include Google-provided role grants"** or look at the principals list.
3. You will actually see the `analytics-ingestion-sa@commerce360-analytics-dev-alvi...` service account listed there with the **Storage Object Viewer** role, proving that cross-project access was successfully granted!

---

## 3. Data Generation & Uploading to GCS (Phase 3)
We generated synthetic E-commerce data (JSON files) and uploaded them to the Cloud Storage data lake.

**What we did:**
- Generated data using our Python script.
- Uploaded it to `gs://c360-raw-commerce360-ingest-dev-alvi/`.

### 🖥️ CLI Approach:
```bash
# Uploading to GCS using gsutil (gcloud storage)
gcloud storage cp -r data/generated/small/* gs://c360-raw-commerce360-ingest-dev-alvi/
```

### 🖱️ GUI Approach:
1. Go to **Cloud Storage** -> **Buckets**.
2. Click on `c360-raw-commerce360-ingest-dev-alvi`.
3. Click **Upload Folder** and select the local `data/generated/small` folder.

---

## 4. Loading Data into Bronze (Phase 4)
We took the raw JSON files from GCS and loaded them into BigQuery native tables using BigQuery Load Jobs.

**What we did:**
- We ran `load_bronze.py`, which uses the BigQuery Python SDK to execute a load job.

### 🖥️ CLI Approach (Using `bq` tool):
```bash
bq load \
  --source_format=NEWLINE_DELIMITED_JSON \
  --autodetect \
  commerce360-analytics-dev-alvi:bronze.orders \
  gs://c360-raw-commerce360-ingest-dev-alvi/orders/dt=2024-01-15/*.json
```

### 🖱️ GUI Approach:
1. Go to **BigQuery** -> **SQL Workspace**.
2. Expand your Analytics project -> click the `bronze` dataset -> click **Create Table**.
3. Create table from: **Google Cloud Storage**.
4. Select the GCS path, set File format to **JSONL**, type the table name (`orders`), and check **Auto-detect Schema**. Click Create.

---

## 5. Medallion Architecture: Silver & Gold (Phase 5 & 6)
We transformed raw Bronze data into deduplicated Silver tables, and then aggregated it into Gold fact/dimension tables.

**What we did:**
- We wrote complex `MERGE` SQL statements.
- The `MERGE` statements ensure **idempotency** (you can run them 100 times, and it won't duplicate data; it will just update existing rows or insert new ones).

### 🖥️ CLI Approach:
```bash
# Running a query from a file
bq query --use_legacy_sql=false < pipelines/sql/silver/silver_orders.sql
```

### 🖱️ GUI Approach:
1. Go to **BigQuery** -> **SQL Workspace**.
2. Open a new query tab.
3. Copy-paste the SQL code from `pipelines/sql/silver/silver_orders.sql` into the editor.
4. Click **RUN**. You will see the "Query results" tab showing how many rows were inserted/updated.

---

## 6. Pub/Sub Cross-Project Streaming (Phase 7)
We verified our real-time messaging queue. Project A (Ingestion) owns the Topics, and Project B (Analytics) owns the Subscriptions.

**What we did:**
- Published mock JSON events to the `orders-created` topic in Project A.
- Pulled those events from the `orders-created-sub` subscription in Project B.

### 🖥️ CLI Approach:
```bash
# Publish a message
gcloud pubsub topics publish orders-created \
    --project=commerce360-ingest-dev-alvi \
    --message='{"order_id": "123", "total_amount": 50.00}'

# Pull the message from the other project
gcloud pubsub subscriptions pull orders-created-sub \
    --project=commerce360-analytics-dev-alvi \
    --limit=1 \
    --auto-ack
```

### 🖱️ GUI Approach:
**To Publish:**
1. Switch to `commerce360-ingest-dev-alvi` project.
2. Go to **Pub/Sub** -> **Topics**.
3. Click `orders-created` -> **Messages** tab -> **Publish Message**. Type raw JSON and hit Publish.

**To Pull (Read):**
1. Switch to `commerce360-analytics-dev-alvi` project.
2. Go to **Pub/Sub** -> **Subscriptions**.
3. Click `orders-created-sub` -> **Messages** tab -> **Pull**. You will see the message you just published!
