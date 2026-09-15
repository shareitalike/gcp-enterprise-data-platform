import uuid
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Any

from .base import BaseGenerator


class OrderGenerator(BaseGenerator):
    @property
    def entity_name(self) -> str:
        return "orders"

    @property
    def schema_version(self) -> str:
        return "1.0"

    def generate(self, count: int, **kwargs: Any) -> pd.DataFrame:
        customer_ids = kwargs.get("customer_ids", [])
        campaign_ids = kwargs.get("campaign_ids", [])
        if not customer_ids:
            raise ValueError("customer_ids must be provided to OrderGenerator")
            
        records = []
        now = datetime.now(timezone.utc)
        
        statuses = ["PENDING", "CONFIRMED", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"]
        channels = ["WEB", "MOBILE", "APP"]
        
        for i in range(count):
            order_date = self.faker.date_time_between(start_date="-1y", end_date="now", tzinfo=timezone.utc)
            
            status = self.faker.random_element(elements=statuses)
            shipped_date = None
            delivered_date = None
            
            if status in ["SHIPPED", "DELIVERED", "RETURNED"]:
                shipped_date = order_date + timedelta(days=self.faker.random_int(min=1, max=3))
            if status in ["DELIVERED", "RETURNED"]:
                delivered_date = shipped_date + timedelta(days=self.faker.random_int(min=1, max=5))
                
            has_campaign = self.faker.boolean(chance_of_getting_true=20) and campaign_ids
            
            # The amounts will be updated after we generate OrderItems, but we initialize them here.
            # However, for schema validation, we need them to be non-zero if required.
            total_amt = round(self.faker.random.uniform(10.0, 1000.0), 2)
            discount = round(total_amt * self.faker.random.uniform(0.0, 0.2), 2) if self.faker.boolean(20) else 0.0
            tax = round((total_amt - discount) * 0.08, 2)
            
            records.append({
                "order_id": str(uuid.UUID(int=self.faker.random.getrandbits(128), version=4)),
                "source_order_id": f"ORD-{100000 + i}",
                "customer_id": self.faker.random_element(elements=customer_ids),
                "campaign_id": self.faker.random_element(elements=campaign_ids) if has_campaign else None,
                "order_status": status,
                "order_date": order_date.isoformat(timespec="seconds"),
                "shipped_date": shipped_date.isoformat(timespec="seconds") if shipped_date else None,
                "delivered_date": delivered_date.isoformat(timespec="seconds") if delivered_date else None,
                "total_amount": total_amt,
                "discount_amount": discount,
                "tax_amount": tax,
                "currency_code": "USD",
                "channel": self.faker.random_element(elements=channels),
                "created_at": order_date.isoformat(timespec="seconds"),
                "updated_at": now.isoformat(timespec="seconds"),
                "_schema_version": self.schema_version,
            })
            
        df = pd.DataFrame(records)
        self.validate_dataframe(df)
        return df
