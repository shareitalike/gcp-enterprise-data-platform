CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.silver.orders` (
  order_id STRING,
  source_order_id STRING,
  customer_id STRING,
  campaign_id STRING,
  order_status STRING,
  order_date TIMESTAMP,
  shipped_date TIMESTAMP,
  delivered_date TIMESTAMP,
  total_amount NUMERIC,
  discount_amount NUMERIC,
  tax_amount NUMERIC,
  currency_code STRING,
  channel STRING,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  _schema_version STRING
);

MERGE `{PROJECT_ID}.silver.orders` T
USING (
  SELECT * EXCEPT(row_num)
  FROM (
    SELECT 
      CAST(order_id AS STRING) AS order_id,
      CAST(source_order_id AS STRING) AS source_order_id,
      CAST(customer_id AS STRING) AS customer_id,
      CAST(campaign_id AS STRING) AS campaign_id,
      CAST(order_status AS STRING) AS order_status,
      CAST(order_date AS TIMESTAMP) AS order_date,
      CAST(shipped_date AS TIMESTAMP) AS shipped_date,
      CAST(delivered_date AS TIMESTAMP) AS delivered_date,
      CAST(total_amount AS NUMERIC) AS total_amount,
      CAST(discount_amount AS NUMERIC) AS discount_amount,
      CAST(tax_amount AS NUMERIC) AS tax_amount,
      CAST(currency_code AS STRING) AS currency_code,
      CAST(channel AS STRING) AS channel,
      CAST(created_at AS TIMESTAMP) AS created_at,
      CAST(updated_at AS TIMESTAMP) AS updated_at,
      CAST(_schema_version AS STRING) AS _schema_version,
      ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY updated_at DESC) as row_num
    FROM `{PROJECT_ID}.bronze.orders`
  )
  WHERE row_num = 1
) S
ON T.order_id = S.order_id
WHEN MATCHED THEN
  UPDATE SET
    source_order_id = S.source_order_id,
    customer_id = S.customer_id,
    campaign_id = S.campaign_id,
    order_status = S.order_status,
    order_date = S.order_date,
    shipped_date = S.shipped_date,
    delivered_date = S.delivered_date,
    total_amount = S.total_amount,
    discount_amount = S.discount_amount,
    tax_amount = S.tax_amount,
    currency_code = S.currency_code,
    channel = S.channel,
    created_at = S.created_at,
    updated_at = S.updated_at,
    _schema_version = S._schema_version
WHEN NOT MATCHED THEN
  INSERT ROW;
