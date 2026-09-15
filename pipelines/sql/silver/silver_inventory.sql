CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.silver.inventory` (
  inventory_id STRING,
  product_id STRING,
  warehouse_id STRING,
  quantity_on_hand INT64,
  quantity_reserved INT64,
  quantity_available INT64,
  reorder_level INT64,
  snapshot_date DATE,
  _schema_version STRING
);

MERGE `{PROJECT_ID}.silver.inventory` T
USING (
  SELECT * EXCEPT(row_num)
  FROM (
    SELECT 
      CAST(inventory_id AS STRING) AS inventory_id,
      CAST(product_id AS STRING) AS product_id,
      CAST(warehouse_id AS STRING) AS warehouse_id,
      CAST(quantity_on_hand AS INT64) AS quantity_on_hand,
      CAST(quantity_reserved AS INT64) AS quantity_reserved,
      CAST(quantity_available AS INT64) AS quantity_available,
      CAST(reorder_level AS INT64) AS reorder_level,
      CAST(snapshot_date AS DATE) AS snapshot_date,
      CAST(_schema_version AS STRING) AS _schema_version,
      ROW_NUMBER() OVER (PARTITION BY inventory_id ORDER BY snapshot_date DESC) as row_num
    FROM `{PROJECT_ID}.bronze.inventory`
  )
  WHERE row_num = 1
) S
ON T.inventory_id = S.inventory_id
WHEN MATCHED THEN
  UPDATE SET
    product_id = S.product_id,
    warehouse_id = S.warehouse_id,
    quantity_on_hand = S.quantity_on_hand,
    quantity_reserved = S.quantity_reserved,
    quantity_available = S.quantity_available,
    reorder_level = S.reorder_level,
    snapshot_date = S.snapshot_date,
    _schema_version = S._schema_version
WHEN NOT MATCHED THEN
  INSERT ROW;
