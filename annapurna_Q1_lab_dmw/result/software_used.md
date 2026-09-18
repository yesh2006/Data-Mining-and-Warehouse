# Software and services used

## Runtime / infrastructure

- Docker 29.8.0
- PostgreSQL 16 container
- MinIO Community Edition container (`quay.io/minio/minio`)
- DuckDB CLI 1.5.5
- Python 3.14.7

## Python packages

- pandas
- pyarrow
- boto3
- psycopg2-binary

## DuckDB extensions

- `httpfs` — S3/MinIO access
- `postgres` — direct PostgreSQL attachment

## Storage format / layout

- Final analytical format: Parquet
- Compression: Zstandard
- Partition keys: `business_year`, `business_month`, `store_id`
