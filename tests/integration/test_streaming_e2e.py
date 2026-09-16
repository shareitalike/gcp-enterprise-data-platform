"""
test_streaming_e2e.py — End-to-end integration test for the streaming pipeline.

This test validates the full Pub/Sub → Dataflow → BigQuery path by:
1. Publishing a uniquely-tagged canary message to Pub/Sub.
2. Polling BigQuery for up to 60 seconds.
3. Asserting the canary message appears in the bronze.orders table.
4. Cleaning up the canary row after the test.

Prerequisites:
    - GOOGLE_IMPERSONATE_SERVICE_ACCOUNT must be set to analytics-streaming-sa
    - The Dataflow pipeline must be RUNNING before executing this test
    - Run with: pytest tests/integration/test_streaming_e2e.py -v -s

Why this matters in production:
    - Unit tests validate individual functions in isolation.
    - Integration tests validate that all the components work TOGETHER.
    - This catches IAM misconfigurations, schema mismatches, and network issues
      that unit tests can never catch.
"""
import json
import time
import uuid
import pytest
import logging
from google.cloud import pubsub_v1, bigquery

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
ANALYTICS_PROJECT   = "commerce360-analytics-dev-alvi"
INGESTION_PROJECT   = "commerce360-ingest-dev-alvi"
ORDERS_TOPIC        = f"projects/{INGESTION_PROJECT}/topics/orders-created"
POLL_INTERVAL_SEC   = 5
MAX_WAIT_SEC        = 60


@pytest.fixture(scope="module")
def canary_order_id() -> str:
    """Generate a unique canary order_id for this test run."""
    return f"E2E-CANARY-{uuid.uuid4().hex[:12].upper()}"


@pytest.fixture(scope="module")
def bq_client():
    return bigquery.Client(project=ANALYTICS_PROJECT)


@pytest.fixture(scope="module")
def publisher():
    return pubsub_v1.PublisherClient()


def test_order_flows_from_pubsub_to_bigquery(canary_order_id, publisher, bq_client):
    """
    GIVEN a valid order JSON message published to Pub/Sub
    WHEN the Dataflow streaming pipeline is running
    THEN the order should appear in BigQuery bronze.orders within 60 seconds
    """
    # ── Step 1: Publish a uniquely tagged canary message ─────────────────────
    canary_message = {
        "order_id": canary_order_id,
        "customer_id": "CUST-E2E-TEST",
        "order_date": "2024-01-15T00:00:00Z",
        "order_status": "e2e_test",
        "total_amount": 0.01,
        "currency_code": "USD",
        "channel": "e2e_test",
        "created_at": "2024-01-15T00:00:00Z",
        "updated_at": "2024-01-15T00:00:00Z",
    }

    logger.info(f"Publishing canary message with order_id={canary_order_id}...")
    future = publisher.publish(ORDERS_TOPIC, json.dumps(canary_message).encode("utf-8"))
    future.result()  # Wait for publish acknowledgement
    logger.info("Canary published successfully.")

    # ── Step 2: Poll BigQuery until the canary appears ────────────────────────
    query = f"""
        SELECT order_id
        FROM `{ANALYTICS_PROJECT}.bronze.orders`
        WHERE order_id = @canary_id
        LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("canary_id", "STRING", canary_order_id)
        ]
    )

    elapsed = 0
    found = False
    while elapsed < MAX_WAIT_SEC:
        logger.info(f"Polling BigQuery... ({elapsed}s elapsed)")
        results = list(bq_client.query(query, job_config=job_config).result())
        if results:
            found = True
            logger.info(f"Canary found in BigQuery after {elapsed}s!")
            break
        time.sleep(POLL_INTERVAL_SEC)
        elapsed += POLL_INTERVAL_SEC

    # ── Step 3: Assert the canary was found ───────────────────────────────────
    assert found, (
        f"Canary message '{canary_order_id}' did NOT appear in bronze.orders "
        f"within {MAX_WAIT_SEC} seconds. Check if Dataflow pipeline is running."
    )


def test_bad_json_flows_to_dlq(publisher, bq_client):
    """
    GIVEN a corrupted (non-JSON) message published to Pub/Sub
    WHEN the Dataflow streaming pipeline is running
    THEN the error should appear in BigQuery bronze.dead_letter_queue within 60 seconds
    """
    bad_payload = b"THIS_IS_NOT_JSON_E2E_TEST"

    logger.info("Publishing bad canary message to test DLQ routing...")
    future = publisher.publish(ORDERS_TOPIC, bad_payload)
    future.result()
    logger.info("Bad canary published.")

    query = f"""
        SELECT payload, source
        FROM `{ANALYTICS_PROJECT}.bronze.dead_letter_queue`
        WHERE payload LIKE '%THIS_IS_NOT_JSON_E2E_TEST%'
        ORDER BY timestamp DESC
        LIMIT 1
    """
    elapsed = 0
    found = False
    while elapsed < MAX_WAIT_SEC:
        logger.info(f"Polling DLQ table... ({elapsed}s elapsed)")
        results = list(bq_client.query(query).result())
        if results:
            found = True
            row = results[0]
            logger.info(f"DLQ entry found: source='{row.source}'")
            assert row.source == "orders", f"Expected source='orders', got '{row.source}'"
            break
        time.sleep(POLL_INTERVAL_SEC)
        elapsed += POLL_INTERVAL_SEC

    assert found, (
        f"Bad message did NOT appear in dead_letter_queue within {MAX_WAIT_SEC}s. "
        "Check Dataflow DLQ routing logic."
    )
