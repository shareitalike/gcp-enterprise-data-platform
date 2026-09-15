"""
tests/unit/test_config.py

Unit tests for the config loader (data_generator.config).
These run locally with no GCP dependencies.

Run with: make test
"""

import os
import pytest
from data_generator.config import load_config, _expand_env_vars


class TestLoadConfig:

    def test_loads_local_config_by_default(self):
        """load_config() with no args should return the local config."""
        # Ensure C360_ENV is not set to something else
        os.environ.pop("C360_ENV", None)
        cfg = load_config()
        assert cfg["environment"] == "local"

    def test_loads_local_config_explicitly(self):
        cfg = load_config(env="local")
        assert cfg["environment"] == "local"

    def test_local_config_has_data_generator_section(self):
        cfg = load_config(env="local")
        assert "data_generator" in cfg
        assert "seed" in cfg["data_generator"]
        assert "volumes" in cfg["data_generator"]

    def test_local_config_seed_is_integer(self):
        cfg = load_config(env="local")
        assert isinstance(cfg["data_generator"]["seed"], int)

    def test_local_config_small_volumes_are_positive(self):
        cfg = load_config(env="local")
        volumes = cfg["data_generator"]["volumes"]["small"]
        for entity, count in volumes.items():
            assert count > 0, f"Volume for '{entity}' must be > 0; got {count}"

    def test_invalid_environment_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown environment"):
            load_config(env="nonexistent-env")

    def test_c360_env_variable_is_respected(self, monkeypatch):
        monkeypatch.setenv("C360_ENV", "local")
        cfg = load_config()
        assert cfg["environment"] == "local"

    def test_ingestion_dev_config_loads(self):
        cfg = load_config(env="ingestion-dev")
        assert cfg["environment"] == "ingestion-dev"

    def test_analytics_dev_config_loads(self):
        cfg = load_config(env="analytics-dev")
        assert cfg["environment"] == "analytics-dev"


class TestExpandEnvVars:

    def test_expands_env_var_in_string(self, monkeypatch):
        monkeypatch.setenv("TEST_PROJECT_ID", "my-test-project")
        result = _expand_env_vars({"key": "${TEST_PROJECT_ID}"})
        assert result["key"] == "my-test-project"

    def test_leaves_non_env_var_strings_unchanged(self):
        result = _expand_env_vars({"key": "plain-string"})
        assert result["key"] == "plain-string"

    def test_expands_nested_dict(self, monkeypatch):
        monkeypatch.setenv("REGION", "us-central1")
        result = _expand_env_vars({"outer": {"inner": "${REGION}"}})
        assert result["outer"]["inner"] == "us-central1"

    def test_expands_list_elements(self, monkeypatch):
        monkeypatch.setenv("BUCKET", "my-bucket")
        result = _expand_env_vars(["${BUCKET}", "static"])
        assert result[0] == "my-bucket"
        assert result[1] == "static"

    def test_integer_values_pass_through(self):
        result = _expand_env_vars({"count": 42})
        assert result["count"] == 42

    def test_none_values_pass_through(self):
        result = _expand_env_vars({"key": None})
        assert result["key"] is None
