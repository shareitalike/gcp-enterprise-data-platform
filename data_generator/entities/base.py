import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd
from faker import Faker
from jsonschema import validate, ValidationError


_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


class BaseGenerator(ABC):
    """
    Abstract base class for all synthetic data generators.
    Provides shared Faker instance, schema validation, and common utilities.
    """

    def __init__(self, seed: int):
        self.faker = Faker()
        Faker.seed(seed)
        self.seed = seed

    @property
    @abstractmethod
    def entity_name(self) -> str:
        """The name of the entity (matches the schema filename)."""
        pass

    @property
    @abstractmethod
    def schema_version(self) -> str:
        """The _schema_version value for this entity."""
        pass

    @abstractmethod
    def generate(self, count: int, **kwargs: Any) -> pd.DataFrame:
        """
        Generate `count` records.
        Kwargs can be used to pass dependencies (e.g. valid customer_ids for orders).
        """
        pass

    def validate_dataframe(self, df: pd.DataFrame) -> None:
        """
        Validate every row in the DataFrame against the JSON schema.
        Raises ValidationError if any row violates the schema.
        """
        schema_path = _SCHEMA_DIR / f"{self.entity_name}.json"
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        # Convert DF to list of dicts. We use 'records' orient.
        # But pandas dates are timestamps, we need to convert to strings first
        # to properly test JSON serialization.
        # Instead of deep conversion here, we'll just parse JSON from pandas
        json_records = json.loads(df.to_json(orient="records", date_format="iso"))

        for idx, record in enumerate(json_records):
            try:
                validate(instance=record, schema=schema)
            except ValidationError as e:
                raise ValidationError(
                    f"Schema validation failed for {self.entity_name} at row {idx}:\n"
                    f"Record: {record}\n"
                    f"Error: {e.message}"
                ) from e
