import argparse
import logging
from google.cloud import pubsub_v1

def publish_bad_events(project_id: str):
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, "orders-created")
    
    bad_messages = [
        # Missing closing brace
        b'{"order_id": "bad-123", "total_amount": 50.00',
        # Completely malformed text
        b'this is just random text, not json at all!',
        # Wrong data types (though parsing json.loads won't fail here, it would fail BQ schema validation
        # but for Phase 11 we are simulating parsing errors, so let's stick to malformed json bytes)
        b'{"order_id": 999, "status: "missing quotes"}',
    ]
    
    logging.info(f"Publishing {len(bad_messages)} intentionally BAD messages to {topic_path}...")
    
    for idx, msg in enumerate(bad_messages):
        future = publisher.publish(topic_path, msg)
        try:
            future.result()
            logging.info(f"Published BAD message {idx+1}/{len(bad_messages)}")
        except Exception as e:
            logging.error(f"Failed to publish message: {e}")
            
    logging.info("Done publishing bad events. Go check the DLQ table in BigQuery!")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Publish intentionally malformed events for DLQ testing")
    parser.add_argument("--project", required=True, help="Ingestion Project ID")
    args = parser.parse_args()
    
    publish_bad_events(args.project)
