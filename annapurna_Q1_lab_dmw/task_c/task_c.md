# Task C — Design the dashboard tables

## Objective

Support fast slicing of revenue by store, product category, day of week and month without repeating store/address/category attributes on every sales line.

## Model

```text
                     dim_store
                         |
                         |
dim_category <- dim_product <- fact_sales -> dim_date
```

### Dimensions

- `dim_store` — 12 rows
- `dim_category` — 14 rows
- `dim_product` — 1,224 rows
- `dim_date` — 366 rows for calendar year 2024

### Fact

The high-volume sales fact remains as partitioned Parquet in MinIO. It contains keys/measures rather than repeated descriptive master data:

- `store_id`
- `business_date`
- `bill_no`
- `line_no`
- `product_sk`
- `category_id`
- `qty`
- `unit_price`
- `line_type`
- `revenue_paise`

## Source issues handled

1. Not every line is a sale. `SALE`, `RETURN`, `DISCOUNT`, and `VOID` affect revenue; `TAX` and `TENDER` do not.
2. `product_code` is not unique. Product identity uses `product_sk` and validity dates.

## Evidence

- `proofs/C/C1_dashboard_dimensions.png`
- `proofs/C/C2_date_dimension.png`
- `proofs/C/C3_dashboard_query.png`
- `proofs/C/C4_october_revenue.png`

## October check

The dashboard query returns October revenue of **₹56,359,195.92**.

See `sql/task_c_dashboard.sql`.
