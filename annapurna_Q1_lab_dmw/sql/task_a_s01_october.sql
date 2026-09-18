-- Task A: partition pruning proof for one store in one month
INSTALL httpfs;
LOAD httpfs;

CREATE OR REPLACE SECRET minio_secret (
    TYPE S3,
    KEY_ID '<MINIO_ACCESS_KEY>',
    SECRET '<MINIO_SECRET_KEY>',
    ENDPOINT 'localhost:9000',
    URL_STYLE 'path',
    USE_SSL false
);

SELECT
    store_id,
    business_year,
    business_month,
    COUNT(*) AS rows,
    ROUND(SUM(revenue_paise) / 100.0, 2) AS revenue
FROM read_parquet(
    's3://annapurna/sales/business_year=*/business_month=*/store_id=*/*.parquet',
    hive_partitioning = true
)
WHERE business_year = 2024
  AND business_month = 10
  AND store_id = 'S01'
GROUP BY store_id, business_year, business_month;

EXPLAIN ANALYZE
SELECT ROUND(SUM(revenue_paise) / 100.0, 2) AS revenue
FROM read_parquet(
    's3://annapurna/sales/business_year=*/business_month=*/store_id=*/*.parquet',
    hive_partitioning = true
)
WHERE business_year = 2024
  AND business_month = 10
  AND store_id = 'S01';
