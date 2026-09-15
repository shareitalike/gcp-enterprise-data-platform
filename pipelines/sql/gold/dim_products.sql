CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.gold.dim_products` (
  product_id STRING,
  sku STRING,
  product_name STRING,
  category_l1 STRING,
  category_l2 STRING,
  brand STRING,
  unit_price NUMERIC,
  cost_price NUMERIC,
  is_active BOOL
);

MERGE `{PROJECT_ID}.gold.dim_products` T
USING `{PROJECT_ID}.silver.products` S
ON T.product_id = S.product_id
WHEN MATCHED THEN
  UPDATE SET
    sku = S.sku,
    product_name = S.product_name,
    category_l1 = S.category_l1,
    category_l2 = S.category_l2,
    brand = S.brand,
    unit_price = S.unit_price,
    cost_price = S.cost_price,
    is_active = S.is_active
WHEN NOT MATCHED THEN
  INSERT (product_id, sku, product_name, category_l1, category_l2, brand, unit_price, cost_price, is_active)
  VALUES (S.product_id, S.sku, S.product_name, S.category_l1, S.category_l2, S.brand, S.unit_price, S.cost_price, S.is_active);
