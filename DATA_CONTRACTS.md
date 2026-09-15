# Data Contracts — GCP Commerce360

Data contracts define the agreed schema, quality SLAs, and field-level rules for each entity.
These drive: synthetic data generation, schema validation at ingestion, Silver-layer checks,
and Gold-layer referential integrity.

---

## Contract Format

Each contract specifies:
- Entity name and source system
- Ingestion mode and frequency
- Primary key
- Required fields (nulls not permitted)
- Field-level types and constraints
- Quality SLAs (acceptable null %, acceptable duplicate %)
- Downstream consumers

---

## CUSTOMERS

| Property | Value |
|---|---|
| Source system | CRM |
| Ingestion mode | Batch (daily) |
| File format | JSON Lines |
| Primary key | `customer_id` |
| Business key | `email_hash` |
| SCD type | Type 2 (tracked in Gold `dim_customer`) |

### Fields

| Field | Type | Required | Constraints |
|---|---|---|---|
| `customer_id` | STRING | ✅ | UUID format |
| `source_customer_id` | STRING | ✅ | — |
| `email_hash` | STRING | ✅ | SHA-256 hex (64 chars) |
| `first_name` | STRING | ✅ | — |
| `last_name` | STRING | ✅ | — |
| `country_code` | STRING | ✅ | ISO 3166-1 alpha-2 |
| `city` | STRING | ❌ | — |
| `signup_date` | DATE | ✅ | >= 2019-01-01 |
| `customer_segment` | STRING | ✅ | BRONZE, SILVER, GOLD, PLATINUM |
| `loyalty_points` | INTEGER | ✅ | >= 0 |
| `is_active` | BOOLEAN | ✅ | — |
| `created_at` | TIMESTAMP | ✅ | — |
| `updated_at` | TIMESTAMP | ✅ | >= created_at |
| `_schema_version` | STRING | ✅ | e.g. "1.0" |

### Quality SLA
- Null rate on required fields: 0%
- Duplicate `customer_id`: 0%
- Invalid `country_code`: < 0.1%
- `updated_at` < `created_at`: 0%

---

## PRODUCTS

| Property | Value |
|---|---|
| Source system | Product catalog |
| Ingestion mode | Batch (daily) |
| File format | JSON Lines |
| Primary key | `product_id` |
| Business key | `sku` |

### Fields

| Field | Type | Required | Constraints |
|---|---|---|---|
| `product_id` | STRING | ✅ | UUID format |
| `source_product_id` | STRING | ✅ | — |
| `sku` | STRING | ✅ | Unique within file |
| `product_name` | STRING | ✅ | Non-empty |
| `category_l1` | STRING | ✅ | — |
| `category_l2` | STRING | ❌ | — |
| `brand` | STRING | ❌ | — |
| `unit_price` | NUMERIC | ✅ | > 0 |
| `cost_price` | NUMERIC | ✅ | > 0, <= unit_price |
| `is_active` | BOOLEAN | ✅ | — |
| `created_at` | TIMESTAMP | ✅ | — |
| `updated_at` | TIMESTAMP | ✅ | >= created_at |

### Quality SLA
- Null rate on required fields: 0%
- Duplicate `sku`: 0%
- `cost_price` > `unit_price`: 0% (data quality failure, not a business rule)
- `unit_price` <= 0: 0%

---

## ORDERS

| Property | Value |
|---|---|
| Source system | Order management system |
| Ingestion mode | Batch (hourly micro-batch) + streaming events |
| File format | JSON Lines |
| Primary key | `order_id` |
| FK | `customer_id` → CUSTOMERS, `campaign_id` → CAMPAIGNS (nullable) |

### Fields

| Field | Type | Required | Constraints |
|---|---|---|---|
| `order_id` | STRING | ✅ | UUID |
| `source_order_id` | STRING | ✅ | — |
| `customer_id` | STRING | ✅ | Must exist in CUSTOMERS |
| `campaign_id` | STRING | ❌ | Must exist in CAMPAIGNS if set |
| `order_status` | STRING | ✅ | PENDING, CONFIRMED, SHIPPED, DELIVERED, CANCELLED, RETURNED |
| `order_date` | TIMESTAMP | ✅ | — |
| `shipped_date` | TIMESTAMP | ❌ | >= order_date if set |
| `delivered_date` | TIMESTAMP | ❌ | >= shipped_date if set |
| `total_amount` | NUMERIC | ✅ | > 0 |
| `discount_amount` | NUMERIC | ✅ | >= 0 |
| `tax_amount` | NUMERIC | ✅ | >= 0 |
| `currency_code` | STRING | ✅ | ISO 4217 (3 chars) |
| `channel` | STRING | ✅ | WEB, MOBILE, APP |
| `created_at` | TIMESTAMP | ✅ | — |
| `updated_at` | TIMESTAMP | ✅ | >= created_at |

### Valid Status Transitions
```
PENDING → CONFIRMED → SHIPPED → DELIVERED
PENDING → CANCELLED
CONFIRMED → CANCELLED
DELIVERED → RETURNED
```
Invalid transitions are flagged as quality failures; records are not quarantined (warn only).

---

## ORDER_ITEMS

| Property | Value |
|---|---|
| Source system | Order management system |
| Ingestion mode | Batch (with Orders) |
| File format | JSON Lines |
| Primary key | `order_item_id` |
| FK | `order_id` → ORDERS, `product_id` → PRODUCTS |

### Fields

| Field | Type | Required | Constraints |
|---|---|---|---|
| `order_item_id` | STRING | ✅ | UUID |
| `order_id` | STRING | ✅ | Must exist in ORDERS (same batch) |
| `product_id` | STRING | ✅ | Must exist in PRODUCTS |
| `quantity` | INTEGER | ✅ | > 0 |
| `unit_price` | NUMERIC | ✅ | > 0 |
| `line_total` | NUMERIC | ✅ | = quantity * unit_price (within tolerance) |
| `discount_amount` | NUMERIC | ✅ | >= 0 |
| `return_quantity` | INTEGER | ✅ | >= 0, <= quantity |
| `return_reason` | STRING | ❌ | Required if return_quantity > 0 |

---

## INVENTORY

| Property | Value |
|---|---|
| Source system | Warehouse management system |
| Ingestion mode | Batch (daily snapshot) |
| File format | CSV |
| Primary key | `inventory_id` |
| FK | `product_id` → PRODUCTS |

### Fields

| Field | Type | Required | Constraints |
|---|---|---|---|
| `inventory_id` | STRING | ✅ | UUID |
| `product_id` | STRING | ✅ | Must exist in PRODUCTS |
| `warehouse_id` | STRING | ✅ | — |
| `quantity_on_hand` | INTEGER | ✅ | >= 0 |
| `quantity_reserved` | INTEGER | ✅ | >= 0 |
| `quantity_available` | INTEGER | ✅ | = quantity_on_hand - quantity_reserved |
| `reorder_level` | INTEGER | ✅ | >= 0 |
| `snapshot_date` | DATE | ✅ | — |

---

## CAMPAIGNS

| Property | Value |
|---|---|
| Source system | Marketing platform |
| Ingestion mode | Batch (daily) |
| File format | JSON Lines |
| Primary key | `campaign_id` |

### Fields

| Field | Type | Required | Constraints |
|---|---|---|---|
| `campaign_id` | STRING | ✅ | UUID |
| `source_campaign_id` | STRING | ✅ | — |
| `campaign_name` | STRING | ✅ | Non-empty |
| `campaign_type` | STRING | ✅ | EMAIL, SMS, PAID_SEARCH, DISPLAY, SOCIAL |
| `channel` | STRING | ✅ | — |
| `start_date` | DATE | ✅ | — |
| `end_date` | DATE | ✅ | >= start_date |
| `budget_amount` | NUMERIC | ✅ | > 0 |
| `spent_amount` | NUMERIC | ✅ | >= 0 |
| `target_segment` | STRING | ❌ | — |
| `is_active` | BOOLEAN | ✅ | — |

---

## CLICKSTREAM_EVENTS

| Property | Value |
|---|---|
| Source system | Website event tracker |
| Ingestion mode | Streaming (Pub/Sub) |
| Message format | JSON |
| Primary key | `event_id` |
| FK | `customer_id` → CUSTOMERS (nullable — anonymous sessions) |
| FK | `product_id` → PRODUCTS (nullable) |

### Fields

| Field | Type | Required | Constraints |
|---|---|---|---|
| `event_id` | STRING | ✅ | UUID |
| `session_id` | STRING | ✅ | — |
| `customer_id` | STRING | ❌ | Must exist in CUSTOMERS if set |
| `anonymous_id` | STRING | ✅ | Required if customer_id is null |
| `event_type` | STRING | ✅ | PAGE_VIEW, PRODUCT_VIEW, ADD_TO_CART, CHECKOUT, PURCHASE, SEARCH |
| `event_timestamp` | TIMESTAMP | ✅ | Client-side clock |
| `ingestion_timestamp` | TIMESTAMP | ✅ | Server-side receipt |
| `page_url` | STRING | ✅ | — |
| `referrer_url` | STRING | ❌ | — |
| `product_id` | STRING | ❌ | Required for PRODUCT_VIEW, ADD_TO_CART |
| `search_query` | STRING | ❌ | Required for SEARCH |
| `device_type` | STRING | ✅ | DESKTOP, MOBILE, TABLET |
| `user_agent_hash` | STRING | ✅ | SHA-256 of user agent string |
| `ip_country` | STRING | ✅ | ISO 3166-1 alpha-2 |

### Streaming SLA
- Allowed lateness (watermark): 10 minutes
- Events arriving > 10 minutes late: accepted but flagged `_is_late_arrival = true`
- Deduplication window: 5 minutes on `event_id`

---

## Schema Versioning Policy

- Field additions (new nullable fields): additive change; schema version minor bump (1.0 → 1.1)
- Field type changes: breaking change; schema version major bump (1.0 → 2.0); requires explicit migration
- Field removals: breaking change; major bump; old field retained as nullable in Silver
- Schema version stored in `_schema_version` on every record
- Bronze retains all schema versions; Silver enforces current version contract
