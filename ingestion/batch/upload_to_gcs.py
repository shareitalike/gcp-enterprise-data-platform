"""
upload_to_gcs.py — Upload synthetic JSON files to the raw ingestion bucket.

Usage:
    python -m ingestion.batch.upload_to_gcs --input-dir data/generated/small --bucket c360-raw-commerce360-ingest-dev-alvi --date 2024-01-15
"""
import click
import logging
from pathlib import Path
from google.cloud import storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

@click.command()
@click.option("--input-dir", required=True, help="Local directory containing generated JSON files.")
@click.option("--bucket", required=True, help="Destination GCS bucket name (Project A).")
@click.option("--date", required=True, help="Logical date partition for the load (YYYY-MM-DD).")
def main(input_dir: str, bucket: str, date: str):
    """Upload generated JSON files to GCS raw landing zone."""
    input_path = Path(input_dir)
    if not input_path.exists():
        logger.error(f"Input directory does not exist: {input_dir}")
        return

    json_files = list(input_path.glob("*.json"))
    if not json_files:
        logger.warning(f"No JSON files found in {input_dir}")
        return

    logger.info(f"Connecting to GCS bucket: {bucket}")
    client = storage.Client()
    bucket_obj = client.bucket(bucket)

    for file_path in json_files:
        entity = file_path.stem  # e.g., 'customers'
        
        # Partition scheme: gs://<bucket>/<entity>/dt=<date>/<entity>.json
        gcs_blob_name = f"{entity}/dt={date}/{file_path.name}"
        
        blob = bucket_obj.blob(gcs_blob_name)
        logger.info(f"Uploading {file_path.name} to gs://{bucket}/{gcs_blob_name}...")
        
        blob.upload_from_filename(str(file_path))
        
        logger.info(f"Successfully uploaded {entity}.")

if __name__ == "__main__":
    main()
