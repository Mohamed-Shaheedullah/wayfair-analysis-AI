# Cleaning log

Audit and implementation date: 2026-11-08. Stage: cleaning implemented and validated.

Source CSVs remain unchanged. Cleaned copies are in data/cleaned/. The table below preserves the initial review; the implementation record that follows supersedes its proposed/open cleaning statuses. Source hashes and original diagnostics are in data_profile.json; cleaning_validation.json records the implemented output counts, hashes and checks.

| ID | Observation | Proposed treatment / assumption | Status |
|---|---|---|---|
| C001 | orders.csv contains 9,245 rows but 9,207 unique order IDs; 38 excess records are exact duplicates. There are no conflicting records after exact deduplication. | Keep one exact record per order in the future prepared order table. This prevents a raw join from increasing item rows from 15,608 to 15,668. | Proposed; no source changes. Exact duplicates collapsed in memory only for missing-price diagnostics. |
| C002 | products.csv has 24 category labels with case and whitespace variants. | Trim surrounding whitespace and map case variants to title case; the profile lists every proposed mapping and affected product count. | Proposed |
| C003 | 199 of 15,608 item rows (1.275%) lack unit_price, covering 259 units; 176 affected rows have completed status. | Retain and flag missing prices. Exclude unknown amounts only from explicitly labelled known-price revenue calculations, with coverage disclosed. Investigate sensitivity before adopting any estimation rule. Do not exclude entire orders automatically. | Open decision; no imputation or exclusions |
| C004 | All 90 products have multiple observed transaction prices; 8,273 known-price item rows differ from list price. | Neither list price nor a single product price establishes the missing historical selling price. Product price counts/ranges and source row references are saved in data/profile/missing_price_investigation.csv. | Evidence recorded |
| C005 | 7,834 raw order rows have blank discount_code. | Interpret as no code recorded, not evidence of zero monetary discount. Use discount_amount as the recorded total line discount, following the project README. | Proposed assumption |
| C006 | Dates parse successfully and span 2024-01-01 to 2025-12-31. CSV timestamps have no timezone suffix. | Apply the project's documented UTC interpretation when preparing timestamps. Preserve source strings. | Proposed assumption |
| C007 | All item order/product IDs match; all orders and products are used. No duplicate item rows or repeated order/product pairs. | Validate many-to-one joins after handling the duplicate order records. Keep all item records. Treat IDs as text. | Audit passed |
| C008 | Quantity is integral and 1–4. Known prices are positive. Discounts and shipping are nonnegative; no known line discount exceeds quantity times price. Product costs do not exceed list prices. | Retain numeric observations. Quantiles in the JSON are descriptive; unusual values are not automatically errors. Missing-price rows cannot pass the discount-versus-gross check until price is known. | Audit passed for available values |
| C009 | completed, returned and canceled are distinct recorded statuses. | Decide the sales/revenue eligibility rule before calculating business metrics; retain all statuses in prepared data. | Open metric definition |

Record-level candidate exports are under data/profile/, excluded from Git by the existing data/ rule. Source CSV row references use header row 1.

## Applied cleaning and validation

- C001 applied: excluded 38 exact duplicate order records from the cleaned orders copy, retaining the first source occurrence. 9,245 source rows became 9,207 unique orders. No conflicting order records were found.
- C002 applied: changed category labels on 22 product rows. Trimming whitespace and using the reviewed case mapping reduced 24 labels to 8 categories; all 90 products remain.
- C003 applied as agreed: retained all 199 blank unit prices and added the Boolean unit_price_missing column. No prices were estimated, no item rows were excluded, and no whole orders were excluded because of missing prices.
- C004 retained as evidence: historical prices vary. No catalogue-price replacement was used.
- C005 adopted: blank discount codes remain blank and mean no code recorded. No monetary discount values changed.
- C006 applied: parsed dates as UTC under the documented source assumption and exported ISO 8601 timestamps with a Z suffix. Every timestamp formatting change is logged.
- C007 validated: IDs are handled as strings in the cleaning process. CSV has no embedded type schema, so downstream readers must explicitly load ID columns as strings. Both many-to-one joins succeed and retain exactly 15,608 item rows.
- C008 validated: item source values and product numeric values are unchanged. Order values are unchanged except for timestamp formatting and the recorded duplicate exclusions. Numeric values are checked in memory and retain their original decimal spelling in CSV.
- C009 remains a later metric-definition decision. All three statuses are retained; cleaning does not calculate revenue or apply sales eligibility exclusions.

The row-level file data/cleaned/cleaning_changes.csv records each excluded order, changed category, timestamp conversion and missing-price flag, with the original source CSV row, old/new values and rule ID. Original source hashes were verified after writing. Exported CSVs were reloaded and compared with the prepared tables; allowed-change checks and numeric/key validation passed. Numeric totals and output hashes are in reports/cleaning_validation.json. Blank prices remain unknown rather than becoming zero.

Reproduce cleaning with `.\.venv\Scripts\python.exe scripts\clean_data.py`. This regenerates the three cleaned CSVs, row-level change log and validation manifest from the originals. The original profiling reports remain a record of the pre-cleaning data.

## Metric decisions agreed 2026-11-12

C009 resolved for the initial metrics: completed orders contribute merchandise revenue, units and shipping income; canceled and returned orders are excluded from those metrics. Returned status is assumed to mean a full merchandise return/refund. Cancellation and return rates each use all distinct orders placed as the denominator. Shipping charged to customers is separate income, counted once per completed order.

C003 remains a known data limitation: no prices are estimated. Merchandise revenue uses known-price completed lines with coverage disclosed. AOV uses only completed orders with every line priced, with matching revenue and order populations. Completed order counts, units and shipping retain missing-price orders. See `reports/metrics.md` for full definitions and results and `scripts/calculate_metrics.py` for reproduction. No further cleaning changes were made.

Rerun the audit from the project root with `.\.venv\Scripts\python.exe scripts\profile_data.py`. Outputs are regenerated from the current source files. This log documents this audit and should be extended when cleaning is implemented.
