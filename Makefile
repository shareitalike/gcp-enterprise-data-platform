# ── Virtual environment ───────────────────────────────────────────────────────
.PHONY: venv install install-dev clean

PYTHON   := python3.11
VENV_DIR := .venv
PIP      := $(VENV_DIR)/Scripts/pip      # Windows path; Linux: $(VENV_DIR)/bin/pip
PYTHON_  := $(VENV_DIR)/Scripts/python   # Windows path; Linux: $(VENV_DIR)/bin/python

venv:
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "✅  venv created at $(VENV_DIR)"
	@echo "   Activate with:  .venv\\Scripts\\activate  (Windows)"

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -e .
	@echo "✅  dependencies installed"

install-dev: venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	pre-commit install
	@echo "✅  dev dependencies installed"

clean:
	rm -rf $(VENV_DIR) __pycache__ .pytest_cache dist build *.egg-info

# ── Linting & formatting ──────────────────────────────────────────────────────
.PHONY: lint format typecheck

lint:
	$(PYTHON_) -m ruff check .

format:
	$(PYTHON_) -m black .
	$(PYTHON_) -m ruff check --fix .

typecheck:
	$(PYTHON_) -m mypy data_generator/ ingestion/ pipelines/ quality/

# ── Tests ─────────────────────────────────────────────────────────────────────
.PHONY: test test-unit test-integration

test-unit:
	$(PYTHON_) -m pytest tests/unit/ -m unit -v

test-integration:
	@echo "⚠️  Integration tests require GCP credentials and ANALYTICS_PROJECT_ID set."
	$(PYTHON_) -m pytest tests/integration/ -m integration -v

test:
	$(PYTHON_) -m pytest tests/unit/ -m unit -v

# ── Data generation ───────────────────────────────────────────────────────────
.PHONY: generate-small generate-medium

generate-small:
	$(PYTHON_) -m data_generator.generator \
		--tier small \
		--seed 42 \
		--output-dir data/generated/small \
		--format json

generate-medium:
	@echo "⚠️  Medium tier generates ~100K records. Confirm before uploading to GCS."
	$(PYTHON_) -m data_generator.generator \
		--tier medium \
		--seed 42 \
		--output-dir data/generated/medium \
		--format json

# ── Terraform helpers ─────────────────────────────────────────────────────────
.PHONY: tf-init-ingestion tf-plan-ingestion tf-init-analytics tf-plan-analytics

TF_INGESTION := infra/terraform/environments/ingestion-dev
TF_ANALYTICS := infra/terraform/environments/analytics-dev

tf-init-ingestion:
	terraform -chdir=$(TF_INGESTION) init

tf-plan-ingestion:
	terraform -chdir=$(TF_INGESTION) plan -var-file=terraform.tfvars.example

tf-init-analytics:
	terraform -chdir=$(TF_ANALYTICS) init

tf-plan-analytics:
	terraform -chdir=$(TF_ANALYTICS) plan -var-file=terraform.tfvars.example

# ── GCP auth helpers ──────────────────────────────────────────────────────────
.PHONY: gcloud-auth gcloud-whoami

gcloud-auth:
	gcloud auth application-default login

gcloud-whoami:
	gcloud auth list
	gcloud config list project

# ── Help ──────────────────────────────────────────────────────────────────────
.PHONY: help

help:
	@echo ""
	@echo "GCP Commerce360 — Available Targets"
	@echo "──────────────────────────────────────────────"
	@echo "  make install          Install runtime dependencies"
	@echo "  make install-dev      Install dev dependencies + pre-commit"
	@echo "  make lint             Run ruff linter"
	@echo "  make format           Run black + ruff --fix"
	@echo "  make typecheck        Run mypy"
	@echo "  make test             Run unit tests"
	@echo "  make generate-small   Generate small synthetic dataset locally"
	@echo "  make tf-plan-ingestion  Terraform plan for Project A"
	@echo "  make tf-plan-analytics  Terraform plan for Project B"
	@echo "  make gcloud-whoami    Show active GCP identity"
	@echo ""
