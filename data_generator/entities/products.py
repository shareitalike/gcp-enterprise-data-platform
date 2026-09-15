import uuid
import pandas as pd
from datetime import datetime, timezone
from typing import Any

from .base import BaseGenerator


class ProductGenerator(BaseGenerator):
    @property
    def entity_name(self) -> str:
        return "products"

    @property
    def schema_version(self) -> str:
        return "1.0"

    def generate(self, count: int, **kwargs: Any) -> pd.DataFrame:
        records = []
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        
        categories = {
            "Electronics": ["Laptops", "Smartphones", "Accessories", "Audio"],
            "Clothing": ["Men", "Women", "Kids", "Shoes"],
            "Home": ["Furniture", "Decor", "Kitchen", "Bedding"],
            "Sports": ["Fitness", "Outdoors", "Team Sports"]
        }
        
        brands = ["TechCorp", "Fashionista", "HomeGoods Co", "FitGear", "Generic", None]
        
        for i in range(count):
            cat_l1 = self.faker.random_element(elements=list(categories.keys()))
            cat_l2 = self.faker.random_element(elements=categories[cat_l1])
            
            cost = round(self.faker.random.uniform(5.0, 500.0), 2)
            margin = self.faker.random.uniform(1.1, 2.5)
            price = round(cost * margin, 2)
            
            records.append({
                "product_id": str(uuid.UUID(int=self.faker.random.getrandbits(128), version=4)),
                "source_product_id": f"PROD-{10000 + i}",
                "sku": f"SKU-{cat_l1[:3].upper()}-{cat_l2[:3].upper()}-{self.faker.random_number(digits=5)}",
                "product_name": f"{self.faker.word().capitalize()} {cat_l2[:-1]}",
                "category_l1": cat_l1,
                "category_l2": cat_l2,
                "brand": self.faker.random_element(elements=brands),
                "unit_price": price,
                "cost_price": cost,
                "is_active": self.faker.boolean(chance_of_getting_true=95),
                "created_at": now,
                "updated_at": now,
                "_schema_version": self.schema_version,
            })
            
        df = pd.DataFrame(records)
        self.validate_dataframe(df)
        return df
