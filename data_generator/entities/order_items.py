import uuid
import pandas as pd
from typing import Any

from .base import BaseGenerator


class OrderItemGenerator(BaseGenerator):
    @property
    def entity_name(self) -> str:
        return "order_items"

    @property
    def schema_version(self) -> str:
        return "1.0"

    def generate(self, count: int, **kwargs: Any) -> pd.DataFrame:
        orders_df = kwargs.get("orders")
        products_df = kwargs.get("products")
        
        if orders_df is None or products_df is None:
            raise ValueError("orders and products dataframes must be provided to OrderItemGenerator")
            
        order_ids = orders_df["order_id"].tolist()
        # We need prices from products to make it realistic
        product_pool = products_df[["product_id", "unit_price"]].to_dict("records")
        
        records = []
        
        for i in range(count):
            order_id = self.faker.random_element(elements=order_ids)
            prod = self.faker.random_element(elements=product_pool)
            
            qty = self.faker.random_int(min=1, max=5)
            unit_price = prod["unit_price"]
            line_total = round(qty * unit_price, 2)
            discount = round(line_total * self.faker.random.uniform(0.1, 0.3), 2) if self.faker.boolean(10) else 0.0
            
            # 5% chance of return
            is_returned = self.faker.boolean(5)
            ret_qty = self.faker.random_int(min=1, max=qty) if is_returned else 0
            ret_reason = self.faker.random_element(["DEFECTIVE", "WRONG_ITEM", "NOT_NEEDED"]) if is_returned else None
            
            records.append({
                "order_item_id": str(uuid.UUID(int=self.faker.random.getrandbits(128), version=4)),
                "order_id": order_id,
                "product_id": prod["product_id"],
                "quantity": qty,
                "unit_price": unit_price,
                "line_total": line_total,
                "discount_amount": discount,
                "return_quantity": ret_qty,
                "return_reason": ret_reason,
                "_schema_version": self.schema_version,
            })
            
        df = pd.DataFrame(records)
        self.validate_dataframe(df)
        return df
