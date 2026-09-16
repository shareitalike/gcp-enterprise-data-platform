# GCP Enterprise Data Platform

> An end-to-end, production-grade data engineering platform built on Google Cloud Platform, demonstrating real-world enterprise patterns across two isolated GCP projects.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Terraform](https://img.shields.io/badge/Terraform-1.8-purple?logo=terraform)
![Apache Beam](https://img.shields.io/badge/Apache%20Beam-2.x-orange)
![BigQuery](https://img.shields.io/badge/BigQuery-Medallion%20Architecture-green?logo=google-cloud)
![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions%20%2B%20WIF-yellow?logo=github-actions)

---

## What This Is

This is **not a tutorial or a demo**. Every component solves a real engineering problem that data engineers face in production:

- **Cross-project IAM isolation** — two GCP projects with explicit, least-privilege trust bridges
- **Real-time streaming pipeline** — Apache Beam on DirectRunner ingesting Pub/Sub → BigQuery
- **Medallion architecture** — Bronze (raw), Silver (clean), Gold (business-ready) BigQuery layers
- **Two-tiered Dead Letter Queue** — Pub/Sub native DLQ + Application-level BigQuery DLQ
- **100% Infrastructure as Code** — every resource provisioned via Terraform, zero manual clicks
- **Secure CI/CD** — GitHub Actions authenticated via Workload Identity Federation (no JSON keys)

---

## Two-Project Architecture

| Project | Logical Role | Owns |
|---|---|---|
| `commerce360-ingest-dev-alvi` | **Project A — Ingestion** | GCS raw bucket, Pub/Sub topics, ingestion service accounts |
| `commerce360-analytics-dev-alvi` | **Project B — Analytics** | BigQuery datasets (Bronze/Silver/Gold), Dataflow jobs, analytics service accounts |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full visual diagram and cross-project IAM design.

---

## Quickstart (Local — No GCP Required)

```bash
# 1. Clone
git clone https://github.com/shareitalike/gcp-enterprise-data-platform.git
cd gcp-enterprise-data-platform

# 2. Create virtual environment and install
make install-dev

# 3. Copy and review environment config
cp .env.example .env

# 4. Generate small synthetic dataset locally
make generate-small

# 5. Run unit tests
make test
```

---

## Directory Map

```
gcp-enterprise-data-platform/
├── configs/             ← environment-specific configuration (local, dev, staging)
├── data_generator/      ← synthetic data generation for 7 entities (7 entities, strict referential integrity)
├── infra/terraform/     ← Terraform modules and per-environment stacks
├── ingestion/           ← batch load scripts and streaming publishers/consumers
├── pipelines/           ← SQL transforms (Silver & Gold layer MERGE statements)
├── quality/             ← data quality check framework
├── tests/               ← unit, integration, data quality tests
└── docs/                ← runbooks, failure scenarios, IAM guides
```

---

## Implementation Phases

| Phase | Status | Focus |
|---|---|---|
| 0 | ✅ Complete | Architecture and design |
| 1 | ✅ Complete | Repository foundation |
| 2 | ✅ Complete | GCP project / API / IAM foundation (Terraform) |
| 3 | ✅ Complete | Synthetic data generator |
| 4 | ✅ Complete | Cross-project GCS access + BigQuery batch load |
| 5 | ✅ Complete | BigQuery Bronze/Silver/Gold modeling |
| 6 | ✅ Complete | Incremental batch processing |
| 7 | ✅ Complete | Pub/Sub cross-project streaming |
| 8 | ✅ Complete | Apache Beam Dataflow streaming pipeline |
| 9 | ✅ Complete | Service account impersonation + WIF |
| 10 | ⏸️ Deferred | Composer orchestration (cost: $50–150/month) |
| 11 | ✅ Complete | Observability + failure simulations (DLQ) |
| 12 | ✅ Complete | Security + CI/CD hardening (WIF + GitHub Actions) |

---

## Key Documents

| Document | Purpose |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Visual diagram, cross-project IAM design, streaming architecture |
| [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) | Architecture Decision Records (ADRs) |
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | Phase-by-phase implementation log |
| [DATA_CONTRACTS.md](DATA_CONTRACTS.md) | Entity schemas and data quality SLAs |
| [SECURITY.md](SECURITY.md) | IAM design, secrets policy, audit logging |
| [COST_GUIDE.md](COST_GUIDE.md) | Cost analysis per phase and per service |
