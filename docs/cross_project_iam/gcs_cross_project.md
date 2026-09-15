# Cross-Project GCS Access — IAM Guide

## What This Covers

How a Project B service account reads files from a GCS bucket owned by Project A.

This is the **first cross-project IAM exercise** (Phase 4).

---

## Resource Ownership

| Resource | Owner | Created by |
|---|---|---|
| GCS raw bucket | Project A | Terraform (ingestion-dev stack) |
| GCS objects (files) | Project A | Data generator |
| `analytics-ingestion-sa` | Project B | Terraform (analytics-dev stack) |
| BigQuery load job | Project B | Batch loader script |
| BigQuery Bronze table | Project B | Batch loader script |

---

## The IAM Binding That Makes It Work

```hcl
# Applied on the Project A bucket — grants Project B SA read access
resource "google_storage_bucket_iam_member" "cross_project_reader" {
  bucket = "c360-raw-<ingestion-project-id>"
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:analytics-ingestion-sa@<analytics-project-id>.iam.gserviceaccount.com"
}
```

**Key point:** The binding lives on the **Project A bucket**, not on the Project B project.
The `analytics-ingestion-sa` email is a Project B identity, but the binding is in Project A's IAM.

---

## Access Denied Test

```bash
# Before adding the binding — should return 403
GOOGLE_CLOUD_PROJECT=$ANALYTICS_PROJECT_ID \
  gcloud storage ls gs://$RAW_BUCKET_NAME/customers/ \
  --impersonate-service-account=analytics-ingestion-sa@$ANALYTICS_PROJECT_ID.iam.gserviceaccount.com

# Expected:
# ERROR: (gcloud.storage.ls) HTTPError 403: analytics-ingestion-sa@... does not have
#   storage.objects.list access to the Google Cloud Storage bucket.
```

---

## Successful Access Test

```bash
# After applying the Terraform binding
gcloud storage ls gs://$RAW_BUCKET_NAME/customers/ \
  --impersonate-service-account=analytics-ingestion-sa@$ANALYTICS_PROJECT_ID.iam.gserviceaccount.com

# Expected: lists .jsonl files in the customers/ prefix
```

---

## Audit Log Query (Project A)

After a cross-project read, verify it appears in Project A's audit logs:

```
# In Cloud Logging on Project A:
resource.type="gcs_bucket"
  AND protoPayload.serviceName="storage.googleapis.com"
  AND protoPayload.methodName=~"storage.objects.(get|list)"
  AND protoPayload.authenticationInfo.principalEmail:"analytics-ingestion-sa"
```

**Note:** Even though the SA is a Project B identity, the audit log entry appears in **Project A**
because that is where the resource (bucket) lives.

---

## Billing Note

- Storage costs for the raw bucket → billed to **Project A**
- Network egress from GCS to BigQuery (same region) → typically free within GCP
- BigQuery load job → billed to **Project B**

---

## GCP vs. AWS Comparison

| Aspect | GCP | AWS |
|---|---|---|
| Mechanism | Bucket-level IAM binding | Bucket policy + cross-account IAM role |
| Identity type | Service account email | IAM role ARN |
| Audit log location | Resource's project (Project A) | CloudTrail in resource account |
| Temporary credentials | SA impersonation (short-lived) | `sts:AssumeRole` |
| Key difference | No bucket policy document — IAM bindings on bucket are the policy | Bucket policy is a separate JSON document |
