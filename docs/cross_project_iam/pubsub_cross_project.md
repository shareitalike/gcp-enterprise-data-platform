# Cross-Project Pub/Sub — IAM Guide

## What This Covers

How a Project B subscription pulls messages from a Pub/Sub topic owned by Project A.

This is the **second cross-project communication exercise** (Phase 7).

---

## Resource Ownership

| Resource | Owner | Notes |
|---|---|---|
| Pub/Sub topic `orders-created` | Project A | Created by Terraform (ingestion-dev) |
| Pub/Sub topic `clickstream-events` | Project A | Created by Terraform (ingestion-dev) |
| Subscription `orders-created-sub` | Project B | References a cross-project topic |
| Subscription `clickstream-events-sub` | Project B | References a cross-project topic |
| `analytics-streaming-sa` | Project B | Pulls from subscriptions |
| Dataflow job | Project B | Uses `analytics-streaming-sa` |

---

## Key Concept: Subscriptions Are Project B Resources

The subscription lives in **Project B**, but it pulls from a **Project A** topic.
This means:
- Project B controls retry policy, dead-letter config, and consumer lifecycle.
- Project A controls who can create subscriptions on its topics (`roles/pubsub.subscriber`).
- Project A does not know the implementation details of the consumer.

**The subscription is created referencing the cross-project topic by full resource name:**
```hcl
resource "google_pubsub_subscription" "clickstream_sub" {
  project = var.analytics_project_id
  name    = "clickstream-events-sub"
  topic   = "projects/${var.ingestion_project_id}/topics/clickstream-events"
  # ...
}
```

---

## IAM Binding Required on Project A Topic

```hcl
# Applied on the Project A topic — grants Project B SA subscriber access
resource "google_pubsub_topic_iam_member" "cross_project_subscriber" {
  project = var.ingestion_project_id
  topic   = "clickstream-events"
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:analytics-streaming-sa@<analytics-project-id>.iam.gserviceaccount.com"
}
```

Without this binding, creating the subscription in Project B will succeed (it's a Project B resource),
but **pulling messages will fail** with a 403 because the SA lacks subscriber permission on the topic.

---

## Pub/Sub vs. Kafka Consumer Model

| Aspect | Pub/Sub | Kafka |
|---|---|---|
| Consumer identity | Subscription is a named resource; must be pre-created | Consumer group configured by consumer at runtime |
| Subscription ownership | Explicit — created in a project, owned by that project | Implicit — managed inside Kafka |
| Cross-project access | Topic IAM binding required | ACL on Kafka topic (if Kafka ACLs enabled) |
| Message replay | Via subscription `seek` to a timestamp or snapshot | Via consumer group offset reset |
| Dead-letter | Configured per subscription | Configured in Kafka Streams / consumer code |
| Ordering | Not guaranteed by default; use ordering keys for partial ordering | Guaranteed within a partition |

---

## Unauthorized Publish Test

```bash
# Attempt to publish to Project A topic as a non-publisher identity
# Expected: PERMISSION_DENIED
gcloud pubsub topics publish orders-created \
  --project=$INGESTION_PROJECT_ID \
  --message='{"test": "unauthorized"}' \
  --impersonate-service-account=analytics-ingestion-sa@$ANALYTICS_PROJECT_ID.iam.gserviceaccount.com

# Expected error:
# ERROR: (gcloud.pubsub.topics.publish) PERMISSION_DENIED: User not authorized to perform this action.
```

---

## Audit Log Query (Project A — Topic Subscription Events)

```
# Cloud Logging on Project A — who subscribed to my topic?
resource.type="pubsub_topic"
  AND protoPayload.serviceName="pubsub.googleapis.com"
  AND protoPayload.methodName="google.pubsub.v1.Subscriber.CreateSubscription"
  AND protoPayload.authenticationInfo.principalEmail:"analytics-streaming-sa"
```

---

## Billing Ownership

| Activity | Billed To |
|---|---|
| Message storage on topic | Project A (topic owner) |
| Message delivery to subscription | Project A (delivery originates from topic) |
| Subscription management (pull, ack) | Project B (subscription owner) |
| Dataflow worker compute | Project B |
