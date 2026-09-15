# Interview Notes — GCP Commerce360

Each section maps to a likely senior Data Engineering / GCP architect interview question.
Notes are added as each component is built and tested.

---

## Q: Why two GCP projects instead of one?

**Answer structure:**
1. The primary reason is cross-project IAM — it is the core learning and interview demonstration objective.
2. In real enterprises, the team managing raw data ingestion infrastructure is separate from the analytics team. Two projects enforce that boundary technically, not just organizationally.
3. Billing isolation: storage costs attributable to Project A; compute and analytics costs to Project B. This matters for chargeback and cost attribution.
4. Security posture: compromising a Project B analytics identity does not automatically grant access to Project A raw data. The cross-project IAM binding is the only trust bridge.
5. In GCP, project boundaries are the primary unit of IAM isolation. Unlike AWS where you can have fine-grained account structures with Organizations, GCP projects are lightweight and cheap to create.

---

## Q: How does cross-project GCS access work in GCP? How is it different from AWS?

**Answer structure:**
- In GCP, you add an IAM binding on the **bucket** in the source project, specifying the consuming identity.
- In AWS, you use a **bucket policy** (resource-based policy) + the consuming account's IAM role (identity-based policy). Both must allow the access.
- Key GCP difference: there is no separate "bucket policy document" — the IAM bindings on the bucket are the policy. This simplifies the model but means IAM bindings must be managed carefully.
- The calling identity (Project B SA) evaluates permissions from the **resource's project** (Project A).
- Audit logs for the cross-project read appear in **Project A** (where the resource is), not Project B.

---

## Q: How does Pub/Sub cross-project subscription work? What is the difference from Kafka?

(See [`docs/cross_project_iam/pubsub_cross_project.md`](../cross_project_iam/pubsub_cross_project.md))

**Key interview points:**
- In Pub/Sub, subscriptions are **resources** — named, IAM-controlled, owned by a project.
- A cross-project subscription lives in Project B but references a Project A topic by full resource name.
- The subscriber needs `roles/pubsub.subscriber` on the **topic** (Project A resource).
- In Kafka, consumer groups are not resources — they are configured by the consumer at runtime. No pre-creation required. IAM is replaced by Kafka ACLs (optional).
- Pub/Sub guarantees at-least-once delivery. Exactly-once requires application-level deduplication (by `message_id`) or use of the BigQuery Storage Write API with deduplication semantics.

---

## Q: When would you use Dataflow vs. Spark Structured Streaming on Dataproc?

**Use Dataflow when:**
- You want serverless (no cluster to manage)
- You already use Apache Beam and want portability
- You need native BQ Storage Write API integration
- Cost is proportional to message volume (no idle cluster cost)

**Use Dataproc when:**
- You have complex Spark-specific operations (MLlib, GraphX, complex window UDFs)
- Your team is already expert in PySpark and Spark Structured Streaming
- You need tight integration with Hive metastore or HDFS
- You require exactly-once semantics via Delta Lake transaction log

**Key trade-off:**
Dataproc has per-minute cluster cost even when idle. Dataflow scales to zero.
For a streaming pipeline with variable throughput, Dataflow is almost always cheaper.

---

## Q: What is the difference between at-least-once delivery and exactly-once processing?

**At-least-once:** The system guarantees every message is delivered at least once. Duplicates are possible (e.g. worker failure before ack). The consumer must handle duplicates.

**Exactly-once processing semantics (Beam):** Beam's runner model provides exactly-once semantics within the pipeline graph — each element is processed exactly once even in the presence of retries. This does NOT guarantee exactly-once side effects (e.g. external writes).

**Effectively-once business outcome:** The BigQuery Storage Write API (used by Dataflow) supports deduplication by `row_offset` within a stream. Combining this with application-level `event_id` deduplication in a MERGE achieves an effectively-once outcome for the business result, even under at-least-once delivery.

**In an interview:** Never say "exactly once" without qualifying what layer you mean. A Pub/Sub message can be delivered more than once. Exactly-once at the Beam processing layer does not mean exactly once in the sink.

---

## Q: How do you prevent a MERGE from scanning the entire BigQuery table?

1. Add a date filter on the target table in the `ON` clause.
2. Use `DATE_SUB(@run_date, INTERVAL 7 DAY)` as a lookback window to handle late updates.
3. Ensure the target table is partitioned by a date column (e.g. `order_date`).
4. BQ will prune partitions based on the filter — verify with `INFORMATION_SCHEMA.JOBS` `total_bytes_processed`.
5. Never use `MERGE INTO full_table USING staging ON key` without a partition filter on a large table.

---

## Q: What is Workload Identity Federation and why use it instead of SA keys?

**SA keys problem:** JSON key files are long-lived credentials. If leaked (GitHub, CI logs, local disk), they grant full SA permissions until manually rotated. GCP has no built-in key leak detection.

**WIF solution:** The CI/CD system (GitHub Actions) presents an OIDC token to GCP's STS. GCP exchanges it for a short-lived GCP credential (1 hour). No long-lived credential exists anywhere. The token exchange is logged in IAM audit logs.

**Required setup:**
1. Create a Workload Identity Pool in GCP.
2. Add a GitHub OIDC provider to the pool.
3. Grant the pool's principal `roles/iam.workloadIdentityUser` on the deploy SA.
4. Grant the deploy SA `roles/iam.serviceAccountTokenCreator` (for impersonation) if needed.

**AWS equivalent:** IAM Identity Provider with OIDC + IAM role trust policy. Conceptually identical.
