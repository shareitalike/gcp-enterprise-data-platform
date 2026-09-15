"""
tests/unit/test_quality_checks.py

Unit tests for the quality check framework (quality.checks).
No GCP dependencies — all checks run on in-memory record lists.
"""

import pytest
from quality.checks import (
    run_null_check,
    run_duplicate_check,
    run_value_range_check,
    compute_record_hash,
    CheckStatus,
    Severity,
)

PIPELINE_RUN_ID = "test-run-001"


class TestNullCheck:

    def test_passes_when_no_nulls(self):
        records = [{"customer_id": "abc"}, {"customer_id": "def"}]
        result = run_null_check(records, "customer_id", "bronze", "raw_customers",
                                Severity.CRITICAL, PIPELINE_RUN_ID)
        assert result.status == CheckStatus.PASSED
        assert result.failed_records == 0

    def test_fails_when_null_present(self):
        records = [{"customer_id": None}, {"customer_id": "def"}]
        result = run_null_check(records, "customer_id", "bronze", "raw_customers",
                                Severity.CRITICAL, PIPELINE_RUN_ID)
        assert result.status == CheckStatus.FAILED
        assert result.failed_records == 1

    def test_fails_on_empty_string(self):
        records = [{"customer_id": ""}]
        result = run_null_check(records, "customer_id", "bronze", "raw_customers",
                                Severity.HIGH, PIPELINE_RUN_ID)
        assert result.status == CheckStatus.FAILED

    def test_total_records_matches_input(self):
        records = [{"x": i} for i in range(10)]
        result = run_null_check(records, "x", "bronze", "t", Severity.LOW, PIPELINE_RUN_ID)
        assert result.total_records == 10

    def test_failure_pct_calculation(self):
        records = [{"id": None}, {"id": "a"}, {"id": "b"}, {"id": "c"}]
        result = run_null_check(records, "id", "s", "t", Severity.MEDIUM, PIPELINE_RUN_ID)
        assert result.failure_pct == 25.0


class TestDuplicateCheck:

    def test_passes_when_no_duplicates(self):
        records = [{"order_id": "a"}, {"order_id": "b"}, {"order_id": "c"}]
        result = run_duplicate_check(records, ["order_id"], "silver", "orders",
                                     Severity.HIGH, PIPELINE_RUN_ID)
        assert result.status == CheckStatus.PASSED
        assert result.failed_records == 0

    def test_detects_single_duplicate(self):
        records = [{"order_id": "a"}, {"order_id": "a"}, {"order_id": "b"}]
        result = run_duplicate_check(records, ["order_id"], "silver", "orders",
                                     Severity.HIGH, PIPELINE_RUN_ID)
        assert result.status == CheckStatus.FAILED
        assert result.failed_records == 1   # 1 extra copy

    def test_composite_key_duplicate(self):
        records = [
            {"order_id": "a", "product_id": "x"},
            {"order_id": "a", "product_id": "x"},   # duplicate
            {"order_id": "a", "product_id": "y"},   # different product — not a duplicate
        ]
        result = run_duplicate_check(records, ["order_id", "product_id"],
                                     "silver", "order_items",
                                     Severity.HIGH, PIPELINE_RUN_ID)
        assert result.failed_records == 1

    def test_empty_records(self):
        result = run_duplicate_check([], ["id"], "s", "t", Severity.LOW, PIPELINE_RUN_ID)
        assert result.total_records == 0
        assert result.status == CheckStatus.PASSED


class TestValueRangeCheck:

    def test_passes_within_range(self):
        records = [{"price": 10.0}, {"price": 50.0}]
        result = run_value_range_check(records, "price", 0.01, 1000.0,
                                       "silver", "products",
                                       Severity.HIGH, PIPELINE_RUN_ID)
        assert result.status == CheckStatus.PASSED

    def test_fails_below_min(self):
        records = [{"price": -1.0}]
        result = run_value_range_check(records, "price", 0.0, None,
                                       "silver", "products",
                                       Severity.HIGH, PIPELINE_RUN_ID)
        assert result.status == CheckStatus.FAILED
        assert result.failed_records == 1

    def test_nulls_are_skipped(self):
        records = [{"price": None}]
        result = run_value_range_check(records, "price", 0.0, 100.0,
                                       "silver", "products",
                                       Severity.MEDIUM, PIPELINE_RUN_ID)
        # Null check is a separate rule; range check skips nulls
        assert result.failed_records == 0


class TestComputeRecordHash:

    def test_same_business_fields_same_hash(self):
        r1 = {"order_id": "abc", "status": "PENDING", "_ingestion_ts": "2024-01-01"}
        r2 = {"order_id": "abc", "status": "PENDING", "_ingestion_ts": "2024-01-02"}
        assert compute_record_hash(r1) == compute_record_hash(r2)

    def test_different_business_fields_different_hash(self):
        r1 = {"order_id": "abc", "status": "PENDING"}
        r2 = {"order_id": "abc", "status": "SHIPPED"}
        assert compute_record_hash(r1) != compute_record_hash(r2)

    def test_hash_is_32_chars(self):
        h = compute_record_hash({"key": "value"})
        assert len(h) == 32

    def test_hash_is_deterministic(self):
        r = {"a": 1, "b": 2, "c": 3}
        assert compute_record_hash(r) == compute_record_hash(r)

    def test_raise_if_critical_raises(self):
        from quality.checks import QualityResult, CheckStatus, Severity
        result = QualityResult(
            rule_name="null_check_id",
            dataset_name="bronze",
            table_name="raw_customers",
            column_name="customer_id",
            total_records=100,
            failed_records=5,
            severity=Severity.CRITICAL,
            status=CheckStatus.FAILED,
            pipeline_run_id=PIPELINE_RUN_ID,
        )
        with pytest.raises(RuntimeError, match="CRITICAL"):
            result.raise_if_critical()

    def test_raise_if_critical_does_not_raise_on_pass(self):
        from quality.checks import QualityResult, CheckStatus, Severity
        result = QualityResult(
            rule_name="null_check_id",
            dataset_name="bronze",
            table_name="raw_customers",
            column_name="customer_id",
            total_records=100,
            failed_records=0,
            severity=Severity.CRITICAL,
            status=CheckStatus.PASSED,
            pipeline_run_id=PIPELINE_RUN_ID,
        )
        result.raise_if_critical()   # should not raise
