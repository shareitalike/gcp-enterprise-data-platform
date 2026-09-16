"""
dataflow_pipeline.py — Apache Beam streaming pipeline to ingest Pub/Sub messages to BigQuery.

Usage (Local Execution):
    # Set the environment variable to impersonate the streaming service account
    $env:GOOGLE_IMPERSONATE_SERVICE_ACCOUNT="<YOUR_SERVICE_ACCOUNT_EMAIL>"
    python -m ingestion.streaming.dataflow_pipeline \
        --project_id <YOUR_PROJECT_ID>
"""

import argparse
import json
import logging
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions, GoogleCloudOptions

class ParseJson(beam.DoFn):
    """Parses the raw Pub/Sub bytes into a Python dictionary."""
    def process(self, element):
        try:
            # element is bytes in Python 3 for Pub/Sub messages
            record = json.loads(element.decode('utf-8'))
            yield record
        except Exception as e:
            logging.error(f"Failed to parse JSON: {e}, payload: {element}")
            # In a production pipeline, we would yield this to a Dead Letter Queue (DLQ)
            # but for now, we just drop bad records so the pipeline doesn't crash.

def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--project_id',
        required=True,
        help='The Analytics GCP Project ID'
    )
    
    # Parse known arguments
    known_args, pipeline_args = parser.parse_known_args(argv)
    project_id = known_args.project_id

    # Set up Pipeline Options
    options = PipelineOptions(pipeline_args)
    options.view_as(StandardOptions).streaming = True
    options.view_as(GoogleCloudOptions).project = project_id

    # Define resource paths
    orders_sub = f"projects/{project_id}/subscriptions/orders-created-sub"
    clickstream_sub = f"projects/{project_id}/subscriptions/clickstream-events-sub"
    
    orders_table = f"{project_id}:bronze.orders"
    clickstream_table = f"{project_id}:bronze.clickstream_events"

    # Start the Beam Pipeline
    with beam.Pipeline(options=options) as p:
        
        # ==========================================
        # BRANCH 1: Orders Pipeline
        # ==========================================
        (
            p
            | "Read Orders from PubSub" >> beam.io.ReadFromPubSub(subscription=orders_sub)
            | "Parse Orders JSON" >> beam.ParDo(ParseJson())
            | "Write Orders to BQ" >> beam.io.WriteToBigQuery(
                table=orders_table,
                create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                insert_retry_strategy=beam.io.gcp.bigquery_tools.RetryStrategy.RETRY_ON_TRANSIENT_ERROR
            )
        )

        # ==========================================
        # BRANCH 2: Clickstream Pipeline
        # ==========================================
        (
            p
            | "Read Clickstream from PubSub" >> beam.io.ReadFromPubSub(subscription=clickstream_sub)
            | "Parse Clickstream JSON" >> beam.ParDo(ParseJson())
            | "Write Clickstream to BQ" >> beam.io.WriteToBigQuery(
                table=clickstream_table,
                create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                insert_retry_strategy=beam.io.gcp.bigquery_tools.RetryStrategy.RETRY_ON_TRANSIENT_ERROR
            )
        )

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    run()
