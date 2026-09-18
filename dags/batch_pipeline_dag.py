"""
dags/batch_pipeline_dag.py — Cloud Composer (Apache Airflow) DAG

This DAG is the Cloud Composer equivalent of pipelines/batch/run_sql.py.
It orchestrates the full batch pipeline for the Commerce 360 platform:

    Bronze -> Silver (7 MERGE models)
    Silver -> Gold   (7 dimension + fact models)
    Data Quality checks (3 checks, circuit-breaker on CRITICAL failures)

Architecture Notes:
    - This DAG uses BigQueryInsertJobOperator, which submits SQL jobs to BigQuery
      and waits for their completion. Airflow is the orchestrator; BigQuery does
      the actual data processing.
    - All SQL files are read from the pipelines/sql/ directory.
    - Secrets (project IDs etc.) are fetched from Airflow Variables, backed
      by Google Secret Manager in production.
    - On failure, an email alert is sent to alert_email (from Airflow Variables).

How to deploy to Cloud Composer:
    gsutil -m rsync -r dags/ gs://<composer-bucket>/dags/
    gsutil -m rsync -r pipelines/sql/ gs://<composer-bucket>/dags/sql/

How to trigger a manual backfill:
    airflow dags backfill -s 2024-01-01 -e 2024-01-31 batch_pipeline

Interview Notes:
    - Each task is atomic. If silver_orders fails, gold_fact_orders is never
      attempted. Airflow's dependency graph enforces this automatically.
    - retries=2 on each SQL task handles transient BigQuery slot unavailability.
    - catchup=False means deploying will NOT trigger historical runs.
    - max_active_runs=1 prevents concurrent runs racing on the same tables.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.utils.trigger_rule import TriggerRule

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Set these Airflow Variables before running (backed by Secret Manager):
#   airflow variables set analytics_project_id "commerce360-analytics-dev-alvi"
#   airflow variables set alert_email          "alvigeorge2@gmail.com"

GCP_CONN_ID = "google_cloud_default"   # Auto-configured in Cloud Composer


def _read_sql(relative_path: str) -> str:
    """Read a SQL file from dags/sql/ and return as a string."""
    base = Path(__file__).parent / "sql"
    return (base / relative_path).read_text()


def _bq_job(sql: str, project_id: str) -> dict:
    """Build a BigQueryInsertJobOperator configuration dict.

    Interview Note:
        BigQueryInsertJobOperator maps directly to the BigQuery Jobs REST API.
        You can pass any job parameter here (labels, timeout, etc.) without
        needing a separate Airflow parameter for each setting.
    """
    return {
        "query": {
            "query": sql.replace("{PROJECT_ID}", project_id),
            "useLegacySql": False,
        }
    }


# ---------------------------------------------------------------------------
# Default task arguments — applied to every task unless overridden
# ---------------------------------------------------------------------------
DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email": ["{{ var.value.alert_email }}"],
    "email_on_failure": True,       # Email the team on any task failure
    "email_on_retry": False,        # Do NOT email on retries (too noisy)
    "retries": 2,                   # Retry twice for transient BigQuery errors
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),
}


# ---------------------------------------------------------------------------
# DAG Definition
# ---------------------------------------------------------------------------
@dag(
    dag_id="batch_pipeline",
    description="Commerce 360: Bronze->Silver->Gold->Quality checks (daily 2am UTC)",
    schedule_interval="0 2 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["commerce360", "batch", "bigquery"],
    doc_md=__doc__,
)
def batch_pipeline():
    """
    Task Dependency Graph:

        silver_customers  ─┐
        silver_products   ─┤
        silver_campaigns  ─┤
        silver_inventory  ─┼──► dim_date      ─┐
        silver_orders     ─┤    dim_customers  ─┤
        silver_order_items─┤    dim_products   ─┼──► fact_orders       ─┐
        silver_clickstream─┘    dim_campaigns  ─┘    fact_inventory     ─┼──► data_quality
                                                      fact_clickstream   ─┘
    """
    project_id = Variable.get(
        "analytics_project_id",
        default_var="commerce360-analytics-dev-alvi"
    )

    # ── SILVER LAYER ─────────────────────────────────────────────────────────
    # All 7 silver models run in PARALLEL — they are independent of each other.
    # Each uses a MERGE statement for idempotency (safe to retry).

    silver_customers = BigQueryInsertJobOperator(
        task_id="silver_customers",
        configuration=_bq_job(_read_sql("silver/silver_customers.sql"), project_id),
        project_id=project_id,
        gcp_conn_id=GCP_CONN_ID,
        doc_md="MERGE bronze.customers -> silver.customers on customer_id",
    )
    silver_products = BigQueryInsertJobOperator(
        task_id="silver_products",
        configuration=_bq_job(_read_sql("silver/silver_products.sql"), project_id),
        project_id=project_id,
        gcp_conn_id=GCP_CONN_ID,
    )
    silver_campaigns = BigQueryInsertJobOperator(
        task_id="silver_campaigns",
        configuration=_bq_job(_read_sql("silver/silver_campaigns.sql"), project_id),
        project_id=project_id,
        gcp_conn_id=GCP_CONN_ID,
    )
    silver_inventory = BigQueryInsertJobOperator(
        task_id="silver_inventory",
        configuration=_bq_job(_read_sql("silver/silver_inventory.sql"), project_id),
        project_id=project_id,
        gcp_conn_id=GCP_CONN_ID,
    )
    silver_orders = BigQueryInsertJobOperator(
        task_id="silver_orders",
        configuration=_bq_job(_read_sql("silver/silver_orders.sql"), project_id),
        project_id=project_id,
        gcp_conn_id=GCP_CONN_ID,
        doc_md="MERGE bronze.orders -> silver.orders on order_id. Critical path for fact_orders.",
    )
    silver_order_items = BigQueryInsertJobOperator(
        task_id="silver_order_items",
        configuration=_bq_job(_read_sql("silver/silver_order_items.sql"), project_id),
        project_id=project_id,
        gcp_conn_id=GCP_CONN_ID,
    )
    silver_clickstream = BigQueryInsertJobOperator(
        task_id="silver_clickstream",
        configuration=_bq_job(_read_sql("silver/silver_clickstream.sql"), project_id),
        project_id=project_id,
        gcp_conn_id=GCP_CONN_ID,
    )

    # ── GOLD LAYER: DIMENSIONS ────────────────────────────────────────────────
    # Dimensions run after ALL silver models complete.
    # They are independent of each other and run in parallel.

    gold_dim_date = BigQueryInsertJobOperator(
        task_id="gold_dim_date",
        configuration=_bq_job(_read_sql("gold/dim_date.sql"), project_id),
        project_id=project_id,
        gcp_conn_id=GCP_CONN_ID,
    )
    gold_dim_customers = BigQueryInsertJobOperator(
        task_id="gold_dim_customers",
        configuration=_bq_job(_read_sql("gold/dim_customers.sql"), project_id),
        project_id=project_id,
        gcp_conn_id=GCP_CONN_ID,
    )
    gold_dim_products = BigQueryInsertJobOperator(
        task_id="gold_dim_products",
        configuration=_bq_job(_read_sql("gold/dim_products.sql"), project_id),
        project_id=project_id,
        gcp_conn_id=GCP_CONN_ID,
    )
    gold_dim_campaigns = BigQueryInsertJobOperator(
        task_id="gold_dim_campaigns",
        configuration=_bq_job(_read_sql("gold/dim_campaigns.sql"), project_id),
        project_id=project_id,
        gcp_conn_id=GCP_CONN_ID,
    )

    # ── GOLD LAYER: FACTS ─────────────────────────────────────────────────────
    # Facts depend on all dimensions being ready (join to them).

    gold_fact_orders = BigQueryInsertJobOperator(
        task_id="gold_fact_orders",
        configuration=_bq_job(_read_sql("gold/fact_orders.sql"), project_id),
        project_id=project_id,
        gcp_conn_id=GCP_CONN_ID,
        doc_md="Primary reporting table. Joins silver.orders + all dimensions.",
    )
    gold_fact_inventory = BigQueryInsertJobOperator(
        task_id="gold_fact_inventory_daily",
        configuration=_bq_job(_read_sql("gold/fact_inventory_daily.sql"), project_id),
        project_id=project_id,
        gcp_conn_id=GCP_CONN_ID,
    )
    gold_fact_clickstream = BigQueryInsertJobOperator(
        task_id="gold_fact_clickstream",
        configuration=_bq_job(_read_sql("gold/fact_clickstream.sql"), project_id),
        project_id=project_id,
        gcp_conn_id=GCP_CONN_ID,
    )

    # ── DATA QUALITY — CIRCUIT BREAKER ───────────────────────────────────────
    # Runs as a Python task AFTER all gold models.
    # CRITICAL failures raise an exception -> task is FAILED -> email alert fired.
    # Identical logic to run_sql.py's _run_post_pipeline_quality_checks().

    @task(
        task_id="data_quality_checks",
        trigger_rule=TriggerRule.ALL_SUCCESS,
        doc_md="""
        Runs 3 post-pipeline data quality checks (mirrors run_sql.py logic):
        1. CRITICAL: silver.orders has no null order_ids
        2. HIGH:     gold.fact_orders has no negative amounts
        3. MEDIUM:   silver.orders data is fresh (< 24h old)
        Circuit Breaker: CRITICAL failures raise RuntimeError -> task FAILED -> email alert.
        """,
    )
    def data_quality_checks():
        from google.cloud import bigquery as bq

        proj = Variable.get("analytics_project_id", default_var="commerce360-analytics-dev-alvi")
        client = bq.Client(project=proj)

        checks = [
            {
                "name": "silver_orders_no_null_order_id",
                "severity": "CRITICAL",
                "sql": f"SELECT COUNT(*) as failed FROM `{proj}.silver.orders` WHERE order_id IS NULL",
            },
            {
                "name": "gold_fact_orders_no_negative_amounts",
                "severity": "HIGH",
                "sql": f"SELECT COUNT(*) as failed FROM `{proj}.gold.fact_orders` WHERE total_amount < 0",
            },
            {
                "name": "bronze_orders_freshness_24h",
                "severity": "MEDIUM",
                "sql": f"""
                    SELECT CASE
                        WHEN MAX(order_date) < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
                        THEN 1 ELSE 0
                    END as failed
                    FROM `{proj}.silver.orders`
                """,
            },
        ]

        all_passed = True
        for check in checks:
            result = list(client.query(check["sql"]).result())
            failed_count = result[0]["failed"] if result else 0

            if failed_count == 0:
                logger.info("PASSED  [%s] %s", check["severity"], check["name"])
            else:
                logger.error("FAILED  [%s] %s -- %d violations", check["severity"], check["name"], failed_count)
                all_passed = False
                if check["severity"] == "CRITICAL":
                    raise RuntimeError(
                        f"CRITICAL quality check failed: {check['name']}. "
                        f"{failed_count} records violated the constraint. Pipeline halted."
                    )

        if not all_passed:
            logger.warning("Some non-critical checks failed. Review logs.")

    # ── WIRE UP DEPENDENCIES ─────────────────────────────────────────────────
    # Read as: "X >> Y" means X must complete before Y starts.

    silver_all = [
        silver_customers, silver_products, silver_campaigns, silver_inventory,
        silver_orders, silver_order_items, silver_clickstream,
    ]
    gold_dims = [gold_dim_date, gold_dim_customers, gold_dim_products, gold_dim_campaigns]
    gold_facts = [gold_fact_orders, gold_fact_inventory, gold_fact_clickstream]
    dq = data_quality_checks()

    # All silver tasks -> all gold dimension tasks (parallel within each layer)
    for silver_task in silver_all:
        silver_task >> gold_dims  # type: ignore[operator]

    # All gold dims -> all gold fact tasks
    for dim_task in gold_dims:
        dim_task >> gold_facts  # type: ignore[operator]

    # All gold fact tasks -> data quality
    for fact_task in gold_facts:
        fact_task >> dq


# Instantiate the DAG
batch_pipeline()
