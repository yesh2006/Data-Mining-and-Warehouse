-- Task E: sales from MinIO + dimensions from PostgreSQL
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

-- October path is deliberately embedded to show that only October store
-- partitions are read.
EXPLAIN ANALYZE
SELECT
    st.store_id,
    st.store_name,
    c.category_name,
    ROUND(SUM(f.revenue_paise) / 100.0, 2) AS revenue
FROM read_parquet(
    's3://annapurna/sales/business_year=2024/business_month=10/store_id=*/data.parquet',
    hive_partitioning = true
) f
JOIN pg.dashboard.dim_store st
    ON f.store_id = st.store_id
JOIN pg.dashboard.dim_product p
    ON f.product_sk = p.product_sk
JOIN pg.dashboard.dim_category c
    ON p.category_id = c.category_id
GROUP BY st.store_id, st.store_name, c.category_name
ORDER BY st.store_id, c.category_name;
