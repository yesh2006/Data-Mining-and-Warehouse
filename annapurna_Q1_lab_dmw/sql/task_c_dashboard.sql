-- Task C: create the analytical fact view and dashboard slice
INSTALL httpfs;
LOAD httpfs;
INSTALL postgres;
LOAD postgres;

CREATE SECRET minio_secret (
    TYPE S3,
    KEY_ID '<MINIO_ACCESS_KEY>',
    SECRET '<MINIO_SECRET_KEY>',
    ENDPOINT 'localhost:9000',
    URL_STYLE 'path',
    USE_SSL false
);

ATTACH 'host=localhost port=5432 dbname=annapurna user=annapurna password=<POSTGRES_PASSWORD>'
AS pg (TYPE POSTGRES, READ_ONLY);

CREATE OR REPLACE VIEW fact_sales AS
SELECT *
FROM read_parquet(
    's3://annapurna/sales/business_year=*/business_month=*/store_id=*/*.parquet',
    hive_partitioning = true
);

-- Store x category x day-of-week x month
SELECT
    st.store_id,
    st.store_name,
    c.category_name,
    d.day_of_week,
    d.day_name,
    d.year,
    d.month,
    d.month_name,
    ROUND(SUM(f.revenue_paise) / 100.0, 2) AS revenue
FROM fact_sales f
JOIN pg.dashboard.dim_store st
    ON f.store_id = st.store_id
JOIN pg.dashboard.dim_product p
    ON f.product_sk = p.product_sk
JOIN pg.dashboard.dim_category c
    ON p.category_id = c.category_id
JOIN pg.dashboard.dim_date d
    ON f.business_date = d.calendar_date
WHERE f.business_year = 2024
  AND f.business_month = 10
GROUP BY
    st.store_id, st.store_name, c.category_name,
    d.day_of_week, d.day_name, d.year, d.month, d.month_name
ORDER BY st.store_id, c.category_name, d.day_of_week;

-- October reconciliation check
SELECT
    ROUND(SUM(revenue_paise) / 100.0, 2) AS october_revenue
FROM fact_sales
WHERE business_year = 2024
  AND business_month = 10;
