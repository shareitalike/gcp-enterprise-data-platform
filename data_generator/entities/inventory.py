import uuid
import pandas as pd
from datetime import datetime, timezone
from typing import Any

from .base import BaseGenerator


class InventoryGenerator(BaseGenerator):
    @property
    def entity_name(self) -> str:
        return "inventory"

    @property
    def schema_version(self) -> str:
        return "1.0"

    def generate(self, count: int, **kwargs: Any) -> pd.DataFrame:
        product_ids = kwargs.get("product_ids", [])
        if not product_ids:
            raise ValueError("product_ids must be provided to InventoryGenerator")
            
        records = []
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        snapshot_date = datetime.now(timezone.utc).date().isoformat()
        
        warehouses = ["WH-EAST-1", "WH-WEST-1", "WH-CENTRAL-1"]
        
        for i in range(count):
            q_on_hand = self.faker.random_int(min=0, max=5000)
            q_reserved = self.faker.random_int(min=0, max=min(1000, q_on_hand) if q_on_hand > 0 else 0)
            q_avail = q_on_hand - q_reserved
            
            records.append({
                "inventory_id": str(uuid.UUID(int=self.faker.random.getrandbits(128), version=4)),
                "product_id": self.faker.random_element(elements=product_ids),
                "warehouse_id": self.faker.random_element(elements=warehouses),
                "quantity_on_hand": q_on_hand,
                "quantity_reserved": q_reserved,
                "quantity_available": q_avail,
                "reorder_level": self.faker.random_int(min=10, max=100),
                "snapshot_date": snapshot_date,
                "_schema_version": self.schema_version,
            })
            
        df = pd.DataFrame(records)
        self.validate_dataframe(df)
        return df
