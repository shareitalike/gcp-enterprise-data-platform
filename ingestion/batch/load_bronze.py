"""
load_bronze.py — Load BigQuery Bronze datasets from GCS raw landing zone.

Usage:
    # Run with standard Application Default Credentials:
    python -m ingestion.batch.load_bronze --bucket c360-raw-commerce360-ingest-dev-alvi --dataset commerce360-analytics-dev-alvi.bronze --date 2024-01-15
    
    # Or, to test cross-project IAM, set this ENV var first:
    # export GOOGLE_IMPERSONATE_SERVICE_ACCOUNT="analytics-ingestion-sa@commerce360-analytics-dev-alvi.iam.gserviceaccount.com"
"""
import click
import logging
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ENTITIES = [
    "customers",
    "products",
    "campaigns",
    "inventory",
    "orders",
    "order_items",
    "clickstream_events"
]

@click.command()
@click.option("--bucket", required=True, help="Source GCS bucket name (Project A).")
@click.option("--dataset", required=True, help="Target BigQuery Dataset in format project_id.dataset_id (Project B).")
@click.option("--date", required=True, help="Logical date partition to load (YYYY-MM-DD).")
def main(bucket: str, dataset: str, date: str):
    """Load raw GCS files into BigQuery Bronze dataset."""
    logger.info("Initializing BigQuery Client...")
    client = bigquery.Client()
    
    # Extract project from dataset string (e.g. "my-project.bronze")
    if "." not in dataset:
        logger.error("Dataset must be in the format 'project_id.dataset_id'")
        return
        
    project_id, dataset_id = dataset.split(".", 1)
    
    # Override client project to ensure jobs run in Analytics project
    client.project = project_id

    for entity in ENTITIES:
        gcs_uri = f"gs://{bucket}/{entity}/dt={date}/*.json"
        table_id = f"{dataset}.{entity}"
        
        logger.info(f"Loading {entity} from {gcs_uri} to {table_id}...")
        
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            autodetect=True,
            # For Bronze, we use WRITE_TRUNCATE for full reloads or WRITE_APPEND for appends.
            # In a real batch pipeline, we'd use WRITE_APPEND with partition filtering, 
            # but for simplicity of this exercise we'll truncate and replace if running multiple times.
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )

        try:
            load_job = client.load_table_from_uri(
                gcs_uri, table_id, job_config=job_config
            )
            
            # Wait for the job to complete
            load_job.result()  
            
            destination_table = client.get_table(table_id)
            logger.info(f"Success! Loaded {destination_table.num_rows} rows to {table_id}.")
            
        except Exception as e:
            logger.error(f"Failed to load {entity}: {e}")
            if hasattr(load_job, 'errors') and load_job.errors:
                logger.error(f"Job Errors: {load_job.errors}")

if __name__ == "__main__":
    main()
