"""
run_sql.py - A lightweight orchestrator to execute BigQuery SQL models.

This executes SQL scripts from pipelines/sql in a defined topological order.
It replaces variables like {PROJECT_ID} in the SQL files with the target project.

Usage:
    python -m pipelines.batch.run_sql --project commerce360-analytics-dev-alvi
"""
import click
import logging
from pathlib import Path
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Topological order of execution
SILVER_SCRIPTS = [
    "silver/silver_customers.sql",
    "silver/silver_products.sql",
    "silver/silver_campaigns.sql",
    "silver/silver_inventory.sql",
    "silver/silver_orders.sql",
    "silver/silver_order_items.sql",
    "silver/silver_clickstream.sql",
]

GOLD_SCRIPTS = [
    "gold/dim_date.sql",
    "gold/dim_customers.sql",
    "gold/dim_products.sql",
    "gold/dim_campaigns.sql",
    "gold/fact_orders.sql",
    "gold/fact_inventory_daily.sql",
    "gold/fact_clickstream.sql",
]

EXECUTION_ORDER = SILVER_SCRIPTS + GOLD_SCRIPTS

@click.command()
@click.option("--project", required=True, help="Target BigQuery Project ID (Analytics).")
def main(project: str):
    """Execute BigQuery SQL models in topological order."""
    client = bigquery.Client(project=project)
    
    base_dir = Path(__file__).parent.parent / "sql"
    
    for relative_path in EXECUTION_ORDER:
        sql_file = base_dir / relative_path
        if not sql_file.exists():
            logger.warning(f"File not found, skipping: {sql_file}")
            continue
            
        logger.info(f"Executing {relative_path}...")
        
        # Read and template the SQL
        sql_content = sql_file.read_text()
        templated_sql = sql_content.replace("{PROJECT_ID}", project)
        
        try:
            job = client.query(templated_sql)
            job.result() # Wait for completion
            
            # Print DML stats if available
            if job.num_dml_affected_rows is not None:
                logger.info(f"  -> Modified {job.num_dml_affected_rows} rows.")
            else:
                logger.info(f"  -> Success.")
                
        except Exception as e:
            logger.error(f"Failed to execute {relative_path}: {e}")
            if hasattr(job, 'errors') and job.errors:
                logger.error(f"Job Errors: {job.errors}")
            raise click.Abort()
            
    logger.info("All SQL models executed successfully!")

if __name__ == "__main__":
    main()
