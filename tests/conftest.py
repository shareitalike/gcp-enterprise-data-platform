"""
conftest.py — shared pytest fixtures for the Commerce360 test suite.

Fixtures defined here are available to all test modules without import.
Markers:
  unit        — fast, no GCP dependencies
  integration — requires GCP credentials and project IDs in environment
  e2e         — full pipeline run, requires explicit approval
"""

import os
import pytest
import yaml


@pytest.fixture(scope="session")
def local_config():
    """Load the local development config. Used by unit tests that need config values."""
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "configs", "local", "config.yaml"
    )
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def data_gen_seed(local_config):
    """Return the configured random seed. Ensures reproducible test data."""
    return local_config["data_generator"]["seed"]


@pytest.fixture(scope="session")
def small_volumes(local_config):
    """Return small-tier record volumes for unit tests."""
    return local_config["data_generator"]["volumes"]["small"]
