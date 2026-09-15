CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.silver.order_items` (
  order_item_id STRING,
  order_id STRING,
  product_id STRING,
  quantity INT64,
  unit_price NUMERIC,
  line_total NUMERIC,
  discount_amount NUMERIC,
  return_quantity INT64,
  return_reason STRING,
  _schema_version STRING
);

MERGE `{PROJECT_ID}.silver.order_items` T
USING (
  SELECT * EXCEPT(row_num)
  FROM (
    SELECT 
      CAST(order_item_id AS STRING) AS order_item_id,
      CAST(order_id AS STRING) AS order_id,
      CAST(product_id AS STRING) AS product_id,
      CAST(quantity AS INT64) AS quantity,
      CAST(unit_price AS NUMERIC) AS unit_price,
      CAST(line_total AS NUMERIC) AS line_total,
      CAST(discount_amount AS NUMERIC) AS discount_amount,
      CAST(return_quantity AS INT64) AS return_quantity,
      CAST(return_reason AS STRING) AS return_reason,
      CAST(_schema_version AS STRING) AS _schema_version,
      ROW_NUMBER() OVER (PARTITION BY order_item_id ORDER BY order_id) as row_num
    FROM `{PROJECT_ID}.bronze.order_items`
  )
  WHERE row_num = 1
) S
ON T.order_item_id = S.order_item_id
WHEN MATCHED THEN
  UPDATE SET
    order_id = S.order_id,
    product_id = S.product_id,
    quantity = S.quantity,
    unit_price = S.unit_price,
    line_total = S.line_total,
    discount_amount = S.discount_amount,
    return_quantity = S.return_quantity,
    return_reason = S.return_reason,
    _schema_version = S._schema_version
WHEN NOT MATCHED THEN
  INSERT ROW;
