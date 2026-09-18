# Task E — Query across the two systems

## Objective

Run one query that combines sales in MinIO with store/product/category data in PostgreSQL without first copying either side into the other.

## Federated query

DuckDB reads:

- sales via `READ_PARQUET` from MinIO
- dimension tables via the attached PostgreSQL database

DuckDB then performs the join, grouping and ordering.

## Engine evidence

The execution plan shows:

- `READ_PARQUET` for the MinIO sales data
- PostgreSQL table scans for `dim_store`, `dim_product`, `dim_category` and `dim_date`
- `HASH_JOIN` operators in DuckDB
- `HASH_GROUP_BY` and `ORDER_BY` in DuckDB

For the optimized October path, `Total Files Read: 12` because there is one October partition per store.

## Evidence

- `proofs/E/E1_cross_system_plan_part1.png`
- `proofs/E/E2_cross_system_plan_part2.png`
- `proofs/E/E3_cross_system_plan_part3.png`
- `proofs/E/E4_cross_system_plan_part4.png`

## Query

See `sql/task_e_cross_system.sql`.
