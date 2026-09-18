# Measured platform evidence

- Source files: 4,457
- Raw bytes: 68,706,877
- Raw rows: 1,137,585
- Deduplicated rows: 1,120,924
- Logical partitions: 144
- Final Parquet bytes: 15,088,945

## S01 / October 2024

- Source files: 31
- Raw bytes: 846,899
- Final Parquet files read: 1
- Final Parquet bytes: 168,919
- Final rows: 13,516
- October revenue for all stores: ₹56,359,195.92

## Partition pruning

DuckDB `EXPLAIN ANALYZE` for S01 + October reports:

- `Function: READ_PARQUET`
- `Total Files Read: 1`
- File path contains `business_year=2024/business_month=10/store_id=S01/data.parquet`

The optimized federated October query reports `Total Files Read: 12` because it reads one October object per store.
