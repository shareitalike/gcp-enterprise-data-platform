import pytest
import pandas as pd
from data_generator.entities.customers import CustomerGenerator
from data_generator.entities.products import ProductGenerator
from data_generator.entities.campaigns import CampaignGenerator
from data_generator.entities.inventory import InventoryGenerator
from data_generator.entities.orders import OrderGenerator


def test_customer_generator():
    gen = CustomerGenerator(seed=42)
    df = gen.generate(count=10)
    assert len(df) == 10
    assert "customer_id" in df.columns
    assert "email_hash" in df.columns
    
def test_product_generator():
    gen = ProductGenerator(seed=42)
    df = gen.generate(count=10)
    assert len(df) == 10
    assert "product_id" in df.columns

def test_dependent_generators():
    cust_gen = CustomerGenerator(seed=42)
    cust_df = cust_gen.generate(count=5)
    customer_ids = cust_df["customer_id"].tolist()
    
    prod_gen = ProductGenerator(seed=42)
    prod_df = prod_gen.generate(count=5)
    product_ids = prod_df["product_id"].tolist()
    
    inv_gen = InventoryGenerator(seed=42)
    inv_df = inv_gen.generate(count=5, product_ids=product_ids)
    assert len(inv_df) == 5
    assert "inventory_id" in inv_df.columns
    # Ensure inventory references a valid product
    assert inv_df["product_id"].iloc[0] in product_ids
    
    order_gen = OrderGenerator(seed=42)
    order_df = order_gen.generate(count=5, customer_ids=customer_ids)
    assert len(order_df) == 5
    # Ensure order references a valid customer
    assert order_df["customer_id"].iloc[0] in customer_ids
