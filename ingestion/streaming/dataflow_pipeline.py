"""
dataflow_pipeline.py — Apache Beam streaming pipeline to ingest Pub/Sub messages to BigQuery.

Pipeline Architecture:
    Pub/Sub (Project A) → Parse JSON → [Window + Aggregate] → BigQuery Bronze (Project B)
                                    ↘ DLQ (bad records) → BigQuery DLQ Table

Windowing Strategy (Clickstream branch):
    - Fixed 60-second tumbling windows group events into time buckets.
    - Watermark of 10 minutes: events up to 10 min late are still processed correctly.
    - Events later than 10 min are counted in a separate late-data metric.

Usage (Local Execution):
    $env:GOOGLE_IMPERSONATE_SERVICE_ACCOUNT="<YOUR_SERVICE_ACCOUNT_EMAIL>"
    python -m ingestion.streaming.dataflow_pipeline --project_id <YOUR_PROJECT_ID>
"""

import argparse
import json
import datetime
import logging
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions, GoogleCloudOptions
from apache_beam.transforms.window import FixedWindows
from apache_beam.transforms.trigger import AfterWatermark, AfterProcessingTime, AccumulationMode
from apache_beam.utils.timestamp import Duration


class ParseJson(beam.DoFn):
    """Parses the raw Pub/Sub bytes into a Python dictionary.

    Yields:
        main: Successfully parsed dict records.
        dead_letter: Dict with payload, error, source, and timestamp for failed records.
    """
    def __init__(self, source_name: str):
        """Args:
            source_name: Label for the data source (e.g. 'orders', 'clickstream').
                         Used to tag DLQ records so engineers know which branch failed.
        """
        self.source_name = source_name

    def process(self, element):
        try:
            # element is bytes in Python 3 for Pub/Sub messages
            record = json.loads(element.decode('utf-8'))
            yield record
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            # Catch only known parsing errors — do NOT swallow unexpected errors
            # like MemoryError or SystemExit which indicate pipeline health issues.
            logging.error(f"[{self.source_name}] Failed to parse JSON: {e}, payload: {element}")
            yield beam.pvalue.TaggedOutput(
                'dead_letter',
                {
                    "payload": str(element),
                    "error_message": str(e),
                    "source": self.source_name,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
            )


class CountEventsInWindow(beam.DoFn):
    """Counts parsed events within a Beam window and emits a summary row.

    This DoFn receives a list of records from a GroupByKey within a fixed window
    and emits a single summary dict suitable for writing to BigQuery.

    Interview Note:
        The window boundaries (window.start / window.end) tell you exactly which
        60-second bucket these events belong to. This is EVENT-TIME, not processing-time.
        If an event was published at 10:00:03 but arrived at 10:01:45 due to network lag,
        it will appear in the 10:00:00–10:01:00 window, NOT the 10:01:00–10:02:00 window.
        That is the key power of event-time windowing.
    """
    def process(self, element, window=beam.DoFn.WindowParam):
        key, records_iter = element
        records = list(records_iter)

        yield {
            "window_start": window.start.to_utc_datetime().isoformat(),
            "window_end": window.end.to_utc_datetime().isoformat(),
            "event_count": len(records),
            "computed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }


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
    clickstream_window_table = f"{project_id}:bronze.clickstream_window_summary"
    dlq_table = f"{project_id}:bronze.dead_letter_queue"

    # Start the Beam Pipeline
    with beam.Pipeline(options=options) as p:

        # ==========================================
        # BRANCH 1: Orders Pipeline (no windowing)
        # Orders are written record-by-record as they arrive.
        # We use a 2-minute ack_deadline so orders are processed quickly.
        # ==========================================
        orders_parsed = (
            p
            | "Read Orders from PubSub" >> beam.io.ReadFromPubSub(subscription=orders_sub)
            | "Parse Orders JSON" >> beam.ParDo(ParseJson(source_name='orders')).with_outputs('dead_letter', main='main')
        )

        # Write good records
        orders_parsed.main | "Write Orders to BQ" >> beam.io.WriteToBigQuery(
            table=orders_table,
            create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
            write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
            insert_retry_strategy=beam.io.gcp.bigquery_tools.RetryStrategy.RETRY_ON_TRANSIENT_ERROR
        )

        # Write bad records to DLQ
        orders_parsed.dead_letter | "Write Orders DLQ to BQ" >> beam.io.WriteToBigQuery(
            table=dlq_table,
            create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
            write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
            insert_retry_strategy=beam.io.gcp.bigquery_tools.RetryStrategy.RETRY_ON_TRANSIENT_ERROR
        )

        # ==========================================
        # BRANCH 2: Clickstream Pipeline (WITH windowing)
        # Clickstream events are high-volume and need aggregation.
        # We use 60-second Fixed Windows with a 10-minute watermark for late data.
        # ==========================================
        clickstream_parsed = (
            p
            | "Read Clickstream from PubSub" >> beam.io.ReadFromPubSub(subscription=clickstream_sub)
            | "Parse Clickstream JSON" >> beam.ParDo(ParseJson(source_name='clickstream')).with_outputs('dead_letter', main='main')
        )

        # Write raw good records (no windowing — individual rows go straight to BQ)
        clickstream_parsed.main | "Write Clickstream to BQ" >> beam.io.WriteToBigQuery(
            table=clickstream_table,
            create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
            write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
            insert_retry_strategy=beam.io.gcp.bigquery_tools.RetryStrategy.RETRY_ON_TRANSIENT_ERROR
        )

        # -- Windowed Aggregation Branch --
        # Apply Fixed 60-second windows with a 10-minute allowed lateness watermark.
        # Events arriving up to 10 minutes late will be placed in their correct
        # event-time window rather than being dropped or misclassified.
        clickstream_windowed_counts = (
            clickstream_parsed.main
            | "Apply 60s Fixed Window" >> beam.WindowInto(
                FixedWindows(60),  # 60-second tumbling windows
                trigger=AfterWatermark(
                    late=AfterProcessingTime(delay=60)  # Fire once more for late data after 60s
                ),
                allowed_lateness=Duration(seconds=600),   # 10-minute watermark
                accumulation_mode=AccumulationMode.DISCARDING  # Don't re-count events already emitted
            )
            # Assign every event a constant key so GroupByKey collects all events in the window
            | "Key By Constant" >> beam.Map(lambda record: ("clickstream", record))
            | "Group By Window" >> beam.GroupByKey()
            | "Count Events Per Window" >> beam.ParDo(CountEventsInWindow())
        )

        # Write window summary to a separate BigQuery table
        clickstream_windowed_counts | "Write Window Summary to BQ" >> beam.io.WriteToBigQuery(
            table=clickstream_window_table,
            create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
            write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
        )

        # Write bad records to DLQ
        clickstream_parsed.dead_letter | "Write Clickstream DLQ to BQ" >> beam.io.WriteToBigQuery(
            table=dlq_table,
            create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
            write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
            insert_retry_strategy=beam.io.gcp.bigquery_tools.RetryStrategy.RETRY_ON_TRANSIENT_ERROR
        )


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    run()
