CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.silver.clickstream_events` (
  event_id STRING,
  session_id STRING,
  customer_id STRING,
  anonymous_id STRING,
  event_type STRING,
  event_timestamp TIMESTAMP,
  ingestion_timestamp TIMESTAMP,
  page_url STRING,
  referrer_url STRING,
  product_id STRING,
  search_query STRING,
  device_type STRING,
  user_agent_hash STRING,
  ip_country STRING,
  _schema_version STRING
);

MERGE `{PROJECT_ID}.silver.clickstream_events` T
USING (
  SELECT * EXCEPT(row_num)
  FROM (
    SELECT 
      CAST(event_id AS STRING) AS event_id,
      CAST(session_id AS STRING) AS session_id,
      CAST(customer_id AS STRING) AS customer_id,
      CAST(anonymous_id AS STRING) AS anonymous_id,
      CAST(event_type AS STRING) AS event_type,
      CAST(event_timestamp AS TIMESTAMP) AS event_timestamp,
      CAST(ingestion_timestamp AS TIMESTAMP) AS ingestion_timestamp,
      CAST(page_url AS STRING) AS page_url,
      CAST(referrer_url AS STRING) AS referrer_url,
      CAST(product_id AS STRING) AS product_id,
      CAST(search_query AS STRING) AS search_query,
      CAST(device_type AS STRING) AS device_type,
      CAST(user_agent_hash AS STRING) AS user_agent_hash,
      CAST(ip_country AS STRING) AS ip_country,
      CAST(_schema_version AS STRING) AS _schema_version,
      ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY ingestion_timestamp DESC) as row_num
    FROM `{PROJECT_ID}.bronze.clickstream_events`
  )
  WHERE row_num = 1
) S
ON T.event_id = S.event_id
WHEN MATCHED THEN
  UPDATE SET
    session_id = S.session_id,
    customer_id = S.customer_id,
    anonymous_id = S.anonymous_id,
    event_type = S.event_type,
    event_timestamp = S.event_timestamp,
    ingestion_timestamp = S.ingestion_timestamp,
    page_url = S.page_url,
    referrer_url = S.referrer_url,
    product_id = S.product_id,
    search_query = S.search_query,
    device_type = S.device_type,
    user_agent_hash = S.user_agent_hash,
    ip_country = S.ip_country,
    _schema_version = S._schema_version
WHEN NOT MATCHED THEN
  INSERT ROW;
