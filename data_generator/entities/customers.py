import hashlib
import uuid
import pandas as pd
from datetime import datetime, timezone
from typing import Any

from .base import BaseGenerator


class CustomerGenerator(BaseGenerator):
    @property
    def entity_name(self) -> str:
        return "customers"

    @property
    def schema_version(self) -> str:
        return "1.0"

    def generate(self, count: int, **kwargs: Any) -> pd.DataFrame:
        records = []
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        
        for i in range(count):
            email = self.faker.unique.email()
            email_hash = hashlib.sha256(email.encode("utf-8")).hexdigest()
            
            signup_date = self.faker.date_between(start_date="-3y", end_date="today")
            
            records.append({
                "customer_id": str(uuid.UUID(int=self.faker.random.getrandbits(128), version=4)),
                "source_customer_id": f"CUST-{10000 + i}",
                "email_hash": email_hash,
                "first_name": self.faker.first_name(),
                "last_name": self.faker.last_name(),
                "country_code": self.faker.country_code(),
                "city": self.faker.city() if self.faker.boolean(chance_of_getting_true=80) else None,
                "signup_date": signup_date.isoformat(),
                "customer_segment": self.faker.random_element(elements=("BRONZE", "SILVER", "GOLD", "PLATINUM")),
                "loyalty_points": self.faker.random_int(min=0, max=10000),
                "is_active": self.faker.boolean(chance_of_getting_true=90),
                "created_at": now,
                "updated_at": now,
                "_schema_version": self.schema_version,
            })
            
        df = pd.DataFrame(records)
        self.validate_dataframe(df)
        return df
