# GCP Project Creation & Setup Guide

This guide details how to create the two required GCP projects for Commerce360 and link them to your active billing account.

You can choose to use either the **gcloud CLI (Recommended)** or the **GCP Console (UI)**.

---

## Option 1: Using the gcloud CLI (Recommended & Fastest)

Open your terminal (ensure you are authenticated via `gcloud auth login`) and run these commands.

**1. Set your variables:**
Choose globally unique project IDs. A good pattern is adding your initials or a random string at the end.
```bash
INGESTION_PROJECT="commerce360-ingest-dev-xyz"    # Replace 'xyz' with your unique string
ANALYTICS_PROJECT="commerce360-analytics-dev-xyz" # Replace 'xyz' with your unique string
```

**2. Create the projects:**
```bash
gcloud projects create $INGESTION_PROJECT --name="Commerce360 Ingestion Dev"
gcloud projects create $ANALYTICS_PROJECT --name="Commerce360 Analytics Dev"
```

**3. Find your Billing Account ID:**
```bash
gcloud billing accounts list
# Note the ACCOUNT_ID from the output (format: XXXXXX-XXXXXX-XXXXXX)
```

**4. Link the projects to your Billing Account:**
```bash
BILLING_ACCOUNT_ID="XXXXXX-XXXXXX-XXXXXX" # Replace with your actual Billing ID

gcloud billing projects link $INGESTION_PROJECT --billing-account=$BILLING_ACCOUNT_ID
gcloud billing projects link $ANALYTICS_PROJECT --billing-account=$BILLING_ACCOUNT_ID
```

---

## Option 2: Using the GCP Console (UI)

If you prefer clicking through the browser, follow these steps:

### 1. Create Project A (Ingestion)
1. Go to the [GCP Project Selector page](https://console.cloud.google.com/projectselector2/home/dashboard).
2. Click **Create Project**.
3. **Project name:** Enter `Commerce360 Ingestion Dev`.
4. **Project ID:** Click "Edit" below the name and set it to something unique like `commerce360-ingest-dev-xyz`. **(Write this ID down)**.
5. Select your Billing Account and Organization/Location if prompted.
6. Click **Create**.

### 2. Create Project B (Analytics)
1. Go back to the [GCP Project Selector page](https://console.cloud.google.com/projectselector2/home/dashboard).
2. Click **Create Project**.
3. **Project name:** Enter `Commerce360 Analytics Dev`.
4. **Project ID:** Click "Edit" and set it to something unique like `commerce360-analytics-dev-xyz`. **(Write this ID down)**.
5. Select your Billing Account.
6. Click **Create**.

### 3. Verify Billing
1. Go to the [Billing section](https://console.cloud.google.com/billing).
2. Go to **Account Management** (or "My Projects").
3. Ensure both `Commerce360 Ingestion Dev` and `Commerce360 Analytics Dev` are listed and have your billing account attached.

---

## Next Steps

Once the projects are created, provide the two Project IDs to the agent so they can be injected into the Terraform configurations (`terraform.tfvars`) to proceed with Phase 2.
