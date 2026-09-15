CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.silver.customers` (
  customer_id STRING,
  source_customer_id STRING,
  email_hash STRING,
  first_name STRING,
  last_name STRING,
  country_code STRING,
  city STRING,
  signup_date DATE,
  customer_segment STRING,
  loyalty_points INT64,
  is_active BOOL,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  _schema_version STRING
);

MERGE `{PROJECT_ID}.silver.customers` T
USING (
  SELECT * EXCEPT(row_num)
  FROM (
    SELECT 
      CAST(customer_id AS STRING) AS customer_id,
      CAST(source_customer_id AS STRING) AS source_customer_id,
      CAST(email_hash AS STRING) AS email_hash,
      CAST(first_name AS STRING) AS first_name,
      CAST(last_name AS STRING) AS last_name,
      CAST(country_code AS STRING) AS country_code,
      CAST(city AS STRING) AS city,
      CAST(signup_date AS DATE) AS signup_date,
      CAST(customer_segment AS STRING) AS customer_segment,
      CAST(loyalty_points AS INT64) AS loyalty_points,
      CAST(is_active AS BOOL) AS is_active,
      CAST(created_at AS TIMESTAMP) AS created_at,
      CAST(updated_at AS TIMESTAMP) AS updated_at,
      CAST(_schema_version AS STRING) AS _schema_version,
      ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC) as row_num
    FROM `{PROJECT_ID}.bronze.customers`
  )
  WHERE row_num = 1
) S
ON T.customer_id = S.customer_id
WHEN MATCHED THEN
  UPDATE SET
    source_customer_id = S.source_customer_id,
    email_hash = S.email_hash,
    first_name = S.first_name,
    last_name = S.last_name,
    country_code = S.country_code,
    city = S.city,
    signup_date = S.signup_date,
    customer_segment = S.customer_segment,
    loyalty_points = S.loyalty_points,
    is_active = S.is_active,
    created_at = S.created_at,
    updated_at = S.updated_at,
    _schema_version = S._schema_version
WHEN NOT MATCHED THEN
  INSERT ROW;
