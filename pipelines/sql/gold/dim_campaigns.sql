CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.gold.dim_campaigns` (
  campaign_id STRING,
  campaign_name STRING,
  campaign_type STRING,
  channel STRING,
  start_date DATE,
  end_date DATE,
  budget_amount NUMERIC,
  target_segment STRING,
  is_active BOOL
);

MERGE `{PROJECT_ID}.gold.dim_campaigns` T
USING `{PROJECT_ID}.silver.campaigns` S
ON T.campaign_id = S.campaign_id
WHEN MATCHED THEN
  UPDATE SET
    campaign_name = S.campaign_name,
    campaign_type = S.campaign_type,
    channel = S.channel,
    start_date = S.start_date,
    end_date = S.end_date,
    budget_amount = S.budget_amount,
    target_segment = S.target_segment,
    is_active = S.is_active
WHEN NOT MATCHED THEN
  INSERT (campaign_id, campaign_name, campaign_type, channel, start_date, end_date, budget_amount, target_segment, is_active)
  VALUES (S.campaign_id, S.campaign_name, S.campaign_type, S.channel, S.start_date, S.end_date, S.budget_amount, S.target_segment, S.is_active);
