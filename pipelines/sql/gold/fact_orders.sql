CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.gold.fact_orders` (
  order_id STRING,
  customer_id STRING,
  campaign_id STRING,
  order_item_id STRING,
  product_id STRING,
  order_date TIMESTAMP,
  order_status STRING,
  quantity INT64,
  unit_price NUMERIC,
  line_total NUMERIC,
  item_discount NUMERIC,
  order_channel STRING,
  currency_code STRING
);

-- Note: Fact tables are often append-only, but since we re-run pipelines and orders can change status,
-- we'll use a MERGE to handle both inserts and updates idempotently.
MERGE `{PROJECT_ID}.gold.fact_orders` T
USING (
  SELECT 
    O.order_id,
    O.customer_id,
    O.campaign_id,
    I.order_item_id,
    I.product_id,
    O.order_date,
    O.order_status,
    I.quantity,
    I.unit_price,
    I.line_total,
    I.discount_amount AS item_discount,
    O.channel AS order_channel,
    O.currency_code
  FROM `{PROJECT_ID}.silver.orders` O
  JOIN `{PROJECT_ID}.silver.order_items` I
    ON O.order_id = I.order_id
) S
ON T.order_item_id = S.order_item_id
WHEN MATCHED THEN
  UPDATE SET
    customer_id = S.customer_id,
    campaign_id = S.campaign_id,
    product_id = S.product_id,
    order_date = S.order_date,
    order_status = S.order_status,
    quantity = S.quantity,
    unit_price = S.unit_price,
    line_total = S.line_total,
    item_discount = S.item_discount,
    order_channel = S.order_channel,
    currency_code = S.currency_code
WHEN NOT MATCHED THEN
  INSERT (order_id, customer_id, campaign_id, order_item_id, product_id, order_date, order_status, quantity, unit_price, line_total, item_discount, order_channel, currency_code)
  VALUES (S.order_id, S.customer_id, S.campaign_id, S.order_item_id, S.product_id, S.order_date, S.order_status, S.quantity, S.unit_price, S.line_total, S.item_discount, S.order_channel, S.currency_code);
