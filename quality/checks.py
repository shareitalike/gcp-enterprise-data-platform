"""
quality/checks.py — Reusable data quality check framework.

Quality results are written to BigQuery `quality.dq_results`.
Each check returns a QualityResult dataclass.

Checks are classified by severity:
  CRITICAL  → pipeline halts (configurable)
  HIGH      → records quarantined; pipeline continues
  MEDIUM    → warning logged; pipeline continues
  LOW       → informational only

Usage:
    from quality.checks import run_null_check, run_duplicate_check, QualityResult
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CheckStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"


@dataclass
class QualityResult:
    rule_name: str
    dataset_name: str
    table_name: str
    column_name: str | None
    total_records: int
    failed_records: int
    severity: Severity
    status: CheckStatus
    pipeline_run_id: str
    error_details: str = ""
    checked_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def failure_pct(self) -> float:
        if self.total_records == 0:
            return 0.0
        return round(self.failed_records / self.total_records * 100, 4)

    def to_bq_row(self) -> dict[str, Any]:
        """Serialize for BigQuery insert."""
        d = asdict(self)
        d["failure_pct"] = self.failure_pct
        d["severity"] = self.severity.value
        d["status"] = self.status.value
        return d

    def raise_if_critical(self) -> None:
        """Raise RuntimeError if this is a CRITICAL failure. Called by pipeline."""
        if self.severity == Severity.CRITICAL and self.status == CheckStatus.FAILED:
            raise RuntimeError(
                f"CRITICAL quality check failed: {self.rule_name} "
                f"on {self.dataset_name}.{self.table_name} "
                f"({self.failed_records}/{self.total_records} records, "
                f"{self.failure_pct}%)"
            )


def run_null_check(
    records: list[dict],
    column: str,
    dataset: str,
    table: str,
    severity: Severity,
    pipeline_run_id: str,
) -> QualityResult:
    """
    Check that no records have a null/missing value in `column`.

    Args:
        records: List of record dicts (already parsed from JSON/CSV).
        column: Field name to check.
        dataset: BigQuery dataset name (for result metadata).
        table: BigQuery table name (for result metadata).
        severity: Failure severity level.
        pipeline_run_id: Current pipeline run ID for lineage.

    Returns:
        QualityResult with pass/fail status.
    """
    total = len(records)
    failed = sum(
        1 for r in records if r.get(column) is None or r.get(column) == ""
    )
    status = CheckStatus.PASSED if failed == 0 else CheckStatus.FAILED

    return QualityResult(
        rule_name=f"null_check_{column}",
        dataset_name=dataset,
        table_name=table,
        column_name=column,
        total_records=total,
        failed_records=failed,
        severity=severity,
        status=status,
        pipeline_run_id=pipeline_run_id,
        error_details=f"{failed} records have null '{column}'" if failed > 0 else "",
    )


def run_duplicate_check(
    records: list[dict],
    key_columns: list[str],
    dataset: str,
    table: str,
    severity: Severity,
    pipeline_run_id: str,
) -> QualityResult:
    """
    Check for duplicate records based on a composite key.

    A duplicate is defined as: two or more records with identical values
    across all `key_columns`.

    Returns:
        QualityResult where failed_records = count of duplicate records
        (total occurrences minus one per unique key, i.e. the extras).
    """
    total = len(records)
    seen: dict[str, int] = {}

    for r in records:
        key = "|".join(str(r.get(col, "")) for col in key_columns)
        seen[key] = seen.get(key, 0) + 1

    # Number of extra (duplicate) records
    failed = sum(count - 1 for count in seen.values() if count > 1)
    status = CheckStatus.PASSED if failed == 0 else CheckStatus.FAILED
    duplicate_keys = [k for k, v in seen.items() if v > 1]

    return QualityResult(
        rule_name=f"duplicate_check_{'_'.join(key_columns)}",
        dataset_name=dataset,
        table_name=table,
        column_name=",".join(key_columns),
        total_records=total,
        failed_records=failed,
        severity=severity,
        status=status,
        pipeline_run_id=pipeline_run_id,
        error_details=(
            f"{len(duplicate_keys)} duplicate keys found"
            if duplicate_keys
            else ""
        ),
    )


def run_schema_check(
    records: list[dict],
    schema_path: str,
    dataset: str,
    table: str,
    severity: Severity,
    pipeline_run_id: str,
) -> tuple[QualityResult, list[dict], list[dict]]:
    """
    Validate records against a JSON Schema file.

    Returns:
        Tuple of (QualityResult, valid_records, invalid_records).
        Invalid records can be routed to quarantine.

    Requires: jsonschema library (in project dependencies).
    """
    import jsonschema

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    validator = jsonschema.Draft7Validator(schema)
    valid: list[dict] = []
    invalid: list[dict] = []

    for record in records:
        errors = list(validator.iter_errors(record))
        if errors:
            record["_validation_errors"] = [str(e.message) for e in errors]
            invalid.append(record)
        else:
            valid.append(record)

    total = len(records)
    failed = len(invalid)
    status = CheckStatus.PASSED if failed == 0 else CheckStatus.FAILED

    result = QualityResult(
        rule_name="schema_check",
        dataset_name=dataset,
        table_name=table,
        column_name=None,
        total_records=total,
        failed_records=failed,
        severity=severity,
        status=status,
        pipeline_run_id=pipeline_run_id,
        error_details=f"{failed} records failed schema validation" if failed > 0 else "",
    )
    return result, valid, invalid


def run_value_range_check(
    records: list[dict],
    column: str,
    min_value: float | None,
    max_value: float | None,
    dataset: str,
    table: str,
    severity: Severity,
    pipeline_run_id: str,
) -> QualityResult:
    """Check that numeric column values fall within [min_value, max_value]."""
    total = len(records)
    failed = 0

    for r in records:
        val = r.get(column)
        if val is None:
            continue  # null check is a separate rule
        try:
            fval = float(val)
        except (TypeError, ValueError):
            failed += 1
            continue
        if min_value is not None and fval < min_value:
            failed += 1
        elif max_value is not None and fval > max_value:
            failed += 1

    status = CheckStatus.PASSED if failed == 0 else CheckStatus.FAILED
    return QualityResult(
        rule_name=f"range_check_{column}",
        dataset_name=dataset,
        table_name=table,
        column_name=column,
        total_records=total,
        failed_records=failed,
        severity=severity,
        status=status,
        pipeline_run_id=pipeline_run_id,
        error_details=(
            f"{failed} records have '{column}' outside "
            f"[{min_value}, {max_value}]"
            if failed > 0
            else ""
        ),
    )


def compute_record_hash(record: dict, exclude_fields: list[str] | None = None) -> str:
    """
    Compute a stable MD5 hash of business fields for idempotency / change detection.

    Excludes pipeline metadata fields (ingestion_ts, pipeline_run_id, etc.)
    by default. Override with exclude_fields.

    Returns:
        32-character hex MD5 string.
    """
    default_exclude = {
        "_ingestion_ts", "_pipeline_run_id", "_source_file",
        "_record_hash", "_validation_errors",
        "_is_late_arrival", "_duplicate_flag",
    }
    excluded = default_exclude | set(exclude_fields or [])

    business_fields = {k: v for k, v in sorted(record.items()) if k not in excluded}
    serialized = json.dumps(business_fields, sort_keys=True, default=str)
    return hashlib.md5(serialized.encode("utf-8")).hexdigest()
