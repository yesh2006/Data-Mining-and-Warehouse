-- Task C: dashboard dimensions in PostgreSQL
CREATE SCHEMA IF NOT EXISTS dashboard;

CREATE TABLE IF NOT EXISTS dashboard.dim_store AS
SELECT
    ROW_NUMBER() OVER (ORDER BY store_id)::BIGINT AS store_key,
    store_id, store_name, address_line, city, state, region,
    floor_area_sqft, opened_on
FROM stores;

CREATE TABLE IF NOT EXISTS dashboard.dim_category AS
SELECT
    ROW_NUMBER() OVER (ORDER BY category_id)::BIGINT AS category_key,
    category_id, category_name, department, gst_rate
FROM product_categories;

CREATE TABLE IF NOT EXISTS dashboard.dim_product AS
SELECT
    product_sk, product_code, product_name, category_id, brand,
    pack_size, uom, valid_from, valid_to, is_current
FROM products;

DROP TABLE IF EXISTS dashboard.dim_date;
CREATE TABLE dashboard.dim_date AS
SELECT
    TO_CHAR(gs.d::date, 'YYYYMMDD')::INTEGER AS date_key,
    gs.d::date AS calendar_date,
    EXTRACT(YEAR FROM gs.d)::INTEGER AS year,
    EXTRACT(MONTH FROM gs.d)::INTEGER AS month,
    TO_CHAR(gs.d::date, 'FMMonth') AS month_name,
    EXTRACT(ISODOW FROM gs.d)::INTEGER AS day_of_week,
    TO_CHAR(gs.d::date, 'FMDay') AS day_name
FROM GENERATE_SERIES(
    DATE '2024-01-01', DATE '2024-12-31', INTERVAL '1 day'
) AS gs(d);

CREATE INDEX IF NOT EXISTS ix_dim_store_store_id
ON dashboard.dim_store(store_id);
CREATE INDEX IF NOT EXISTS ix_dim_category_category_id
ON dashboard.dim_category(category_id);
CREATE INDEX IF NOT EXISTS ix_dim_product_product_sk
ON dashboard.dim_product(product_sk);
CREATE INDEX IF NOT EXISTS ix_dim_product_code_dates
ON dashboard.dim_product(product_code, valid_from, valid_to);
CREATE INDEX IF NOT EXISTS ix_dim_date_calendar
ON dashboard.dim_date(calendar_date);
