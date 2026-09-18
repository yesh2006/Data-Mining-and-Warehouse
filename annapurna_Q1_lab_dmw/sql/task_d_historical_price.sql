-- Task D: same temporal price query; change only reporting_date.
-- Product: P100019 / product_sk 1003 / Sunfeast Cookies 150g

WITH params AS (
    SELECT DATE '2024-03-15' AS reporting_date
)
SELECT
    x.reporting_date,
    p.product_code,
    p.product_name,
    pr.selling_price,
    pr.mrp,
    pr.effective_from,
    pr.effective_to
FROM pg.public.products p
JOIN pg.public.price_revisions pr
    ON p.product_sk = pr.product_sk
CROSS JOIN params x
WHERE p.product_sk = 1003
  AND x.reporting_date >= p.valid_from
  AND x.reporting_date <= p.valid_to
  AND x.reporting_date >= pr.effective_from
  AND x.reporting_date < pr.effective_to;

-- For the second demonstration, change only the parameter above to:
-- DATE '2024-10-15'
