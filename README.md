# GCP Commerce360 — Multi-Project E-Commerce Analytics Platform

## What This Is

A production-oriented, GCP-native e-commerce analytics platform built across **two separate GCP projects** to teach and implement cross-project IAM, resource ownership, billing isolation, and streaming + batch pipeline patterns.

This is **not a tutorial or demo**. Every component solves a real engineering problem.

---

## Two-Project Architecture

| Project | Logical Role | Owns |
|---|---|---|
| `INGESTION_PROJECT_ID` | Project A — Ingestion | GCS raw bucket, Pub/Sub topics, ingestion service accounts |
| `ANALYTICS_PROJECT_ID` | Project B — Analytics | BigQuery datasets (Bronze/Silver/Gold), Dataflow jobs, analytics service accounts |

---

## Quickstart (Local — No GCP Required)

```bash
# 1. Clone
git clone <repo-url>
cd commerce360-gcp

# 2. Create virtual environment and install
make install-dev

# 3. Copy and review environment config
cp .env.example .env
# Edit .env with your GCP project IDs (leave blank for local-only work)

# 4. Generate small synthetic dataset locally
make generate-small

# 5. Run unit tests
make test
```

---

## Directory Map

```
commerce360-gcp/
├── configs/            ← environment-specific configuration (local, dev, staging)
├── data_generator/     ← synthetic data generation for all 7 entities
├── infra/terraform/    ← Terraform modules and per-environment stacks
├── ingestion/          ← batch load scripts and streaming publishers
├── pipelines/          ← Apache Beam jobs and SQL transforms
├── quality/            ← data quality check framework
├── orchestration/      ← Cloud Composer DAGs (Phase 10+)
├── tests/              ← unit, integration, data quality tests
└── docs/               ← runbooks, failure scenarios, IAM guides
```

---

## Implementation Phases

| Phase | Status | Focus |
|---|---|---|
| 0 | ✅ Complete | Architecture and design |
| 1 | 🔄 In Progress | Repository foundation |
| 2 | ⬜ Pending | GCP project / API / IAM foundation (Terraform) |
| 3 | ⬜ Pending | Synthetic data generator |
| 4 | ⬜ Pending | Cross-project GCS access + BigQuery batch load |
| 5 | ⬜ Pending | BigQuery Bronze/Silver/Gold modeling |
| 6 | ⬜ Pending | Incremental batch processing |
| 7 | ⬜ Pending | Pub/Sub cross-project streaming |
| 8 | ⬜ Pending | Dataflow pipeline |
| 9 | ⬜ Pending | Service account impersonation + WIF |
| 10 | ⬜ Pending | Composer orchestration |
| 11 | ⬜ Pending | Observability + failure simulations |
| 12 | ⬜ Pending | Security + CI/CD hardening |

---

## Key Documents

| Document | Purpose |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Detailed component architecture |
| [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) | Architecture Decision Records |
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | Phase-by-phase implementation status |
| [DATA_CONTRACTS.md](DATA_CONTRACTS.md) | Entity schemas and data quality SLAs |
| [SECURITY.md](SECURITY.md) | IAM design, secrets policy, audit logging |
| [COST_GUIDE.md](COST_GUIDE.md) | Cost analysis per phase and per service |
| [docs/runbooks/](docs/runbooks/) | Operational runbooks |
| [docs/cross_project_iam/](docs/cross_project_iam/) | Cross-project IAM guides and exercises |
