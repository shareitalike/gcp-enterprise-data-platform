CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.gold.fact_clickstream` (
  event_id STRING,
  session_id STRING,
  customer_id STRING,
  product_id STRING,
  event_type STRING,
  event_timestamp TIMESTAMP,
  page_url STRING,
  device_type STRING,
  ip_country STRING
);

MERGE `{PROJECT_ID}.gold.fact_clickstream` T
USING (
  SELECT 
    event_id,
    session_id,
    customer_id,
    product_id,
    event_type,
    event_timestamp,
    page_url,
    device_type,
    ip_country
  FROM `{PROJECT_ID}.silver.clickstream_events`
) S
ON T.event_id = S.event_id
WHEN MATCHED THEN
  UPDATE SET
    session_id = S.session_id,
    customer_id = S.customer_id,
    product_id = S.product_id,
    event_type = S.event_type,
    event_timestamp = S.event_timestamp,
    page_url = S.page_url,
    device_type = S.device_type,
    ip_country = S.ip_country
WHEN NOT MATCHED THEN
  INSERT ROW;
