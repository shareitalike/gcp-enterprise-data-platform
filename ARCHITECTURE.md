# Architecture — GCP Commerce360

## Two-Project Design

```
PROJECT A (Ingestion)                PROJECT B (Analytics)
─────────────────────                ──────────────────────────────────────
GCS raw bucket                       BigQuery: bronze / silver / gold
Pub/Sub topics                       BigQuery: control / audit / quarantine / quality
Ingestion service accounts           Analytics service accounts
Synthetic data publisher             Dataflow streaming jobs
                                     Batch load jobs (reads cross-project GCS)
                                     Data quality framework
```

### Why Two Projects?

1. **Ownership isolation** — the team managing raw ingestion infrastructure (Project A) is independent of the team managing analytics (Project B). This reflects real enterprise patterns.
2. **Billing isolation** — storage costs land on Project A; compute and BQ costs land on Project B. Cost attribution is unambiguous.
3. **IAM boundary** — Project B service accounts must be explicitly granted access to Project A resources. There is no implicit trust between projects.
4. **Security posture** — compromising a Project B analytics identity does not automatically grant access to Project A raw data. The cross-project IAM binding is the only trust bridge, and it is resource-scoped.

---

## Cross-Project Communication Mechanisms

### Mechanism 1: GCS Cross-Project Read (Batch — Phase 4)

```
Project A GCS bucket
  IAM: roles/storage.objectViewer → analytics-ingestion-sa@project-b
          │
          │ HTTP read (Google internal network)
          ▼
Project B: bq load job
  Runs as: analytics-ingestion-sa@project-b
  Charged to: Project B
          │
          ▼
Project B BigQuery bronze dataset
```

**What the cross-project IAM binding looks like (Terraform):**
```hcl
# Applied on the Project A bucket; grants Project B SA read access
resource "google_storage_bucket_iam_member" "cross_project_reader" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${var.analytics_ingestion_sa_email}"
}
```

### Mechanism 2: Pub/Sub Cross-Project Subscription (Streaming — Phase 7)

```
Project A Pub/Sub topic: projects/project-a/topics/clickstream-events
  IAM: roles/pubsub.subscriber → analytics-streaming-sa@project-b
          │
          │ Pull subscription
          ▼
Project B Pub/Sub subscription: projects/project-b/subscriptions/clickstream-sub
  Subscription is a Project B resource; it pulls from a Project A topic
  Dead-letter routing → Project B DLQ topic
          │
          ▼
Project B Dataflow → BigQuery bronze
```

**Key operational distinction from AWS SQS/SNS or Kafka:**
In Pub/Sub, the subscription is a named, IAM-controlled resource. A subscriber cannot simply connect to a topic; they must:
1. Have `roles/pubsub.subscriber` on the **topic** (Project A).
2. Own a **subscription** resource (Project B).
3. The subscription was pre-created with a reference to the cross-project topic.

---

## Data Layer Responsibilities

### GCS Raw (Project A)
- Source of truth for replay
- Immutable after landing
- 90-day lifecycle policy
- Uniform bucket-level access; no ACLs

### BigQuery Bronze (Project B)
- Queryable copy of raw files
- Append-only; never updated after load
- Partitioned by `_ingestion_date`
- Clustered by primary business key
- Schema validated before load; rejects fail to quarantine

### BigQuery Silver (Project B)
- Validated, typed, deduplicated
- MERGE-based idempotent upserts
- Invalid records → `silver_quarantine` dataset
- Preserves all audit columns from Bronze

### BigQuery Gold (Project B)
- SCD Type 2 dimensions: `dim_customer`, `dim_product`, `dim_campaign`
- Insert-only facts: `fact_orders`, `fact_order_items`, `fact_clickstream`, `fact_inventory`
- Rolled-up aggregate: `fact_daily_sales`
- Pre-generated static: `dim_date`

---

## Streaming Architecture (Phase 8)

```
Beam pipeline (Dataflow)
  Source: Cross-project Pub/Sub subscription
  ↓
  Parse + validate JSON schema
  ↓
  Deduplication (event_id within fixed window)
  ↓
  Event-time windowing (Pub/Sub event_time attribute)
  ↓
  Watermark: 10-minute allowed lateness for clickstream
             2-minute allowed lateness for orders
  ↓
  Valid records → BQ Storage Write API (at-least-once, BQ dedup via MERGE)
  Invalid records → BQ DLQ table + Pub/Sub DLQ topic
```

---

## Idempotency Strategy by Layer

| Layer | Idempotency Mechanism |
|---|---|
| GCS landing | File-level manifest in `control.file_manifest`; re-landing same file is detected and skipped |
| Bronze load | File-level check; same GCS object URI + generation number = duplicate; skipped |
| Silver MERGE | Record-level: `MERGE ON business_key AND _record_hash`; same record re-merged is a no-op |
| Gold dimensions | SCD2: new version inserted only if `_record_hash` differs |
| Gold facts | Partition-level: overwrite current day's partition on re-run |
| Streaming | Beam deduplication window + BQ `insertId` for streaming dedup |
