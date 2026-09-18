# Annapurna Stores — Retail Sales Data Platform

This repository contains the exam solution for the Annapurna Stores data-platform scenario.

## Problem

Annapurna Stores has 12 supermarkets. Each store writes a nightly sales export. The solution must make reporting reproducible, preserve historical prices, handle resend files safely, and stop the analyst from manually opening files.

## Architecture

```text
Nightly store exports (CSV / Parquet)
              |
              v
        Python ETL / normalization
              |
              v
      MinIO object store
      sales/business_year=YYYY/
        business_month=MM/
          store_id=Sxx/data.parquet
              |
              v
             DuckDB  <----> PostgreSQL
                           stores
                           products
                           product_categories
                           price_revisions
```

## Technology used

- Docker 29.8.0
- PostgreSQL 16
- MinIO Community Edition (`quay.io/minio/minio`)
- DuckDB CLI 1.5.5
- Python 3.14.7
- pandas, PyArrow, boto3, psycopg2-binary

## Key source-data rules

- Business date comes from the sales filename, not the transaction timestamp.
- Resends are handled at `(bill_no, line_no)` level.
- `SALE`, `RETURN`, `DISCOUNT`, and `VOID` affect revenue; `TAX` and `TENDER` do not.
- `product_code` is not unique; product identity uses `product_sk` plus validity dates.
- Historical prices come from `price_revisions` for the requested reporting date.

## Main measured results

- Source files: **4,457**
- Raw bytes: **68,706,877**
- Raw rows: **1,137,585**
- Final deduplicated rows: **1,120,924**
- Logical partitions: **144**
- S01 October source files: **31**
- S01 October raw bytes: **846,899**
- S01 October final Parquet files read: **1**
- S01 October final Parquet bytes: **168,919**
- October total revenue: **₹56,359,195.92**

## Idempotency proof

Three consecutive loads produced the same result:

| Run | Rows | SHA-256 checksum |
|---|---:|---|
| proof1 | 1,120,924 | `b3fd2afe6f718ad6064a9927f0c632ea07cd280682cb744f7587c1c40a00e853` |
| proof2 | 1,120,924 | `b3fd2afe6f718ad6064a9927f0c632ea07cd280682cb744f7587c1c40a00e853` |
| proof3 | 1,120,924 | `b3fd2afe6f718ad6064a9927f0c632ea07cd280682cb744f7587c1c40a00e853` |

## Reconciliation exceptions

- **March:** finance includes a ₹486,250 institutional order invoiced outside the till.
- **July:** S07 is missing exports for 9–11 July 2024.
- **December:** finance rounds each bill to the rupee.
- **October:** pipeline and finance both report ₹56,359,195.92.

## Repository layout

- `task_a/` — platform, landing and partitioning
- `task_b/` — idempotent loading proof
- `task_c/` — dashboard/star-schema design
- `task_d/` — historical pricing
- `task_e/` — cross-system query and execution evidence
- `task_f/` — reconciliation
- `sql/` — reusable SQL queries
- `scripts/` — ETL script and verification helpers
- `proofs/` — screenshots from the completed run
- `results/` — measured outputs
- `data_reference/` — source-data inventory

## Data handling

Raw sales data and `truth.json` are intentionally not committed. Review the instructor's data-sharing rules before publishing any instructor-provided data to a public repository.
