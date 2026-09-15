import hashlib
import uuid
import pandas as pd
from datetime import datetime, timezone
from typing import Any

from .base import BaseGenerator


class ClickstreamGenerator(BaseGenerator):
    @property
    def entity_name(self) -> str:
        return "clickstream_events"

    @property
    def schema_version(self) -> str:
        return "1.0"

    def generate(self, count: int, **kwargs: Any) -> pd.DataFrame:
        customer_ids = kwargs.get("customer_ids", [])
        product_ids = kwargs.get("product_ids", [])
        
        # Don't strictly require customers/products for clicks, but prefer them if available
        
        records = []
        now = datetime.now(timezone.utc)
        
        event_types = ["PAGE_VIEW", "PRODUCT_VIEW", "ADD_TO_CART", "CHECKOUT", "PURCHASE", "SEARCH"]
        devices = ["DESKTOP", "MOBILE", "TABLET"]
        
        for i in range(count):
            event_ts = self.faker.date_time_between(start_date="-30d", end_date="now", tzinfo=timezone.utc)
            ingest_ts = event_ts # simulate real time
            
            is_known = self.faker.boolean(40) and customer_ids
            cust_id = self.faker.random_element(elements=customer_ids) if is_known else None
            
            event_type = self.faker.random_element(elements=event_types)
            prod_id = None
            if event_type in ["PRODUCT_VIEW", "ADD_TO_CART", "PURCHASE"] and product_ids:
                prod_id = self.faker.random_element(elements=product_ids)
                
            ua_hash = hashlib.sha256(self.faker.user_agent().encode("utf-8")).hexdigest()
            
            records.append({
                "event_id": str(uuid.UUID(int=self.faker.random.getrandbits(128), version=4)),
                "session_id": f"SESS-{self.faker.random_number(digits=8)}",
                "customer_id": cust_id,
                "anonymous_id": f"ANON-{self.faker.random_number(digits=10)}",
                "event_type": event_type,
                "event_timestamp": event_ts.isoformat(timespec="seconds"),
                "ingestion_timestamp": ingest_ts.isoformat(timespec="seconds"),
                "page_url": self.faker.uri(),
                "referrer_url": self.faker.uri() if self.faker.boolean(50) else None,
                "product_id": prod_id,
                "search_query": self.faker.word() if event_type == "SEARCH" else None,
                "device_type": self.faker.random_element(elements=devices),
                "user_agent_hash": ua_hash,
                "ip_country": self.faker.country_code(),
                "_schema_version": self.schema_version,
            })
            
        df = pd.DataFrame(records)
        self.validate_dataframe(df)
        return df
