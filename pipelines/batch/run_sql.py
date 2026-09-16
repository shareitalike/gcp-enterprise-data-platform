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
@click.option("--skip-quality", is_flag=True, default=False, help="Skip data quality checks (use for debugging only).")
def main(project: str, skip_quality: bool):
    """Execute BigQuery SQL models in topological order, then run data quality checks."""
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

    # ── Run automated data quality checks after every pipeline run ────────────
    # This ensures data quality is enforced automatically, not left to manual runs.
    if skip_quality:
        logger.warning("Skipping data quality checks (--skip-quality flag set).")
        return

    logger.info("=" * 60)
    logger.info("Running post-pipeline data quality checks...")
    logger.info("=" * 60)
    _run_post_pipeline_quality_checks(client, project)


def _run_post_pipeline_quality_checks(client: bigquery.Client, project: str) -> None:
    """Run BigQuery-native data quality checks after pipeline completion.
    
    Uses SQL to perform checks directly in BigQuery (no data movement).
    Results are logged. CRITICAL failures raise RuntimeError to fail the pipeline.
    """
    checks = [
        # Check 1: Ensure silver.orders has no null order_ids (critical integrity check)
        {
            "name": "silver_orders_no_null_order_id",
            "severity": "CRITICAL",
            "sql": f"SELECT COUNT(*) as failed FROM `{project}.silver.orders` WHERE order_id IS NULL",
        },
        # Check 2: Ensure gold.fact_orders has no negative amounts
        {
            "name": "gold_fact_orders_no_negative_amounts",
            "severity": "HIGH",
            "sql": f"SELECT COUNT(*) as failed FROM `{project}.gold.fact_orders` WHERE total_amount < 0",
        },
        # Check 3: Freshness check — ensure data was loaded in the last 24 hours
        {
            "name": "bronze_orders_freshness_24h",
            "severity": "MEDIUM",
            "sql": f"""
                SELECT CASE WHEN MAX(order_date) < DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
                THEN 1 ELSE 0 END as failed
                FROM `{project}.silver.orders`
            """,
        },
    ]

    all_passed = True
    for check in checks:
        try:
            result = list(client.query(check["sql"]).result())
            failed_count = result[0]["failed"] if result else 0

            if failed_count == 0:
                logger.info(f"  ✅ PASSED  [{check['severity']}] {check['name']}")
            else:
                logger.error(f"  ❌ FAILED  [{check['severity']}] {check['name']} — {failed_count} violations")
                all_passed = False
                if check["severity"] == "CRITICAL":
                    raise RuntimeError(
                        f"CRITICAL data quality check failed: {check['name']}. "
                        f"{failed_count} records violated the constraint."
                    )
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"  ⚠️  ERROR running check '{check['name']}': {e}")

    if all_passed:
        logger.info("All data quality checks passed!")
    else:
        logger.warning("Some data quality checks failed. Review logs above.")


if __name__ == "__main__":
    main()
