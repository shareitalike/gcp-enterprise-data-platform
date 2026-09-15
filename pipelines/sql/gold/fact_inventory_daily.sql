CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.gold.fact_inventory_daily` (
  inventory_id STRING,
  product_id STRING,
  warehouse_id STRING,
  snapshot_date DATE,
  quantity_on_hand INT64,
  quantity_reserved INT64,
  quantity_available INT64
);

MERGE `{PROJECT_ID}.gold.fact_inventory_daily` T
USING `{PROJECT_ID}.silver.inventory` S
ON T.inventory_id = S.inventory_id
WHEN MATCHED THEN
  UPDATE SET
    product_id = S.product_id,
    warehouse_id = S.warehouse_id,
    snapshot_date = S.snapshot_date,
    quantity_on_hand = S.quantity_on_hand,
    quantity_reserved = S.quantity_reserved,
    quantity_available = S.quantity_available
WHEN NOT MATCHED THEN
  INSERT (inventory_id, product_id, warehouse_id, snapshot_date, quantity_on_hand, quantity_reserved, quantity_available)
  VALUES (S.inventory_id, S.product_id, S.warehouse_id, S.snapshot_date, S.quantity_on_hand, S.quantity_reserved, S.quantity_available);
