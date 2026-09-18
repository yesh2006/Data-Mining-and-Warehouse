# Task B — Make the load idempotent

## Objective

Running the loading process repeatedly must produce the same result as running it once.

## Design

The safe unit is the sales line key `(bill_no, line_no)`. Resend files are not treated as independent sales batches.

The loader:

1. Reads all source files in deterministic filename order.
2. Normalizes each source format.
3. Checks duplicate line keys for conflicting contents.
4. Keeps one canonical row per `(bill_no, line_no)`.
5. Writes deterministic, sorted Parquet partitions.
6. Computes a deterministic SHA-256 checksum.

## Proof

| Run | Rows after dedup | Checksum |
|---|---:|---|
| proof1 | 1,120,924 | `b3fd2afe6f718ad6064a9927f0c632ea07cd280682cb744f7587c1c40a00e853` |
| proof2 | 1,120,924 | `b3fd2afe6f718ad6064a9927f0c632ea07cd280682cb744f7587c1c40a00e853` |
| proof3 | 1,120,924 | `b3fd2afe6f718ad6064a9927f0c632ea07cd280682cb744f7587c1c40a00e853` |

## Evidence

`proofs/B/B1_idempotency_three_runs.png`

## Commands

```powershell
py .\scripts\load_sales.py proof1
py .\scripts\load_sales.py proof2
py .\scripts\load_sales.py proof3
```

Then compare `staging/manifests/load_runs.csv` with the verification command documented in `sql/task_b_verify.ps1`.
