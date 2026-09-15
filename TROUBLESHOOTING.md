# GCP Commerce360 — Troubleshooting Guide

---

## T-001: 403 AccessDeniedException on GCS Cross-Project Read

**Symptom:**
```
google.api_core.exceptions.Forbidden: 403 GET https://storage.googleapis.com/...
analytics-ingestion-sa@analytics-dev.iam... does not have
storage.objects.get access to the Google Cloud Storage bucket.
```

**Cause:** The cross-project IAM binding on the Project A bucket is missing or uses the wrong member.

**Diagnosis:**
```bash
# Check current IAM bindings on the bucket
gsutil iam get gs://${RAW_BUCKET_NAME}

# Verify the SA email is correct
gcloud iam service-accounts list --project=$ANALYTICS_PROJECT_ID
```

**Fix:**
```bash
# Grant the binding (Terraform is the authoritative method; this is for emergency repair)
gsutil iam ch \
  serviceAccount:analytics-ingestion-sa@${ANALYTICS_PROJECT_ID}.iam.gserviceaccount.com:objectViewer \
  gs://${RAW_BUCKET_NAME}
```

**Then re-apply Terraform** to ensure the binding is tracked in state.

**Interview explanation:**  
In GCP, cross-project GCS access requires an IAM binding at the **bucket level** in the project that owns the bucket (Project A). The calling identity lives in Project B. There is no concept of a "cross-account role" as in AWS — the identity from Project B is granted directly on the resource in Project A. The IAM evaluation happens on the bucket's policy, checked against the calling identity's project-agnostic email.

---

## T-002: Pub/Sub Subscription Not Receiving Messages

**Symptom:** Subscription backlog shows 0 messages; topic is receiving publishes.

**Possible causes and checks:**

```bash
# 1. Confirm topic exists in Project A
gcloud pubsub topics list --project=$INGESTION_PROJECT_ID

# 2. Confirm subscription exists in Project B and references correct topic
gcloud pubsub subscriptions describe clickstream-events-sub \
  --project=$ANALYTICS_PROJECT_ID \
  --format="json" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('topic'))"
# Expected: projects/{INGESTION_PROJECT_ID}/topics/clickstream-events

# 3. Confirm IAM binding on the topic
gcloud pubsub topics get-iam-policy clickstream-events \
  --project=$INGESTION_PROJECT_ID
# Look for: role: roles/pubsub.subscriber
#           member: serviceAccount:analytics-streaming-sa@...
```

**Fix if IAM is missing:**
```bash
gcloud pubsub topics add-iam-policy-binding clickstream-events \
  --project=$INGESTION_PROJECT_ID \
  --member="serviceAccount:analytics-streaming-sa@${ANALYTICS_PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/pubsub.subscriber"
```

---

## T-003: BigQuery MERGE Scanning Too Much Data (High Cost)

**Symptom:** A Silver-layer MERGE job scans hundreds of GB; cost exceeds expectation.

**Cause:** MERGE target table has no partition filter, causing a full-table scan.

**Diagnosis:**
```sql
-- Check the job in INFORMATION_SCHEMA
SELECT
  job_id,
  total_bytes_processed,
  total_bytes_billed,
  query
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE job_type = 'QUERY'
  AND statement_type = 'MERGE'
  AND creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
ORDER BY total_bytes_billed DESC
LIMIT 10;
```

**Fix:** Add a partition filter to the MERGE target subquery:
```sql
-- Add AND T._ingestion_date >= DATE_SUB(@run_date, INTERVAL 7 DAY) to the ON clause
-- so BQ prunes the target partition scan
```

See [COST_GUIDE.md](COST_GUIDE.md) for the full MERGE cost-control pattern.

---

## T-004: Dataflow Job Stuck in RUNNING State with No Progress

**Symptom:** Dataflow job has been running for >30 minutes with no output records.

**Diagnosis:**
```bash
# View job logs for errors
gcloud logging read \
  'resource.type="dataflow_step" AND severity>=ERROR' \
  --project=$ANALYTICS_PROJECT_ID \
  --limit=20 \
  --format="table(timestamp, textPayload)"

# Check worker count (may be 0 if autoscaling failed)
gcloud dataflow jobs describe JOB_ID \
  --region=$GCP_REGION \
  --project=$ANALYTICS_PROJECT_ID \
  --format="json" | python -c "
import sys,json; d=json.load(sys.stdin)
print('Workers:', d.get('currentNumberOfWorkerHarnesses', 'N/A'))
print('State:', d.get('currentState'))
"
```

**Common causes:**
1. Worker SA missing `roles/dataflow.worker` — workers launch then immediately fail.
2. Dataflow temp GCS bucket inaccessible — workers can't stage files.
3. Pub/Sub subscription IAM missing — pipeline starts but reads 0 messages.

**Fix for each:**
```bash
# 1. Grant dataflow.worker role
gcloud projects add-iam-policy-binding $ANALYTICS_PROJECT_ID \
  --member="serviceAccount:analytics-streaming-sa@${ANALYTICS_PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/dataflow.worker"

# 2. Verify temp bucket access
gsutil ls gs://c360-df-temp-${ANALYTICS_PROJECT_ID}/

# 3. See T-002 for Pub/Sub IAM fix
```

---

## T-005: Service Account Impersonation Fails

**Symptom:**
```
google.auth.exceptions.TransportError: Unable to acquire impersonated credentials
Error: Request had insufficient authentication scopes.
```

**Cause:** The caller lacks `roles/iam.serviceAccountTokenCreator` on the target SA, or the target SA is disabled.

**Diagnosis:**
```bash
# Check if caller has TokenCreator on the target SA
gcloud iam service-accounts get-iam-policy \
  analytics-deploy-sa@${ANALYTICS_PROJECT_ID}.iam.gserviceaccount.com \
  --project=$ANALYTICS_PROJECT_ID

# Check if target SA is enabled
gcloud iam service-accounts describe \
  analytics-deploy-sa@${ANALYTICS_PROJECT_ID}.iam.gserviceaccount.com \
  --project=$ANALYTICS_PROJECT_ID \
  --format="value(disabled)"
# Expected: False (or empty)
```

**Fix:**
```bash
gcloud iam service-accounts add-iam-policy-binding \
  analytics-deploy-sa@${ANALYTICS_PROJECT_ID}.iam.gserviceaccount.com \
  --project=$ANALYTICS_PROJECT_ID \
  --member="serviceAccount:github-actions-sa@${ANALYTICS_PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountTokenCreator"
```

---

## T-006: Duplicate Records in Silver Layer

**Symptom:** `SELECT COUNT(*) FROM silver.orders` returns more rows than expected after re-run.

**Cause:** The MERGE idempotency key (`order_id` + `_record_hash`) did not deduplicate because the record hash changed between runs (e.g. `_ingestion_ts` was included in the hash).

**Diagnosis:**
```sql
-- Find duplicates
SELECT order_id, COUNT(*) AS cnt
FROM `{ANALYTICS_PROJECT_ID}.silver.orders`
GROUP BY order_id
HAVING cnt > 1
ORDER BY cnt DESC
LIMIT 20;
```

**Fix:** Verify that `_record_hash` is computed only from **business fields**, not ingestion metadata fields (`_ingestion_ts`, `_pipeline_run_id`, `_source_file`). See [`DATA_CONTRACTS.md`](DATA_CONTRACTS.md) for the hash definition.

---

## T-007: terraform apply Fails with "Project Not Found"

**Symptom:**
```
Error: Error creating Bucket: googleapi: Error 404: The specified bucket does not exist.
  OR
Error: Error setting IAM policy: googleapi: Error 403: ...
```

**Cause:** The `project_id` variable is wrong, or the project was not created before running `apply`.

**Diagnosis:**
```bash
# Verify project exists and you have access
gcloud projects describe $INGESTION_PROJECT_ID
gcloud projects describe $ANALYTICS_PROJECT_ID
```

**Fix:** Ensure:
1. Projects are created (manually or via `google_project` resource if using Option B).
2. `terraform.tfvars` (gitignored) contains the correct IDs matching the real GCP project IDs.
3. The identity running Terraform has at least `roles/editor` + `roles/iam.securityAdmin` on each project.
