# GCP Project Creation & Setup Guide

This guide details how to create the two required GCP projects for Commerce360 and link them to your active billing account.

You can choose to use either the **gcloud CLI (Recommended)** or the **GCP Console (UI)**.

---

## Option 1: Using the gcloud CLI (Recommended & Fastest)

Open your terminal. Since `gcloud` is already installed and authenticated as `stocknagraaj2@gmail.com`, run these exact commands:

**1. Create the projects:**
We use `-stock` as a suffix to make the project IDs globally unique.
```bash
gcloud projects create commerce360-ingest-dev-stock --name="Commerce360 Ingestion Dev"
gcloud projects create commerce360-analytics-dev-stock --name="Commerce360 Analytics Dev"
```

**2. Find your Billing Account ID:**
```bash
gcloud billing accounts list
# Note the ACCOUNT_ID from the output (format: XXXXXX-XXXXXX-XXXXXX)
```

**3. Link the projects to your Billing Account:**
Replace `YOUR_BILLING_ID` with the actual ID from the previous step.
```bash
gcloud billing projects link commerce360-ingest-dev-stock --billing-account=YOUR_BILLING_ID
gcloud billing projects link commerce360-analytics-dev-stock --billing-account=YOUR_BILLING_ID
```

**4. Generate Application Default Credentials (ADC)**
Terraform requires these to authenticate as you. This command will open your browser to log in one more time:
```bash
gcloud auth application-default login
```

---

## Option 2: Using the GCP Console (UI)

If you prefer clicking through the browser, follow these steps:

### 1. Create Project A (Ingestion)
1. Go to the [GCP Project Selector page](https://console.cloud.google.com/projectselector2/home/dashboard).
2. Click **Create Project**.
3. **Project name:** Enter `Commerce360 Ingestion Dev`.
4. **Project ID:** Click "Edit" below the name and set it to `commerce360-ingest-dev-stock`.
5. Select your Billing Account and Organization/Location if prompted.
6. Click **Create**.

### 2. Create Project B (Analytics)
1. Go back to the [GCP Project Selector page](https://console.cloud.google.com/projectselector2/home/dashboard).
2. Click **Create Project**.
3. **Project name:** Enter `Commerce360 Analytics Dev`.
4. **Project ID:** Click "Edit" and set it to `commerce360-analytics-dev-stock`.
5. Select your Billing Account.
6. Click **Create**.

### 3. Verify Billing
1. Go to the [Billing section](https://console.cloud.google.com/billing).
2. Go to **Account Management** (or "My Projects").
3. Ensure both `Commerce360 Ingestion Dev` and `Commerce360 Analytics Dev` are listed and have your billing account attached.

---

## Next Steps

Once the projects are created and ADC is generated, we are ready to inject these project IDs into Terraform (`terraform.tfvars`) and proceed with Phase 2 (Foundation Deployment).

