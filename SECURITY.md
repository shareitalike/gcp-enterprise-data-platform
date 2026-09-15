# Security — GCP Commerce360

## Principles

1. **Least privilege at the resource level.** No pipeline identity receives project-level `roles/editor` or `roles/owner`.
2. **No long-lived service account keys.** All authentication uses ADC, WIF, or attached SAs.
3. **Uniform bucket-level access.** No ACLs on GCS buckets.
4. **Cross-project access is resource-scoped.** Project B identities are granted access on specific Project A resources only — not at the project level.
5. **Audit logging enabled from day one.** Data Access logs active on both projects.

---

## IAM Design

### Project A (Ingestion) IAM Bindings

| Resource | Member | Role | Notes |
|---|---|---|---|
| GCS raw bucket | `analytics-ingestion-sa@project-b` | `roles/storage.objectViewer` | Cross-project read only |
| Pub/Sub topic: orders-created | `analytics-streaming-sa@project-b` | `roles/pubsub.subscriber` | Cross-project subscribe |
| Pub/Sub topic: clickstream-events | `analytics-streaming-sa@project-b` | `roles/pubsub.subscriber` | Cross-project subscribe |
| Pub/Sub topics (all) | `synthetic-publisher-sa@project-a` | `roles/pubsub.publisher` | Local to Project A |

### Project B (Analytics) IAM Bindings

| Member | Role | Scope | Notes |
|---|---|---|---|
| `analytics-ingestion-sa` | `roles/bigquery.dataEditor` | bronze dataset | Write Bronze tables |
| `analytics-ingestion-sa` | `roles/bigquery.jobUser` | Project B | Run BQ load jobs |
| `analytics-streaming-sa` | `roles/dataflow.worker` | Project B | Run Dataflow workers |
| `analytics-streaming-sa` | `roles/bigquery.dataEditor` | bronze dataset | Write streaming data |
| `analytics-deploy-sa` | `roles/bigquery.admin` | Project B | Terraform-managed lifecycle |
| `analytics-deploy-sa` | `roles/storage.admin` | Dataflow temp bucket | Temp/staging files |
| GitHub WIF principal | `roles/iam.serviceAccountTokenCreator` | `analytics-deploy-sa` | CI/CD token exchange |

---

## Secrets Management

All runtime configuration that would previously be an environment variable with a sensitive
value is stored in **Cloud Secret Manager** (Project B).

Secrets stored:
- `c360/ingestion-project-id` — Project A ID (not sensitive, but centralised)
- `c360/analytics-project-id` — Project B ID
- `c360/raw-bucket-name` — GCS bucket name
- `c360/data-gen-seed` — synthetic data seed

Secrets accessed via:
```python
from google.cloud import secretmanager

client = secretmanager.SecretManagerServiceClient()
name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
response = client.access_secret_version(request={"name": name})
value = response.payload.data.decode("UTF-8")
```

No secrets are stored in `.env` files committed to git.
`.env` (git-ignored) is for local development only and contains no production values.

---

## Audit Logging

Data Access audit logs are enabled for:
- Cloud Storage (Project A): `DATA_READ`, `DATA_WRITE`
- BigQuery (Project B): `DATA_READ`, `DATA_WRITE`, `DATA_WRITE` (job execution)
- IAM (both projects): `ADMIN_READ` (for impersonation audit)

Log sink location: Default `_Default` log bucket in each project.  
Retention: 30 days in `_Default`; extend via Log Router sink to GCS for longer retention.

### Querying audit logs (cross-project GCS read events)
```sql
-- Run in Cloud Logging / Log Explorer on Project A
resource.type="gcs_bucket"
protoPayload.serviceName="storage.googleapis.com"
protoPayload.methodName="storage.objects.get"
protoPayload.authenticationInfo.principalEmail:"analytics-ingestion-sa"
```

---

## What Is Not Implemented in Dev

| Control | Status | Reason |
|---|---|---|
| VPC Service Controls | Not implemented | Adds complexity; requires Org-level setup; revisit at Phase 12 |
| Customer-Managed Encryption Keys (CMEK) | Not implemented | CMEK requires Cloud KMS; unnecessary for synthetic data |
| Binary Authorization | Not implemented | Relevant for container deployments; not applicable to this stack |
| Compliance certifications | Not claimed | This is a learning environment using synthetic data |
