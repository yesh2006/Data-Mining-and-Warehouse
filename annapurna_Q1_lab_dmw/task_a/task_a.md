# Task A — Stand up the platform and land the data

## Objective

Provide an object store, relational database and analytical query engine. Land sales data so a store-month query is isolated from other stores and months.

## Platform

- **Object store:** MinIO
- **Relational database:** PostgreSQL 16
- **Analytical engine:** DuckDB 1.5.5
- **ETL:** Python + pandas + PyArrow + boto3 + psycopg2

## Chosen object layout

```text
s3://annapurna/sales/
  business_year=2024/
    business_month=10/
      store_id=S01/data.parquet
      store_id=S02/data.parquet
      ...
      store_id=S12/data.parquet
```

The partition keys are the business year, business month and store ID. This directly supports store/month pruning.

## Landing and normalization

The ETL reads the mixed POS dialects, normalizes the column names, extracts the business date from the filename, deduplicates resend rows at `(bill_no, line_no)`, resolves product identity, calculates revenue in integer paise and writes Parquet.

## Evidence

- `proofs/A/A1_platform_containers.png`
- `proofs/A/A2_postgres_master_loaded.png`
- `proofs/A/A3_minio_bucket.png`
- `proofs/A/A4_duckdb_running.png`
- `proofs/A/A5_successful_etl_load.png`
- `proofs/A/A6_s01_october_pruning.png`

## Measured comparison

For S01 in October 2024:

| Layout | Potential/actual files read | Bytes |
|---|---:|---:|
| Flat raw folder | 4,457 source files | 68,706,877 |
| Partitioned final layout | 1 final Parquet file | 168,919 |

The DuckDB execution proof reports `Total Files Read: 1` for the S01 October query.

## Query

See `sql/task_a_s01_october.sql`.
