# Cost Guide — GCP Commerce360

## Principles

1. Always-on compute is the primary cost risk. Avoid it.
2. BQ on-demand pricing scales with data scanned. Use partition pruning in every query.
3. Dataflow must always have `--max_num_workers` bounded.
4. Composer is deferred until justified. It is the single largest fixed cost.
5. Check current GCP pricing in your selected region before deployment.
   Prices in this document are directional estimates only.

---

## Cost Risk by Phase (us-central1, directional estimates)

| Phase | Resources | Monthly Cost Estimate | Risk Level |
|---|---|---|---|
| 1 | None (local only) | $0 | None |
| 2 | 2 GCS buckets, 6 BQ datasets, 4 SAs | < $1 | Low |
| 3 | Data generator (local) | $0 | None |
| 4 | GCS storage (< 100 MB), BQ load jobs | < $1 | Low |
| 5–6 | BQ MERGE queries on small data | $0–$3 | Low (free tier covers it) |
| 7 | 2 Pub/Sub topics, 1 DLQ, subscriptions | < $1 | Low (free tier: 10 GB/month) |
| 8 | Dataflow 2-worker job (test runs only) | $3–$10 per test run | Medium |
| 9 | WIF config, short-lived token exchange | $0 | None |
| 10 | **Composer environment** | **$50–$150/month** | **HIGH — deferred** |
| 11 | Cloud Monitoring dashboards, log queries | < $5 | Low |
| Total Phases 1–9 | — | **< $20/month** | Low (with discipline) |

---

## BigQuery Cost Controls

### Partition pruning is mandatory
Every query against a partitioned table MUST filter on the partition column.

```sql
-- ✅ Correct — partition pruned
SELECT * FROM `project.bronze.raw_orders`
WHERE _ingestion_date = '2024-01-15'

-- ❌ Wrong — full table scan, charges for all partitions
SELECT * FROM `project.bronze.raw_orders`
WHERE order_status = 'SHIPPED'
```

### MERGE cost behaviour
`MERGE` scans the entire target table unless filtered. On large Silver tables:
- Always include a date predicate in the `MERGE` target subquery.
- Use `_ingestion_date` or `order_date` partition to limit the scan window.

```sql
-- ✅ Cost-controlled MERGE — limits target scan to relevant partition range
MERGE `project.silver.orders` T
USING (
  SELECT * FROM `project.bronze.raw_orders`
  WHERE _ingestion_date = @run_date
) S
ON T.order_id = S.order_id
  AND T._ingestion_date >= DATE_SUB(@run_date, INTERVAL 7 DAY)
WHEN MATCHED AND T._record_hash != S._record_hash THEN UPDATE SET ...
WHEN NOT MATCHED THEN INSERT ...
```

### On-demand vs. flat-rate
- On-demand: $6.25/TB scanned (check current pricing). Appropriate for dev.
- Flat-rate slots: only cost-effective above ~$2,000/month of on-demand spending.
- Do not buy slots for this project.

---

## Dataflow Cost Controls

- Always set `--max_num_workers=2` in dev.
- Always set `--machine_type=n1-standard-1` in dev.
- Shut down Dataflow jobs after testing. Jobs in DRAINING state still incur cost.
- Use Dataflow Flex Templates rather than streaming jobs left running overnight.

Approximate cost for a 2-worker, n1-standard-1 Dataflow job (us-central1):
- vCPU: 2 × 1 vCPU × $0.056/vCPU-hr = $0.112/hr
- Memory: 2 × 3.75 GB × $0.003/GB-hr = $0.0225/hr
- **Total: ~$0.13/hr per test run**

---

## Storage Cost Controls

| Storage | Estimated Size (dev) | Monthly Cost |
|---|---|---|
| GCS raw (Project A) | < 500 MB | < $0.01 |
| Dataflow temp GCS | < 200 MB (cleaned up) | < $0.01 |
| BQ Bronze (6 months) | < 1 GB | < $0.02 |
| BQ Silver | < 500 MB | < $0.01 |
| BQ Gold | < 200 MB | < $0.01 |
| **Total** | **< 3 GB** | **< $0.10** |

BQ active storage: $0.020/GB/month. First 10 GB free.
GCS Standard: $0.020/GB/month. First 5 GB free.

---

## Budget Alert Setup (Phase 2)

Set a billing budget alert on each project:
- Alert at 50% of $20 threshold = $10
- Alert at 100% = $20
- Auto-shutdown is NOT configured (too risky for running pipeline tests)
- Manual review triggered when alert fires

```bash
# Set a budget alert (requires Billing Account Admin)
# Command provided in Phase 2 Terraform
```

---

## Cleanup Commands

After completing any cloud testing phase, run:

```bash
# Stop all Dataflow jobs
gcloud dataflow jobs list --region=us-central1 --status=active \
  --project=$ANALYTICS_PROJECT_ID \
  --format="value(id)" | xargs -I{} gcloud dataflow jobs cancel {} \
  --region=us-central1 --project=$ANALYTICS_PROJECT_ID

# Delete generated GCS objects (Project A)
gsutil -m rm -r gs://$RAW_BUCKET_NAME/generated/

# List BQ tables by dataset (verify before deletion)
bq ls --project_id=$ANALYTICS_PROJECT_ID bronze
```
