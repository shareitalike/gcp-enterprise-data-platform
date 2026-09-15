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

## Phase 2 — GCP Foundation (Terraform) ⬜ NOT STARTED

**Blocked on:** User providing real GCP project IDs and billing account confirmation.

**Target resources:**
- Project A: GCS raw bucket, publisher SA, IAM
- Project B: BigQuery datasets (6), analytics SAs (3), IAM
- Audit log configuration on both projects
- Budget alert on both projects

---

## Phase 3 — Synthetic Data Generator ⬜ NOT STARTED

**Target:** `data_generator/` producing all 7 entities in JSON/CSV/Parquet.

---

## Phase 4 — Cross-Project GCS Access + BQ Batch Load ⬜ NOT STARTED

**First cross-project IAM exercise.**

---

## Phase 5 — BigQuery Bronze/Silver/Gold Modeling ⬜ NOT STARTED

---

## Phase 6 — Incremental Batch Processing ⬜ NOT STARTED

---

## Phase 7 — Pub/Sub Cross-Project Streaming ⬜ NOT STARTED

**Second cross-project communication exercise.**

---

## Phase 8 — Dataflow Streaming Pipeline ⬜ NOT STARTED

---

## Phase 9 — Service Account Impersonation + WIF ⬜ NOT STARTED

---

## Phase 10 — Composer Orchestration ⬜ DEFERRED

**Justification required before starting.** Cost: $50–150/month.

---

## Phase 11 — Observability + Failure Simulations ⬜ NOT STARTED

---

## Phase 12 — Security + CI/CD Hardening ⬜ NOT STARTED

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
| 1 | GCP billing account confirmed | ⬜ Pending user response |
| 2 | Actual Project A ID | ⬜ Pending user response |
| 3 | Actual Project B ID | ⬜ Pending user response |
| 4 | GitHub repository URL | ⬜ Pending user response |
| 5 | Budget ceiling | ⬜ Using $20/month default |
