# Design Decisions — GCP Commerce360

This file is the Architecture Decision Record (ADR) log.
Each decision documents context, alternatives considered, rationale, and consequences.

---

## ADR-001: Two Separate GCP Projects

**Status:** Accepted  
**Date:** 2026-09-15  
**Phase:** 0

### Context
The project must teach cross-project IAM, resource ownership, billing isolation, and
cross-project communication patterns. A single project would eliminate these learning objectives.

### Decision
Use two GCP projects: one for ingestion (Project A) and one for analytics (Project B).

### Alternatives Considered
- **Single project with dataset/bucket namespacing** — simpler, but eliminates the primary
  learning objective. No cross-project IAM, no billing isolation.
- **Three projects from the start** — unnecessary complexity until Projects A and B are stable.

### Consequences
- Terraform complexity: two state backends, two provider configurations.
- Cross-project IAM bindings must be explicitly managed (cannot rely on project-level IAM).
- Billing attribution is split by design (storage costs in Project A, compute in Project B).
- Permission-denied failures are part of the learning path, not bugs.

### GCP vs. AWS Note
In AWS, cross-account S3 access uses bucket policies + IAM roles. In GCP, cross-project
GCS access uses bucket-level IAM bindings (`google_storage_bucket_iam_member`). The conceptual
model is similar, but GCP has no concept of bucket policies as a separate document — IAM
bindings on the bucket ARE the access control policy.

---

## ADR-002: BigQuery Native Load for Batch (Not Dataproc / PySpark)

**Status:** Accepted  
**Date:** 2026-09-15  
**Phase:** 0

### Context
Batch transformations (Bronze → Silver → Gold) require a processing engine.

### Decision
Use BigQuery native load jobs (GCS → BQ) and BigQuery SQL for all batch transformations.

### Alternatives Considered
- **Dataproc (standard cluster)** — PySpark is familiar but incurs per-minute cluster cost.
  A `n1-standard-4` cluster at $0.24/hr = $175/month if left running.
- **Dataproc Serverless** — no always-on cost; cold-start ~2 minutes; less operational
  overhead than standard Dataproc; viable alternative for Phase 6+ if complex Spark logic needed.
- **Cloud Run + Pandas** — workable for small data; not scalable beyond ~10M rows.

### Rationale
- BQ load from GCS is free (no slot consumption; charged only for storage after load).
- SQL transforms use BQ on-demand pricing; 1 TB free per month.
- No cluster to manage, provision, or accidentally leave running.
- BQ MERGE, SCD2, window functions, and partitioning cover all required transformation patterns.

### Consequences
- Complex Spark UDFs not available. Accepted: not required for this use case.
- BQ on-demand pricing scales with data scanned — must use partition pruning in all queries.
- Dataproc is documented as a comparison exercise, not a runtime component.

### When to Revisit
If ML feature engineering, complex graph processing, or transformations requiring Spark APIs
are added, Dataproc Serverless is the preferred upgrade path (not standard Dataproc).

---

## ADR-003: Dataflow / Apache Beam for Streaming (Not Spark Structured Streaming)

**Status:** Accepted  
**Date:** 2026-09-15  
**Phase:** 0

### Context
Clickstream events and near-real-time order events require streaming processing.

### Decision
Use Apache Beam on Google Cloud Dataflow.

### Alternatives Considered
- **Spark Structured Streaming on Dataproc** — requires always-on Dataproc cluster or
  Dataproc Serverless with cold-start latency. Spark Streaming has no native BQ Storage Write API
  integration; requires BigQuery Spark connector with additional configuration.
- **Pub/Sub → BigQuery direct subscription** — viable for simple streaming loads with no
  transformation logic. Eliminated because deduplication, schema validation, windowing,
  and dead-letter routing require a processing layer.
- **Cloud Run + Pub/Sub push** — workable for low-throughput event processing;
  not designed for stateful windowing or watermark-based late data handling.

### Rationale
- Beam is a portable abstraction: the same pipeline can run locally (DirectRunner),
  on Dataflow, or on Flink.
- Dataflow is serverless: workers scale to zero when no messages are in flight.
- Native BigQuery Storage Write API integration for high-throughput streaming writes.
- Watermark-based late-data handling is built into the Beam model.

### GCP vs. Databricks / AWS Note
- Databricks: Spark Structured Streaming on Delta Lake is the default pattern; exactly-once
  semantics via Delta transaction log. Strong if already on Databricks.
- AWS: Kinesis + Flink (Managed Service for Apache Flink) is the nearest equivalent to
  Dataflow. Pub/Sub is closer to Kinesis Data Streams than Kafka.
- Dataflow's key advantage: no worker infrastructure to manage; billing per vCPU-hour only
  when workers are running.

### Consequences
- Beam API has a learning curve, particularly for windowing and triggers.
- Dataflow costs $0.056/vCPU-hr + $0.003/GB (us-central1). A 2-worker job running 1 hour
  costs approximately $0.11. Cost is controllable via `--max_num_workers`.

---

## ADR-004: Pub/Sub Cross-Project Subscription Pattern

**Status:** Accepted  
**Date:** 2026-09-15  
**Phase:** 0

### Context
Project A produces events; Project B consumes them. How should cross-project consumption work?

### Decision
Project A owns topics. Project B creates subscriptions that pull from Project A topics.
Cross-project IAM binding: `roles/pubsub.subscriber` granted on the Project A topic
to the Project B streaming service account.

### Key Operational Distinction from Kafka
In Kafka, consumer groups are configured by the consumer; there is no pre-created
subscription resource. In Pub/Sub:
- A subscription is a named GCP resource.
- The subscription must be pre-created (by Terraform).
- The subscription references the cross-project topic by full resource name
  (`projects/project-a/topics/topic-name`).
- A subscriber must hold `roles/pubsub.subscriber` on the **topic** (Project A resource).
- Message delivery billing is charged to the **topic owner** (Project A).
- Subscription management billing is charged to the **subscription owner** (Project B).

### Why Not Have Project A Own the Subscriptions?
If Project A owns the subscriptions, Project A must manage consumer lifecycle, retry policy,
and dead-letter configuration on behalf of Project B. This couples the teams. The
cross-project subscription pattern preserves team autonomy.

---

## ADR-005: Dataplex Deferred Until Proven Necessary

**Status:** Accepted  
**Date:** 2026-09-15  
**Phase:** 0

### Context
Dataplex provides data catalog, zone enforcement, data lineage, and automated DQ scanning.

### Decision
Dataplex is not used in Phases 1–11. It will be re-evaluated at Phase 12 or later.

### Rationale
- Dataplex lake + zone + DQ scan costs approximately $50–200/month in dev.
- The platform already provides: explicit BQ dataset organisation (Bronze/Silver/Gold),
  a custom DQ framework writing results to BQ, and documented data contracts.
- Dataplex DQ scanning requires Dataplex lake/zone configuration, which adds operational
  complexity without equivalent learning value at this stage.
- GCP Data Catalog (now part of Dataplex) provides automatic BQ metadata cataloging at no
  additional cost; this is available without creating Dataplex lakes.

### When to Revisit
Phase 12 or later, if: (a) automated cross-dataset lineage is required, (b) automated
DQ scan scheduling replaces the custom framework, or (c) enterprise data catalog
discoverability is a genuine requirement.

---

## ADR-006: No Long-Lived Service Account Keys — Ever

**Status:** Accepted  
**Date:** 2026-09-15  
**Phase:** 0

### Context
Service account key files (JSON) are a significant security risk: they are long-lived,
portable, and if leaked, grant full SA permissions with no audit trail.

### Decision
No SA key files will be generated or used anywhere in this project.

### Authentication Patterns Used Instead
| Context | Authentication Method |
|---|---|
| Local development | `gcloud auth application-default login` (ADC) |
| CI/CD (GitHub Actions) | Workload Identity Federation (short-lived OIDC tokens) |
| Dataflow workers | Attached service account (implicit via GCE metadata server) |
| Cross-project impersonation | Short-lived impersonation token (1-hour TTL) via `roles/iam.serviceAccountTokenCreator` |

### GCP vs. AWS Note
AWS uses IAM roles attached to EC2/Lambda/ECS with instance metadata service (IMDS) for
credential retrieval — conceptually equivalent to GCP's attached service account pattern.
WIF is GCP's equivalent of AWS IAM Identity Provider (OIDC federation with GitHub Actions).
The key difference: WIF eliminates the need to store any long-lived credential in GitHub Secrets.
