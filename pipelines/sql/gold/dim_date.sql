CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.gold.dim_date` (
  date_key DATE,
  year INT64,
  quarter INT64,
  month INT64,
  day INT64,
  day_of_week INT64,
  is_weekend BOOL
);

-- Recreate every time for simplicity, since it's a static dimension
TRUNCATE TABLE `{PROJECT_ID}.gold.dim_date`;

INSERT INTO `{PROJECT_ID}.gold.dim_date`
SELECT
  d AS date_key,
  EXTRACT(YEAR FROM d) AS year,
  EXTRACT(QUARTER FROM d) AS quarter,
  EXTRACT(MONTH FROM d) AS month,
  EXTRACT(DAY FROM d) AS day,
  EXTRACT(DAYOFWEEK FROM d) AS day_of_week,
  EXTRACT(DAYOFWEEK FROM d) IN (1, 7) AS is_weekend
FROM UNNEST(GENERATE_DATE_ARRAY('2019-01-01', '2030-12-31')) AS d;
