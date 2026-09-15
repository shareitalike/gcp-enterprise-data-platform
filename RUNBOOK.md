# GCP Commerce360 — Operational Runbook

This runbook covers routine operational procedures for the Commerce360 platform.
For failure diagnosis, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
For detailed per-component runbooks, see [docs/runbooks/](docs/runbooks/).

---

## 1. Check Active GCP Identity

```bash
gcloud auth list
gcloud config list project
# Or via make:
make gcloud-whoami
```

Expected output confirms your ADC identity and active project.

---

## 2. Verify Cross-Project GCS Access

Run as the analytics ingestion service account (or impersonate it):

```bash
# List objects in Project A bucket from Project B identity
gsutil ls gs://${RAW_BUCKET_NAME}/customers/

# Expected: list of files (if IAM binding is correct)
# Expected failure output if IAM missing:
# AccessDeniedException: 403 analytics-ingestion-sa@... does not have ...
#   storage.objects.list access to the Google Cloud Storage bucket.
```

---

## 3. Trigger Manual Batch Load (Phase 4+)

```bash
# Load a specific date partition from GCS into BigQuery Bronze
python -m ingestion.batch.loader \
  --entity customers \
  --source-date 2024-01-15 \
  --env analytics-dev
```

Expected: `pipeline_run_id` printed; row written to `audit.pipeline_runs`.

---

## 4. Check BigQuery Dataset Freshness

```sql
-- Run in BigQuery console or via bq CLI
SELECT
  table_id,
  TIMESTAMP_MILLIS(last_modified_time) AS last_modified,
  row_count,
  size_bytes
FROM `{ANALYTICS_PROJECT_ID}.bronze.__TABLES__`
ORDER BY last_modified DESC;
```

---

## 5. Check Pub/Sub Subscription Backlog

```bash
gcloud pubsub subscriptions describe clickstream-events-sub \
  --project=$ANALYTICS_PROJECT_ID \
  --format="value(name, pushConfig, ackDeadlineSeconds)"

# Check backlog size
gcloud pubsub subscriptions describe clickstream-events-sub \
  --project=$ANALYTICS_PROJECT_ID \
  --format="json" | python -c "
import sys, json
d = json.load(sys.stdin)
print('Backlog not directly available via CLI; use Cloud Monitoring metric:')
print('  pubsub.googleapis.com/subscription/num_undelivered_messages')
"
```

---

## 6. List Running Dataflow Jobs

```bash
gcloud dataflow jobs list \
  --region=$GCP_REGION \
  --project=$ANALYTICS_PROJECT_ID \
  --status=active \
  --format="table(id,name,currentState,startTime)"
```

---

## 7. Cancel a Dataflow Job

```bash
# Replace JOB_ID with the actual job ID from step 6
gcloud dataflow jobs cancel JOB_ID \
  --region=$GCP_REGION \
  --project=$ANALYTICS_PROJECT_ID
```

Draining (graceful) vs. cancelling: use `--force` only if the job is stuck.
Draining commits in-flight windows; cancelling discards them.

---

## 8. Replay a Failed Batch File

If a file was quarantined or the Bronze load failed:

```bash
# 1. Identify the failed run
SELECT * FROM `{ANALYTICS_PROJECT_ID}.audit.pipeline_runs`
WHERE status = 'FAILED'
ORDER BY started_at DESC
LIMIT 10;

# 2. Re-trigger the load for the specific file
python -m ingestion.batch.loader \
  --entity orders \
  --source-gcs-uri gs://${RAW_BUCKET_NAME}/orders/2024-01-15/orders_20240115_001.jsonl \
  --force-reload \
  --env analytics-dev
```

`--force-reload` removes the file's manifest entry and re-processes it.

---

## 9. Rotate a Service Account (Emergency)

If an SA is suspected of compromise:

```bash
# 1. Disable the SA immediately
gcloud iam service-accounts disable \
  analytics-ingestion-sa@${ANALYTICS_PROJECT_ID}.iam.gserviceaccount.com \
  --project=$ANALYTICS_PROJECT_ID

# 2. Review audit logs for SA activity (last 24h)
gcloud logging read \
  'protoPayload.authenticationInfo.principalEmail="analytics-ingestion-sa@..."
   AND timestamp >= "2024-01-14T00:00:00Z"' \
  --project=$ANALYTICS_PROJECT_ID \
  --limit=50

# 3. Re-enable after investigation or create a replacement SA via Terraform
gcloud iam service-accounts enable \
  analytics-ingestion-sa@${ANALYTICS_PROJECT_ID}.iam.gserviceaccount.com \
  --project=$ANALYTICS_PROJECT_ID
```

---

## 10. Check Data Quality Results

```sql
SELECT
  rule_name,
  dataset_name,
  table_name,
  total_records,
  failed_records,
  ROUND(failed_records / total_records * 100, 2) AS failure_pct,
  severity,
  status,
  checked_at
FROM `{ANALYTICS_PROJECT_ID}.quality.dq_results`
WHERE checked_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
ORDER BY severity DESC, failure_pct DESC;
```
