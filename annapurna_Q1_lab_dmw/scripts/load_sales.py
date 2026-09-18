from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
import pandas as pd
import psycopg2
from botocore.client import Config

# ----------------------------
# Configuration
# ----------------------------
BASE = Path(__file__).resolve().parents[1]
RAW_DIR = BASE / "raw"
STAGING_DIR = BASE / "staging"
PARQUET_DIR = STAGING_DIR / "parquet"
MANIFEST_DIR = STAGING_DIR / "manifests"

POSTGRES = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "annapurna"),
    "user": os.getenv("POSTGRES_USER", "annapurna"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}

MINIO = {
    "endpoint": os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
    "access_key": os.getenv("MINIO_ACCESS_KEY", ""),
    "secret_key": os.getenv("MINIO_SECRET_KEY", ""),
    "bucket": os.getenv("MINIO_BUCKET", "annapurna"),
    "prefix": "sales",
}

REV_TYPES = {"SALE", "RETURN", "DISCOUNT", "VOID"}
ITEM_TYPES = {"SALE", "RETURN", "VOID"}
FILE_RE = re.compile(
    r"^SALES_(S\d{2})_(\d{8})(?:__R\d+)?\.(csv|parquet)$",
    re.IGNORECASE,
)

COLUMN_MAP = {
    "bill_no": "bill_no",
    "line_no": "line_no",
    "product_code": "product_code",
    "item_code": "product_code",
    "qty": "qty",
    "quantity": "qty",
    "unit_price": "unit_price",
    "rate": "unit_price",
    "line_type": "line_type",
    "type": "line_type",
    "ts": "txn_ts_raw",
    "txn_time": "txn_ts_raw",
}


def die(msg: str) -> None:
    raise RuntimeError(msg)


def parse_filename(path: Path) -> tuple[str, str]:
    m = FILE_RE.match(path.name)
    if not m:
        die(f"Unexpected sales filename: {path.name}")
    store_id, yyyymmdd, _ext = m.groups()
    business_date = f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}"
    return store_id, business_date


def normalize_frame(df: pd.DataFrame, store_id: str, business_date: str, source_file: str) -> pd.DataFrame:
    # Normalize headers and tolerate a UTF-8 BOM.
    df.columns = [str(c).replace("\ufeff", "").strip().lower() for c in df.columns]
    df = df.rename(columns=COLUMN_MAP)

    required = {"bill_no", "line_no", "product_code", "qty", "unit_price", "line_type", "txn_ts_raw"}
    missing = sorted(required - set(df.columns))
    if missing:
        die(f"Missing columns in {source_file}: {missing}")

    df = df[["bill_no", "line_no", "product_code", "qty", "unit_price", "line_type", "txn_ts_raw"]].copy()

    df["bill_no"] = df["bill_no"].astype("string").str.strip()
    df["product_code"] = df["product_code"].astype("string").str.strip()
    df["line_type"] = df["line_type"].astype("string").str.strip().str.upper()
    df["line_no"] = pd.to_numeric(df["line_no"], errors="raise").astype("int64")
    df["qty"] = pd.to_numeric(df["qty"], errors="raise").astype("int64")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="raise").astype("float64")

    if df[["bill_no", "product_code", "line_type"]].isna().any().any():
        die(f"Null key/header values in {source_file}")

    # Business date always comes from the filename. Timestamp is retained separately.
    df["store_id"] = store_id
    df["business_date"] = business_date
    df["source_file"] = source_file

    # S10-S12 export epoch seconds in UTC; S01-S09 carry local India time.
    if store_id in {"S10", "S11", "S12"}:
        df["txn_ts"] = pd.to_datetime(df["txn_ts_raw"], unit="s", utc=True, errors="raise")
    elif store_id in {"S06", "S07", "S08", "S09"}:
        local = pd.to_datetime(df["txn_ts_raw"], format="%d-%m-%Y %H:%M:%S", errors="raise")
        df["txn_ts"] = local.dt.tz_localize("Asia/Kolkata").dt.tz_convert("UTC")
    else:
        local = pd.to_datetime(df["txn_ts_raw"], format="ISO8601", errors="raise")
        df["txn_ts"] = local.dt.tz_localize("Asia/Kolkata").dt.tz_convert("UTC")

    return df.drop(columns=["txn_ts_raw"])


def read_sales_file(path: Path, store_id: str, business_date: str) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext == ".csv":
        if store_id in {"S06", "S07", "S08", "S09"}:
            df = pd.read_csv(path, sep=";", encoding="utf-8-sig", low_memory=False)
        else:
            df = pd.read_csv(path, sep=",", encoding="utf-8-sig", low_memory=False)
    elif ext == ".parquet":
        df = pd.read_parquet(path)
    else:
        die(f"Unsupported extension: {path}")
    return normalize_frame(df, store_id, business_date, path.name)


def load_product_master() -> pd.DataFrame:
    conn = psycopg2.connect(**POSTGRES)
    try:
        sql = """
            SELECT product_sk, product_code, category_id,
                   valid_from::text AS valid_from,
                   valid_to::text AS valid_to
            FROM products
            ORDER BY product_code, valid_from, product_sk
        """
        return pd.read_sql_query(sql, conn)
    finally:
        conn.close()


def resolve_products(df: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    merged = df.merge(products, on="product_code", how="left", suffixes=("", "_master"), sort=False)
    in_range = (
        merged["valid_from"].notna()
        & (merged["business_date"] >= merged["valid_from"])
        & (merged["business_date"] <= merged["valid_to"])
    )
    matched = merged.loc[in_range].copy()

    key_cols = ["bill_no", "line_no"]
    counts = matched.groupby(key_cols, dropna=False).size()
    bad_multiple = counts[counts != 1]
    if not bad_multiple.empty:
        die(
            "Product validity join is not one-to-one for item lines. "
            f"Example keys: {bad_multiple.head(5).to_dict()}"
        )

    # SALE and RETURN rows must resolve to a product.
    # VOID rows can reverse a DISCOUNT line (product_code DISC), which
    # is not a real product. A VOID of a real item must resolve normally.
    requires_product = merged["line_type"].isin({"SALE", "RETURN"}) | (
        (merged["line_type"] == "VOID")
        & (~merged["product_code"].eq("DISC"))
    )
    item_candidates = merged.loc[
        requires_product,
        ["bill_no", "line_no", "product_code", "business_date"],
    ]
    matched_item_keys = set(zip(matched["bill_no"], matched["line_no"]))
    missing_items = [
        (b, l, p, d)
        for b, l, p, d in item_candidates.itertuples(index=False, name=None)
        if (b, l) not in matched_item_keys
    ]
    if missing_items:
        die(f"Unresolved item products; first examples: {missing_items[:10]}")

    # Merge the matched master values back using the natural line key.
    resolved = matched[["bill_no", "line_no", "product_sk", "category_id"]].copy()
    df = df.merge(resolved, on=key_cols, how="left", validate="one_to_one")
    df["product_sk"] = df["product_sk"].astype("Int64")
    return df


def deduplicate_lines(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    key = ["bill_no", "line_no"]
    dup_mask = df.duplicated(key, keep=False)
    duplicate_rows = df.loc[dup_mask].copy()
    duplicate_input_rows = len(duplicate_rows)

    if not duplicate_rows.empty:
        compare_cols = ["product_code", "qty", "unit_price", "line_type", "txn_ts", "store_id", "business_date"]
        conflict_counts = duplicate_rows.groupby(key, dropna=False)[compare_cols].nunique(dropna=False)
        conflicts = conflict_counts[(conflict_counts > 1).any(axis=1)]
        if not conflicts.empty:
            die(
                "Conflicting resend rows found for the same (bill_no,line_no). "
                f"First examples: {list(conflicts.index[:10])}"
            )

    # Deterministic source ordering makes the surviving identical duplicate deterministic.
    df = df.sort_values(["bill_no", "line_no", "source_file"]).drop_duplicates(key, keep="first")
    return df.reset_index(drop=True), duplicate_input_rows


def add_revenue(df: pd.DataFrame) -> pd.DataFrame:
    unit_paise = (df["unit_price"] * 100).round().astype("int64")
    df["revenue_paise"] = 0
    mask = df["line_type"].isin(REV_TYPES)
    df.loc[mask, "revenue_paise"] = df.loc[mask, "qty"] * unit_paise.loc[mask]
    return df


def canonical_partition_hash(df: pd.DataFrame) -> str:
    cols = [
        "store_id", "business_date", "bill_no", "line_no", "product_code",
        "qty", "unit_price", "line_type", "product_sk", "category_id", "revenue_paise"
    ]
    s = df.sort_values(["bill_no", "line_no"])[cols].copy()
    lines = []
    for row in s.itertuples(index=False, name=None):
        store, bdate, bill, line, prod, qty, price, typ, psk, cat, rev = row
        psk_text = "" if pd.isna(psk) else str(int(psk))
        cat_text = "" if pd.isna(cat) else str(cat)
        lines.append(
            f"{store}|{bdate}|{bill}|{int(line)}|{prod}|{int(qty)}|{price:.2f}|{typ}|{psk_text}|{cat_text}|{int(rev)}\n"
        )
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def get_s3():
    return boto3.client(
        "s3",
        endpoint_url=MINIO["endpoint"],
        aws_access_key_id=MINIO["access_key"],
        aws_secret_access_key=MINIO["secret_key"],
        region_name="us-east-1",
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket(s3) -> None:
    try:
        s3.head_bucket(Bucket=MINIO["bucket"])
    except Exception:
        s3.create_bucket(Bucket=MINIO["bucket"])


def append_run_log(record: dict) -> None:
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    path = MANIFEST_DIR / "load_runs.csv"
    row = pd.DataFrame([record])
    row.to_csv(path, mode="a", header=not path.exists(), index=False)


def main() -> None:
    run_label = sys.argv[1] if len(sys.argv) > 1 else datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    if not RAW_DIR.exists():
        die(f"Raw folder not found: {RAW_DIR}")

    files = sorted([p for p in RAW_DIR.rglob("*") if p.is_file() and p.suffix.lower() in {".csv", ".parquet"}])
    print(f"Found source files: {len(files)}")
    if not files:
        die("No CSV/Parquet sales files found")

    groups: dict[tuple[str, str, str], list[Path]] = {}
    total_raw_bytes = 0
    for p in files:
        store_id, business_date = parse_filename(p)
        key = (business_date[:4], business_date[:7][5:7], store_id)
        groups.setdefault(key, []).append(p)
        total_raw_bytes += p.stat().st_size

    print(f"Total raw bytes: {total_raw_bytes}")
    products = load_product_master()
    print(f"Loaded product master rows: {len(products)}")

    s3 = get_s3()
    ensure_bucket(s3)
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)

    manifest = []
    total_rows = 0
    total_output_bytes = 0
    total_duplicate_input_rows = 0

    for (year, month, store_id), paths in sorted(groups.items()):
        frames = []
        source_bytes = 0
        for path in sorted(paths, key=lambda x: x.name):
            _, business_date = parse_filename(path)
            frames.append(read_sales_file(path, store_id, business_date))
            source_bytes += path.stat().st_size

        df = pd.concat(frames, ignore_index=True)
        df, duplicate_input_rows = deduplicate_lines(df)
        total_duplicate_input_rows += duplicate_input_rows
        df = resolve_products(df, products)
        df = add_revenue(df)

        # Stable ordering makes output and evidence repeatable.
        df = df.sort_values(["bill_no", "line_no"]).reset_index(drop=True)
        out_dir = PARQUET_DIR / f"business_year={year}" / f"business_month={month}" / f"store_id={store_id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "data.parquet"
        df.to_parquet(out_path, engine="pyarrow", compression="zstd", index=False)

        object_key = f"{MINIO['prefix']}/business_year={year}/business_month={month}/store_id={store_id}/data.parquet"
        s3.upload_file(str(out_path), MINIO["bucket"], object_key)

        output_bytes = out_path.stat().st_size
        partition_hash = canonical_partition_hash(df)
        row_count = len(df)
        total_rows += row_count
        total_output_bytes += output_bytes

        rec = {
            "year": int(year),
            "month": int(month),
            "store_id": store_id,
            "source_file_count": len(paths),
            "source_bytes": source_bytes,
            "duplicate_input_rows": duplicate_input_rows,
            "output_row_count": row_count,
            "output_bytes": output_bytes,
            "object_key": object_key,
            "partition_checksum": partition_hash,
        }
        manifest.append(rec)

    overall = hashlib.sha256()
    for rec in sorted(manifest, key=lambda r: r["object_key"]):
        overall.update(rec["object_key"].encode("utf-8"))
        overall.update(b"=")
        overall.update(rec["partition_checksum"].encode("ascii"))
        overall.update(b"\n")
    overall_checksum = overall.hexdigest()

    manifest_path = MANIFEST_DIR / "load_manifest.json"
    manifest_path.write_text(json.dumps({
        "run_label": run_label,
        "source_file_count": len(files),
        "source_bytes": total_raw_bytes,
        "partitions_written": len(manifest),
        "deduplicated_row_count": total_rows,
        "duplicate_input_rows_removed": total_duplicate_input_rows,
        "output_bytes": total_output_bytes,
        "overall_checksum": overall_checksum,
        "partitions": manifest,
    }, indent=2), encoding="utf-8")

    append_run_log({
        "run_label": run_label,
        "run_time_utc": datetime.now(timezone.utc).isoformat(),
        "source_files": len(files),
        "raw_bytes": total_raw_bytes,
        "rows": total_rows,
        "partitions": len(manifest),
        "output_bytes": total_output_bytes,
        "checksum": overall_checksum,
    })

    print("\n=== LOAD COMPLETE ===")
    print(f"Run label              : {run_label}")
    print(f"Source files           : {len(files)}")
    print(f"Raw bytes              : {total_raw_bytes}")
    print(f"Rows after dedup       : {total_rows}")
    print(f"Duplicate input rows   : {total_duplicate_input_rows}")
    print(f"Partitions written     : {len(manifest)}")
    print(f"Output bytes           : {total_output_bytes}")
    print(f"Overall checksum       : {overall_checksum}")

    oct_rows = [r for r in manifest if r["year"] == 2024 and r["month"] == 10 and r["store_id"] == "S01"]
    if oct_rows:
        r = oct_rows[0]
        print("\n=== S01 / OCTOBER 2024 EVIDENCE ===")
        print(f"Source files for S01 October : {r['source_file_count']}")
        print(f"Raw source bytes             : {r['source_bytes']}")
        print(f"Final Parquet files scanned  : 1")
        print(f"Final Parquet bytes          : {r['output_bytes']}")
        print(f"Final rows                   : {r['output_row_count']}")
        print(f"MinIO object                 : {r['object_key']}")


if __name__ == "__main__":
    main()
