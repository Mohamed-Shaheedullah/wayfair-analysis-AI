# Initial metrics: 2024–2025

## Agreed definitions

- Merchandise revenue is quantity × historical unit_price − discount_amount, summed over completed orders. The source dictionary confirms discount_amount is a line total. USD throughout; calculations use integer cents and AOV is rounded half up to two decimal places.
- Canceled and returned orders contribute no merchandise revenue, completed units or completed shipping income. Returned status is treated as a full merchandise return/refund; partial refunds and refund dates are unavailable. No additional refund deduction is made after exclusion.
- Revenue is grouped by order_date in UTC and reflects final recorded status, not revenue/refunds as recorded at each historical month end.
- Known-price merchandise revenue includes only priced lines from completed orders, including priced lines in otherwise incompletely priced orders. Unknown line revenue remains missing, never zero. Its recorded discount is not deducted separately from other lines. No historical prices are estimated.
- Completed orders and units sold include completed orders/lines with missing prices. Coverage measures the fraction of completed lines with prices and the fraction of completed orders with every line priced; neither measures the fraction of dollar revenue captured.
- Average order value (AOV) = revenue of fully priced completed orders ÷ number of fully priced completed orders. Both numerator and denominator exclude any order with a missing line price. This subset may differ from the full population.
- Shipping income is shipping_fee summed once per completed order, independently of price completeness. It is customer income, not delivery expense, and is excluded from merchandise revenue. Shipping refunds/costs are unavailable.
- Cancellation rate = canceled orders ÷ all distinct orders placed. Return rate = returned orders ÷ all distinct orders placed. These rates describe final statuses by order placement date.

## Results

| Metric | 2024–2025 | 2024 | 2025 |
|---|---:|---:|---:|
| All orders | 9,207 | 4,212 | 4,995 |
| Completed orders | 8,456 | 3,867 | 4,589 |
| Canceled orders | 344 | 160 | 184 |
| Returned orders | 407 | 185 | 222 |
| Cancellation rate | 3.74% | 3.80% | 3.68% |
| Return rate | 4.42% | 4.39% | 4.44% |
| Completed units sold | 17,775 | 8,215 | 9,560 |
| Known-price merchandise revenue (USD) | $1,858,121.00 | $841,136.33 | $1,016,984.67 |
| Completed shipping income (USD) | $13,135.50 | $6,067.35 | $7,068.15 |
| AOV: fully priced completed orders (USD) | $221.36 | $219.01 | $223.36 |
| Fully priced completed-order revenue (USD) | $1,833,343.28 | $831,807.35 | $1,001,535.93 |
| Completed orders with all prices | 8,282 | 3,798 | 4,484 |
| Completed orders with missing prices | 174 | 69 | 105 |
| Completed-order price coverage | 97.94% | 98.22% | 97.71% |
| Completed item lines | 14,283 | 6,603 | 7,680 |
| Completed missing-price lines | 176 | 71 | 105 |
| Completed missing-price units | 230 | 93 | 137 |
| Completed-line price coverage | 98.77% | 98.92% | 98.63% |

## Reproduction and validation

Run `.\.venv\Scripts\python.exe scripts\calculate_metrics.py` from the project root.
Uses only `data/cleaned/` inputs verified against the cleaning manifest. Sources and cleaned inputs are unchanged.
Detailed order calculations and annual exports are under `data/metrics/` (excluded from Git).
Machine-readable totals, input hashes and validation results are in `reports/metrics_results.json`.
Validation passed for cleaned-file hashes, joins, line-to-order revenue, status counts, and annual-to-overall counts and money. AOV is recomputed from its matching numerator and denominator for each period, not averaged across years.

These are initial metric calculations. Monthly comparisons, category/product analysis, charts and final recommendations remain later steps.
