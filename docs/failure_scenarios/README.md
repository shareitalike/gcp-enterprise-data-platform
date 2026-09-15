# Failure Scenarios — Index

Each scenario documents: reproduction steps, expected behavior, detection method, recovery, data impact, and runbook entry.
Scenarios are implemented incrementally — only after the corresponding component is built.

| # | Scenario | Phase | Status |
|---|---|---|---|
| FS-001 | Cross-project GCS permission denied | 4 | ⬜ Not yet implemented |
| FS-002 | Duplicate raw file delivered to GCS | 4 | ⬜ Not yet implemented |
| FS-003 | Invalid JSON record in batch file | 4 | ⬜ Not yet implemented |
| FS-004 | Missing required field in batch file | 4 | ⬜ Not yet implemented |
| FS-005 | Schema evolution — new field added to source | 5 | ⬜ Not yet implemented |
| FS-006 | Schema evolution — field type changed (breaking) | 5 | ⬜ Not yet implemented |
| FS-007 | BigQuery MERGE cost spike (unbounded scan) | 5 | ⬜ Not yet implemented |
| FS-008 | Referential integrity violation (order with unknown customer_id) | 6 | ⬜ Not yet implemented |
| FS-009 | Partial file delivery (truncated JSONL) | 6 | ⬜ Not yet implemented |
| FS-010 | Unauthorized Pub/Sub publisher | 7 | ⬜ Not yet implemented |
| FS-011 | Unauthorized Pub/Sub subscriber | 7 | ⬜ Not yet implemented |
| FS-012 | Duplicate Pub/Sub messages | 7 | ⬜ Not yet implemented |
| FS-013 | Pub/Sub subscription backlog growth | 7 | ⬜ Not yet implemented |
| FS-014 | Dead-letter queue overflow | 7 | ⬜ Not yet implemented |
| FS-015 | Dataflow worker failure | 8 | ⬜ Not yet implemented |
| FS-016 | Late clickstream event (> watermark) | 8 | ⬜ Not yet implemented |
| FS-017 | Poison message (unparseable JSON) in Pub/Sub | 8 | ⬜ Not yet implemented |
| FS-018 | Service account impersonation failure | 9 | ⬜ Not yet implemented |
| FS-019 | Unexpected data volume spike | 11 | ⬜ Not yet implemented |
| FS-020 | Pipeline re-run without idempotency (duplicate Gold records) | 6 | ⬜ Not yet implemented |

Each scenario will be documented in a separate file: `FS-XXX-<name>.md`
