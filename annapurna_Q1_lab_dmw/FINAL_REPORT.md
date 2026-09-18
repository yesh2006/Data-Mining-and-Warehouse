# Annapurna Stores — Exam Solution Summary

## Architecture

**MinIO** stores the normalized sales Parquet files. **PostgreSQL** stores operational master data. **DuckDB** is the analytical query engine and federates the two systems directly.

Sales are organized as Hive-style partitions:

```text
sales/business_year=2024/business_month=MM/store_id=Sxx/data.parquet
```

## A — Platform and landing

- 4,457 source files
- 68,706,877 raw bytes
- 1,137,585 raw rows
- 144 final partitions
- 15,088,945 final Parquet bytes
- S01 + October: 31 source files / 846,899 raw bytes / 1 final Parquet object / 168,919 Parquet bytes
- S01 + October `EXPLAIN ANALYZE`: 1 file read

## B — Idempotency

Final deduplicated rows: **1,120,924**.

```text
proof1  1,120,924  b3fd2afe6f718ad6064a9927f0c632ea07cd280682cb744f7587c1c40a00e853
proof2  1,120,924  b3fd2afe6f718ad6064a9927f0c632ea07cd280682cb744f7587c1c40a00e853
proof3  1,120,924  b3fd2afe6f718ad6064a9927f0c632ea07cd280682cb744f7587c1c40a00e853
```

## C — Dashboard model

PostgreSQL dimensions:

- `dashboard.dim_store` — 12 rows
- `dashboard.dim_category` — 14 rows
- `dashboard.dim_product` — 1,224 rows
- `dashboard.dim_date` — 366 rows

Sales remain in partitioned Parquet and are joined by keys. This avoids repeating store/address/category attributes on every sales line.

Revenue handling:

- revenue-affecting: `SALE`, `RETURN`, `DISCOUNT`, `VOID`
- excluded from revenue: `TAX`, `TENDER`

`product_sk` is used because `product_code` is not unique across product validity periods.

October revenue: **₹56,359,195.92**.

## D — Historical pricing

Demonstration product: `P100019`, Sunfeast Cookies 150g, `product_sk=1003`.

The same temporal query was run with two reporting dates:

- 2024-03-15 — price revision ending 2024-04-13
- 2024-10-15 — price revision starting 2024-09-26

The reporting date is the only parameter changed.

## E — Cross-system query

DuckDB reads sales with `READ_PARQUET` from MinIO and reads the dashboard dimensions from attached PostgreSQL tables. The physical plan shows `HASH_JOIN`, `HASH_GROUP_BY` and `ORDER_BY` in DuckDB. The optimized October path reports **12 files read**, one per store.

## F — Reconciliation

| Month | Difference | Explanation |
|---|---:|---|
| 2024-03 | +₹486,250.00 | Finance includes an institutional order invoiced outside the till |
| 2024-07 | +₹232,131.70 | S07 is missing 9–11 July exports |
| 2024-12 | −₹50.48 | Finance rounds each bill to the rupee |

All other months match. October matches at **₹56,359,195.92**.

## Finance interpretation

The pipeline should remain a reproducible **till-sales** measure. The three exceptions are reconciliation items to document with finance rather than forcing the pipeline to match by changing the calculation.
