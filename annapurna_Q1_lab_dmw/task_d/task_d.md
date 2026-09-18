# Task D — Make March use March prices

## Objective

A historical report must use the price revision that was valid during the requested reporting period.

## Demonstration product

- Product: **Sunfeast Cookies 150g**
- Product code: `P100019`
- Surrogate key: `1003`

## Same query, different reporting period

For `2024-03-15`, the applicable revision is `2022-01-01` through `2024-04-13`.

For `2024-10-15`, the applicable revision is `2024-09-26` through `9999-12-31`.

Only the reporting date is changed; the temporal join logic remains the same.

## Evidence

- `proofs/D/D2_march_price_query.png`
- `proofs/D/D1_price_period_comparison.png`

## Query

See `sql/task_d_historical_price.sql`.
