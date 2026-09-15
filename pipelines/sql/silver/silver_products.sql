CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.silver.products` (
  product_id STRING,
  source_product_id STRING,
  sku STRING,
  product_name STRING,
  category_l1 STRING,
  category_l2 STRING,
  brand STRING,
  unit_price NUMERIC,
  cost_price NUMERIC,
  is_active BOOL,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  _schema_version STRING
);

MERGE `{PROJECT_ID}.silver.products` T
USING (
  SELECT * EXCEPT(row_num)
  FROM (
    SELECT 
      CAST(product_id AS STRING) AS product_id,
      CAST(source_product_id AS STRING) AS source_product_id,
      CAST(sku AS STRING) AS sku,
      CAST(product_name AS STRING) AS product_name,
      CAST(category_l1 AS STRING) AS category_l1,
      CAST(category_l2 AS STRING) AS category_l2,
      CAST(brand AS STRING) AS brand,
      CAST(unit_price AS NUMERIC) AS unit_price,
      CAST(cost_price AS NUMERIC) AS cost_price,
      CAST(is_active AS BOOL) AS is_active,
      CAST(created_at AS TIMESTAMP) AS created_at,
      CAST(updated_at AS TIMESTAMP) AS updated_at,
      CAST(_schema_version AS STRING) AS _schema_version,
      ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY updated_at DESC) as row_num
    FROM `{PROJECT_ID}.bronze.products`
  )
  WHERE row_num = 1
) S
ON T.product_id = S.product_id
WHEN MATCHED THEN
  UPDATE SET
    source_product_id = S.source_product_id,
    sku = S.sku,
    product_name = S.product_name,
    category_l1 = S.category_l1,
    category_l2 = S.category_l2,
    brand = S.brand,
    unit_price = S.unit_price,
    cost_price = S.cost_price,
    is_active = S.is_active,
    created_at = S.created_at,
    updated_at = S.updated_at,
    _schema_version = S._schema_version
WHEN NOT MATCHED THEN
  INSERT ROW;
