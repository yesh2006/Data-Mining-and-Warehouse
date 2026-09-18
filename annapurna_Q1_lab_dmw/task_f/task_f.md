# Task F — Reconcile against finance

## Objective

Compare the pipeline monthly revenue with `finance_monthly.csv` and classify every difference.

## Result

| Month | Pipeline | Finance | Difference | Cause |
|---|---:|---:|---:|---|
| 2024-03 | ₹41,971,649.09 | ₹42,457,899.09 | +₹486,250.00 | Finance scope includes external institutional invoice |
| 2024-07 | ₹40,295,160.11 | ₹40,527,291.81 | +₹232,131.70 | S07 source-data gap |
| 2024-12 | ₹50,745,259.48 | ₹50,745,209.00 | −₹50.48 | Finance bill-level rounding |

All other months match exactly.

October matches:

**₹56,359,195.92**

## Classification

- March — definition/scope difference, not pipeline bug.
- July — missing source data, not pipeline bug.
- December — rounding/definition difference, not pipeline bug.

## Evidence

- `proofs/F/F1_monthly_reconciliation.png`
- `proofs/F/F2_months_that_differ.png`
- `proofs/F/F3_october_final.png`
- `proofs/F/F4_finance_csv_schema.png`

## Query

See `sql/task_f_reconcile.sql`.
