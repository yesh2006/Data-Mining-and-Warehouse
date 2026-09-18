-- Task F: reconcile pipeline monthly revenue against finance_monthly.csv

WITH pipeline AS (
    SELECT
        printf('%04d-%02d', business_year, CAST(business_month AS INTEGER)) AS month,
        ROUND(SUM(revenue_paise) / 100.0, 2) AS pipeline_revenue
    FROM read_parquet(
        's3://annapurna/sales/business_year=*/business_month=*/store_id=*/*.parquet',
        hive_partitioning = true
    )
    GROUP BY 1
),
finance AS (
    SELECT month, revenue_inr AS finance_revenue
    FROM read_csv_auto('staging/finance_monthly.csv', header=true)
)
SELECT
    f.month,
    ROUND(p.pipeline_revenue, 2) AS pipeline_revenue,
    ROUND(f.finance_revenue, 2) AS finance_revenue,
    ROUND(f.finance_revenue - p.pipeline_revenue, 2) AS difference,
    CASE
        WHEN ABS(f.finance_revenue - p.pipeline_revenue) < 0.01 THEN 'MATCH'
        ELSE 'DIFFERS'
    END AS status
FROM finance f
LEFT JOIN pipeline p ON f.month = p.month
ORDER BY f.month;

-- Show only months that differ.
WITH pipeline AS (
    SELECT
        printf('%04d-%02d', business_year, CAST(business_month AS INTEGER)) AS month,
        ROUND(SUM(revenue_paise) / 100.0, 2) AS pipeline_revenue
    FROM read_parquet(
        's3://annapurna/sales/business_year=*/business_month=*/store_id=*/*.parquet',
        hive_partitioning = true
    )
    GROUP BY 1
),
finance AS (
    SELECT month, revenue_inr AS finance_revenue
    FROM read_csv_auto('staging/finance_monthly.csv', header=true)
)
SELECT
    f.month,
    ROUND(p.pipeline_revenue, 2) AS pipeline_revenue,
    ROUND(f.finance_revenue, 2) AS finance_revenue,
    ROUND(f.finance_revenue - p.pipeline_revenue, 2) AS difference
FROM finance f
JOIN pipeline p ON f.month = p.month
WHERE ABS(f.finance_revenue - p.pipeline_revenue) >= 0.01
ORDER BY f.month;
