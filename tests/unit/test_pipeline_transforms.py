"""
tests/unit/test_pipeline_transforms.py — Unit tests for Beam DoFns in dataflow_pipeline.py

These tests validate the LOGIC of each transform completely in isolation.
No GCP project, no Pub/Sub, no BigQuery, no internet connection required.
They run in milliseconds.

Run with:
    pytest tests/unit/test_pipeline_transforms.py -v -s
"""
import json
import pytest
import apache_beam as beam

from ingestion.streaming.dataflow_pipeline import ParseJson


class TestParseJson:
    """Tests for the ParseJson DoFn that parses raw Pub/Sub bytes."""

    def test_valid_json_yields_dict(self):
        """
        GIVEN a valid JSON byte string
        WHEN ParseJson processes it
        THEN it should yield a plain dict (goes to the 'main' output)
        """
        dofn = ParseJson(source_name="orders")
        valid_input = b'{"order_id": "ORD-001", "total_amount": 99.99}'

        outputs = list(dofn.process(valid_input))

        assert len(outputs) == 1
        assert isinstance(outputs[0], dict)
        assert outputs[0]["order_id"] == "ORD-001"
        assert outputs[0]["total_amount"] == 99.99

    def test_invalid_json_yields_tagged_dlq_output(self):
        """
        GIVEN a byte string that is NOT valid JSON
        WHEN ParseJson processes it
        THEN it should yield a TaggedOutput to 'dead_letter' — NOT raise an exception
        """
        dofn = ParseJson(source_name="orders")
        bad_input = b"THIS_IS_NOT_JSON"

        outputs = list(dofn.process(bad_input))

        assert len(outputs) == 1
        tagged = outputs[0]
        assert isinstance(tagged, beam.pvalue.TaggedOutput)
        assert tagged.tag == "dead_letter"

    def test_dlq_record_contains_correct_fields(self):
        """
        GIVEN a malformed JSON byte string
        WHEN ParseJson processes it
        THEN the DLQ record must contain payload, error_message, source, and timestamp
        """
        dofn = ParseJson(source_name="clickstream")
        bad_input = b"NOT_VALID_JSON"

        outputs = list(dofn.process(bad_input))
        dlq_record = outputs[0].value  # .value gets the dict from the TaggedOutput

        assert "payload" in dlq_record
        assert "error_message" in dlq_record
        assert "source" in dlq_record
        assert "timestamp" in dlq_record

    def test_dlq_record_source_tag_matches_constructor(self):
        """
        GIVEN a ParseJson configured with source_name='clickstream'
        WHEN a bad message is processed
        THEN the DLQ record's 'source' field should be 'clickstream'

        This is critical so engineers can filter DLQ records by pipeline branch.
        """
        dofn = ParseJson(source_name="clickstream")
        bad_input = b"[INVALID"

        outputs = list(dofn.process(bad_input))
        dlq_record = outputs[0].value

        assert dlq_record["source"] == "clickstream"

    def test_orders_source_tag_is_orders(self):
        """
        GIVEN a ParseJson configured with source_name='orders'
        WHEN a bad message is processed
        THEN source should be 'orders'
        """
        dofn = ParseJson(source_name="orders")
        bad_input = b"NOT JSON"

        outputs = list(dofn.process(bad_input))
        assert outputs[0].value["source"] == "orders"

    def test_unicode_decode_error_sends_to_dlq(self):
        """
        GIVEN raw bytes that cannot be decoded as UTF-8
        WHEN ParseJson processes it
        THEN it should send to DLQ, not crash the pipeline
        """
        dofn = ParseJson(source_name="orders")
        # 0xFF and 0xFE are not valid UTF-8 sequences
        bad_bytes = b'\xff\xfe INVALID UTF-8'

        outputs = list(dofn.process(bad_bytes))

        assert len(outputs) == 1
        assert isinstance(outputs[0], beam.pvalue.TaggedOutput)
        assert outputs[0].tag == "dead_letter"

    def test_valid_json_with_nested_objects(self):
        """
        GIVEN a JSON message with nested objects (e.g. order with line items)
        WHEN ParseJson processes it
        THEN it should yield the complete nested dict intact
        """
        dofn = ParseJson(source_name="orders")
        nested = {
            "order_id": "ORD-005",
            "items": [{"sku": "SKU-1", "qty": 2}],
            "metadata": {"source": "mobile_app"}
        }
        valid_input = json.dumps(nested).encode("utf-8")

        outputs = list(dofn.process(valid_input))

        assert len(outputs) == 1
        result = outputs[0]
        assert result["items"][0]["sku"] == "SKU-1"
        assert result["metadata"]["source"] == "mobile_app"
