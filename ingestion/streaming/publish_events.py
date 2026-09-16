"""
publish_events.py — Simulates microservices publishing real-time events to Pub/Sub.

Usage:
    $env:GOOGLE_IMPERSONATE_SERVICE_ACCOUNT="<YOUR_PUBLISHER_SA_EMAIL>"
    python -m ingestion.streaming.publish_events --input-dir data/generated/small --project <YOUR_INGESTION_PROJECT_ID>
"""
import click
import logging
import json
import time
from pathlib import Path
from google.cloud import pubsub_v1

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def publish_file(publisher, topic_path, file_path, limit=None):
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return

    logger.info(f"Publishing messages from {file_path.name} to {topic_path}...")
    
    count = 0
    futures = []
    
    with open(file_path, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            
            # Pub/Sub requires bytes
            data_str = line.strip()
            data_bytes = data_str.encode("utf-8")
            
            # Publish message
            future = publisher.publish(topic_path, data_bytes)
            futures.append(future)
            count += 1
            
            if limit and count >= limit:
                break
                
            # Sleep tiny bit to avoid overwhelming local memory/quota too fast
            if count % 100 == 0:
                time.sleep(0.1)
                
    # Wait for all publishes to finish
    for future in futures:
        future.result()
        
    logger.info(f"Successfully published {count} messages to {topic_path}")


@click.command()
@click.option("--input-dir", required=True, help="Local directory containing generated JSON files (e.g. data/generated/small)")
@click.option("--project", required=True, help="Ingestion Project ID")
@click.option("--limit", type=int, default=1000, help="Max messages to publish per topic (default 1000 to save quota)")
def main(input_dir: str, project: str, limit: int):
    publisher = pubsub_v1.PublisherClient()
    
    in_dir = Path(input_dir)
    
    orders_topic = publisher.topic_path(project, "orders-created")
    clickstream_topic = publisher.topic_path(project, "clickstream-events")
    
    publish_file(publisher, orders_topic, in_dir / "orders.json", limit)
    publish_file(publisher, clickstream_topic, in_dir / "clickstream_events.json", limit)

if __name__ == "__main__":
    main()
