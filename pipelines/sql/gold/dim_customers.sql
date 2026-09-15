CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.gold.dim_customers` (
  customer_sk STRING, -- Surrogate key for SCD2
  customer_id STRING,
  email_hash STRING,
  first_name STRING,
  last_name STRING,
  country_code STRING,
  city STRING,
  customer_segment STRING,
  valid_from TIMESTAMP,
  valid_to TIMESTAMP,
  is_current BOOL
);

-- SCD Type 2 logic
-- 1. Identify new records or changed records
-- 2. Update `valid_to` and `is_current` of existing records
-- 3. Insert new versions
MERGE `{PROJECT_ID}.gold.dim_customers` T
USING (
  WITH updates AS (
    SELECT 
      S.customer_id,
      S.email_hash,
      S.first_name,
      S.last_name,
      S.country_code,
      S.city,
      S.customer_segment,
      S.updated_at AS valid_from
    FROM `{PROJECT_ID}.silver.customers` S
  ),
  current_dim AS (
    SELECT * FROM `{PROJECT_ID}.gold.dim_customers` WHERE is_current = TRUE
  )
  -- Insert records (either completely new or new versions of existing)
  SELECT 
    GENERATE_UUID() AS customer_sk,
    U.customer_id,
    U.email_hash,
    U.first_name,
    U.last_name,
    U.country_code,
    U.city,
    U.customer_segment,
    U.valid_from,
    CAST(NULL AS TIMESTAMP) AS valid_to,
    TRUE AS is_current
  FROM updates U
  LEFT JOIN current_dim C ON U.customer_id = C.customer_id
  WHERE C.customer_id IS NULL OR C.email_hash != U.email_hash OR C.customer_segment != U.customer_segment
) S
ON FALSE -- Always insert the new state
WHEN NOT MATCHED THEN
  INSERT ROW;

-- After inserting new active rows, we must close out the old active rows
UPDATE `{PROJECT_ID}.gold.dim_customers` T
SET 
  valid_to = S.valid_from,
  is_current = FALSE
FROM (
  SELECT customer_id, MIN(valid_from) AS valid_from
  FROM `{PROJECT_ID}.gold.dim_customers`
  WHERE is_current = TRUE
  GROUP BY customer_id
  HAVING COUNT(*) > 1 -- Means a new current row was just inserted
) S
WHERE T.customer_id = S.customer_id 
  AND T.is_current = TRUE 
  AND T.valid_from < S.valid_from;
