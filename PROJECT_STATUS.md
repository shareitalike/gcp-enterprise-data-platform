# Project Status — GCP Commerce360

Last updated: 2026-09-15

---

## Phase 0 — Architecture and Design ✅ COMPLETE

**Completed:**
- Two-project architecture defined (Project A: Ingestion, Project B: Analytics)
- Resource ownership matrix documented
- GCP service selection matrix with rationale
- Cross-project IAM design (GCS, Pub/Sub, SA impersonation)
- Batch vs. streaming decision by domain
- Full data model for all 7 entities
- Bronze/Silver/Gold responsibilities defined
- 5 Architecture Decision Records written
- Dev cost risk assessment (target: < $20/month for Phases 1–9)
- 20 open items identified for user approval

**Defaults applied (pending confirmation):**
- Region: `us-central1`
- Python: 3.11
- Terraform: 1.8+
- Random seed: 42
- Project A logical ID: `commerce360-ingest-dev`
- Project B logical ID: `commerce360-analytics-dev`

---

## Phase 1 — Repository Foundation ✅ COMPLETE

**Completed:** 2026-09-15

**Files created (18 files, no cloud resources):**
- [x] Git repository initialised
- [x] `.gitignore` (Python, Terraform, GCP credentials)
- [x] `pyproject.toml` (dependencies, tool config)
- [x] `Makefile` (install, test, generate, terraform, auth targets)
- [x] `.env.example` (all configurable values documented)
- [x] `configs/local/config.yaml`
- [x] `configs/ingestion-dev/config.yaml`
- [x] `configs/analytics-dev/config.yaml`
- [x] `README.md`
- [x] `PROJECT_STATUS.md`
- [x] `ARCHITECTURE.md`
- [x] `DESIGN_DECISIONS.md`
- [x] `SECURITY.md`
- [x] `DATA_CONTRACTS.md`
- [x] `COST_GUIDE.md`
- [x] `tests/conftest.py` + `tests/unit/test_config.py`
- [x] `data_generator/__init__.py` + `config.py` + `generator.py`

**Validation results (local — no GCP):**
```
15 passed in 0.49s  (Python 3.10.10, pytest 9.1.1)
Platform: win32
```
- Config loader: all 9 tests passed
- Env var expansion: all 6 tests passed
- No cloud resources created
- No placeholder files

---

## Phase 2 — GCP Foundation (Terraform) ✅ COMPLETE

**Completed:** 2026-09-15

**Deployed resources (100% Free Tier compatible):**
- Project A (`commerce360-ingest-dev-alvi`): GCS raw bucket, Pub/Sub topics + DLQs, publisher SA, IAM bindings.
- Project B (`commerce360-analytics-dev-alvi`): BigQuery datasets (bronze, silver, silver_quarantine, gold, audit, control, quality), Dataflow staging bucket, analytics SAs (ingestion, streaming, deploy), Pub/Sub subscriptions, IAM bindings.

---

## Phase 3 — Synthetic Data Generator ✅ COMPLETE

**Completed:** 2026-09-15

**Target:** `data_generator/` producing all 7 entities in JSON/CSV/Parquet.

**Implementation Details:**
- Modular pipeline inside `data_generator/entities/`.
- Strict referential integrity (Orders use valid Customer IDs, Items use valid Order/Product IDs).
- Built-in `jsonschema` validation strictly enforces data contracts.
- CLI supports tier-based volume scaling and exports to JSON Lines, CSV, or Parquet.

---

## Phase 4 — Cross-Project GCS Access + BQ Batch Load ✅ COMPLETE

**Completed:** 2026-09-15

**First cross-project IAM exercise.**

**Implementation Details:**
- Created `ingestion/batch/upload_to_gcs.py` to push synthetic JSON files to `c360-raw-<ingestion_project_id>`.
- Created `ingestion/batch/load_bronze.py` to load GCS JSON files into BigQuery `bronze` dataset via auto-detect.
- Confirmed cross-project IAM access by using Service Account Impersonation (`analytics-ingestion-sa`) to execute the BigQuery load step.

---

## Phase 5 — BigQuery Bronze/Silver/Gold Modeling ✅ COMPLETE

**Completed:** 2026-09-15

**Implementation Details:**
- Created `pipelines/batch/run_sql.py` to orchestrate SQL transformations.
- Implemented **Silver Layer** (7 models): deduplication, type-casting, and idempotent loading via `MERGE` statements.
- Implemented **Gold Layer** (7 models): 
  - `dim_customers` (SCD Type 2)
  - `dim_products`, `dim_campaigns` (SCD Type 1)
  - `dim_date` (Static spine)
  - `fact_orders`, `fact_inventory_daily`, `fact_clickstream` (Insert/Merge logic)
- Executed pipelines entirely within BigQuery using the `analytics-ingestion-sa` service account.

## Phase 6 — Incremental Batch Processing ✅ COMPLETE

**Completed:** 2026-09-15

**Implementation Details:**
- Modified `ingestion/batch/load_bronze.py` to use `WRITE_APPEND` instead of `WRITE_TRUNCATE`.
- Generated a "Day 2" batch of synthetic data using `--seed 123`.
- Uploaded and appended the new logical partition (`dt=2024-01-16`) to the Bronze datasets.
- Re-ran the Silver and Gold SQL pipelines, which automatically and idempotently merged the new data without duplicating existing records.

---

## Phase 7 — Pub/Sub Cross-Project Streaming ✅ COMPLETE

**Completed:** 2026-09-15

**Implementation Details:**
- Developed `ingestion/streaming/publish_events.py` to push synthetic JSON events to Pub/Sub.
- Authenticated using the `synthetic-publisher-sa` in Project A to mimic a microservice publisher.
- Published 1,000 order and clickstream messages to the topics in Project A (`commerce360-ingest-dev-alvi`).
- Verified that subscriptions hosted in Project B (`commerce360-analytics-dev-alvi`) successfully received the cross-project events, proving IAM and network isolation is working as designed.

---

## Phase 8 — Dataflow Streaming Pipeline ✅ COMPLETE

**Completed:** 2026-09-16
**Implementation Details:**
- Developed Apache Beam pipeline (`dataflow_pipeline.py`)
- Configured local execution via `DirectRunner` with ADC impersonation.
- Real-time sink to BigQuery bronze tables verified.

---

## Phase 9 — Service Account Impersonation + WIF ✅ COMPLETE

**Completed:** 2026-09-16
**Implementation Details:**
- Defined the local vs production authentication strategy.
- Created `IMPERSONATION_VS_WORKLOAD_IDENTITY.md` in the external interview prep folder.
- Demonstrated least-privilege security model by forcing terminal impersonation of streaming service accounts.

---

## Phase 10 — Composer Orchestration ⬜ DEFERRED

**Justification required before starting.** Cost: $50–150/month.

---

## Phase 11 — Observability + Failure Simulations ✅ COMPLETE

**Completed:** 2026-09-16
**Implementation Details:**
- Designed a two-tiered DLQ approach (Pub/Sub Native + Application DLQ).
- Implemented Tagged Outputs in `dataflow_pipeline.py` to route parse failures gracefully.
- Created `dlq_table` using Terraform in the Analytics project.
- Simulated pipeline failure via `publish_bad_events.py` and successfully captured exceptions and payloads in BigQuery without crashing the stream.

---

## Phase 12 — Security + CI/CD Hardening ✅ COMPLETE

**Completed:** 2026-09-16
**Implementation Details:**
- Defined Workload Identity Federation (WIF) pool and provider via Terraform to secure CI/CD access.
- Created `.github/workflows/terraform-ci.yml` (Checkov scanning, formatting, planning).
- Created `.github/workflows/python-ci.yml` (Ruff linting, PyTest).

---

## Known Limitations

- Staging and production environments are simulated via config files only (no actual cloud deployments in early phases)
- Composer is deferred pending cost justification
- Project C (BI sharing) deferred until Projects A and B are stable

---

## Open Items

See [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) for full ADR log.

| # | Item | Status |
|---|---|---|
| 1 | GCP billing account confirmed | ✅ Resolved (`01C28A-FD425B-861407`) |
| 2 | Actual Project A ID | ✅ Resolved (`commerce360-ingest-dev-alvi`) |
| 3 | Actual Project B ID | ✅ Resolved (`commerce360-analytics-dev-alvi`) |
| 4 | GitHub repository URL | ⬜ Pending user response |
| 5 | Budget ceiling | ✅ Using $20/month default (Current cost: $0.00) |
