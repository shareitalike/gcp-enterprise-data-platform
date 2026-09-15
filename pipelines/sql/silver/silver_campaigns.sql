CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.silver.campaigns` (
  campaign_id STRING,
  source_campaign_id STRING,
  campaign_name STRING,
  campaign_type STRING,
  channel STRING,
  start_date DATE,
  end_date DATE,
  budget_amount NUMERIC,
  spent_amount NUMERIC,
  target_segment STRING,
  is_active BOOL,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  _schema_version STRING
);

MERGE `{PROJECT_ID}.silver.campaigns` T
USING (
  SELECT * EXCEPT(row_num)
  FROM (
    SELECT 
      CAST(campaign_id AS STRING) AS campaign_id,
      CAST(source_campaign_id AS STRING) AS source_campaign_id,
      CAST(campaign_name AS STRING) AS campaign_name,
      CAST(campaign_type AS STRING) AS campaign_type,
      CAST(channel AS STRING) AS channel,
      CAST(start_date AS DATE) AS start_date,
      CAST(end_date AS DATE) AS end_date,
      CAST(budget_amount AS NUMERIC) AS budget_amount,
      CAST(spent_amount AS NUMERIC) AS spent_amount,
      CAST(target_segment AS STRING) AS target_segment,
      CAST(is_active AS BOOL) AS is_active,
      CAST(created_at AS TIMESTAMP) AS created_at,
      CAST(updated_at AS TIMESTAMP) AS updated_at,
      CAST(_schema_version AS STRING) AS _schema_version,
      ROW_NUMBER() OVER (PARTITION BY campaign_id ORDER BY updated_at DESC) as row_num
    FROM `{PROJECT_ID}.bronze.campaigns`
  )
  WHERE row_num = 1
) S
ON T.campaign_id = S.campaign_id
WHEN MATCHED THEN
  UPDATE SET
    source_campaign_id = S.source_campaign_id,
    campaign_name = S.campaign_name,
    campaign_type = S.campaign_type,
    channel = S.channel,
    start_date = S.start_date,
    end_date = S.end_date,
    budget_amount = S.budget_amount,
    spent_amount = S.spent_amount,
    target_segment = S.target_segment,
    is_active = S.is_active,
    created_at = S.created_at,
    updated_at = S.updated_at,
    _schema_version = S._schema_version
WHEN NOT MATCHED THEN
  INSERT ROW;
