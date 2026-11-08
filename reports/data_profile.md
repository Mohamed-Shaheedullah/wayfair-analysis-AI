# CSV data profile

Scope: orders, order_items and products. Customer data is outside the project scope.
All checks are observational. No source values have been changed or records excluded.
Blank means empty or whitespace-only. Literal null markers are reported separately. IDs remain text.

## orders.csv

9,245 rows; 7 columns; 38 excess exact duplicate rows.
SHA-256: `ee812cda782cb10d25b5db00a86ba46167105341fec0caf288cc1771b3f2038a`

| Column | Inferred type | Blank | Distinct nonblank | Range / values |
|---|---|---:|---:|---|
| order_id | text identifier | 0 | 9207 | High cardinality; see JSON profile |
| customer_id | text identifier | 0 | 2106 | High cardinality; see JSON profile |
| order_date | object | 0 | 9206 | 2024-01-01 09:24:45 to 2025-12-31 23:23:29; invalid=0 |
| status | object | 0 | 3 | completed (8490), returned (409), canceled (346) |
| payment_method | object | 0 | 4 | credit_card (5332), paypal (1959), apple_pay (1422), gift_card (532) |
| discount_code | object | 7834 | 3 | HOLIDAY20 (782), WELCOME10 (391), SPRING15 (238) |
| shipping_fee | float64 | 0 | 2 | 0 to 6.95; negative=0; zero=7190 |

Malformed row widths: 0; duplicate headers: 0.

## order_items.csv

15,608 rows; 5 columns; 0 excess exact duplicate rows.
SHA-256: `b61ea33611ef4a13797d23c7d2ec9c22ada0ca22997a2227cbda31f4f156b2ca`

| Column | Inferred type | Blank | Distinct nonblank | Range / values |
|---|---|---:|---:|---|
| order_id | text identifier | 0 | 9207 | High cardinality; see JSON profile |
| product_id | text identifier | 0 | 90 | High cardinality; see JSON profile |
| quantity | int64 | 0 | 4 | 1 to 4; negative=0; zero=0 |
| unit_price | float64 | 199 | 158 | 7.99 to 812.69; negative=0; zero=0 |
| discount_amount | float64 | 0 | 537 | 0 to 196.56; negative=0; zero=13230 |

Malformed row widths: 0; duplicate headers: 0.

## products.csv

90 rows; 5 columns; 0 excess exact duplicate rows.
SHA-256: `821eee7cd8ad85a8c827066f3bdee44d8d370f0fe7caffc6b8dd555fd93d6689`

| Column | Inferred type | Blank | Distinct nonblank | Range / values |
|---|---|---:|---:|---|
| product_id | text identifier | 0 | 90 | High cardinality; see JSON profile |
| product_name | object | 0 | 90 | High cardinality; see JSON profile |
| category | object | 0 | 24 | High cardinality; see JSON profile |
| list_price | float64 | 0 | 80 | 7.99 to 773.99; negative=0; zero=0 |
| unit_cost | float64 | 0 | 90 | 4.76 to 445.47; negative=0; zero=0 |

Malformed row widths: 0; duplicate headers: 0.

## Identifier and join checks

```json
{
  "orders_to_items": {
    "parent_duplicate_key_excess": 38,
    "parent_blank_keys": 0,
    "child_blank_keys": 0,
    "unmatched_child_rows": 0,
    "unmatched_child_ids": [],
    "unused_parent_rows": 0,
    "unused_parent_ids": [],
    "child_rows_before": 15608,
    "left_join_rows_after": 15668
  },
  "products_to_items": {
    "parent_duplicate_key_excess": 0,
    "parent_blank_keys": 0,
    "child_blank_keys": 0,
    "unmatched_child_rows": 0,
    "unmatched_child_ids": [],
    "unused_parent_rows": 0,
    "unused_parent_ids": [],
    "child_rows_before": 15608,
    "left_join_rows_after": 15608
  }
}
```

Order items have no line ID. A repeated order ID is expected for multi-line orders. Exact duplicate lines and repeated order/product pairs require review before deletion.

## Category label mapping proposed for review

| Original label (quoted to expose spaces) | Proposed label | Products |
|---|---|---:|
| `Kitchen` | Kitchen | 10 |
| ` Kitchen` | Kitchen | 2 |
| `Kitchen ` | Kitchen | 1 |
| `kitchen` | Kitchen | 1 |
| `KITCHEN` | Kitchen | 1 |
| ` Bedding` | Bedding | 2 |
| `Bedding` | Bedding | 8 |
| `bedding` | Bedding | 1 |
| `BEDDING` | Bedding | 1 |
| `Bath` | Bath | 9 |
| `bath` | Bath | 1 |
| `Furniture` | Furniture | 9 |
| `Furniture ` | Furniture | 1 |
| `furniture` | Furniture | 1 |
| `FURNITURE` | Furniture | 1 |
| `Lighting` | Lighting | 8 |
| `LIGHTING` | Lighting | 1 |
| `Outdoor` | Outdoor | 9 |
| `OUTDOOR` | Outdoor | 1 |
| ` Outdoor` | Outdoor | 1 |
| `Decor` | Decor | 8 |
| `decor` | Decor | 4 |
| `Storage` | Storage | 7 |
| `Storage ` | Storage | 2 |

## Missing-price investigation and business-rule checks

```json
{
  "repeated_order_product_pairs": 0,
  "rows_in_repeated_pairs": 0,
  "exact_duplicate_item_rows_including_first": 0,
  "missing_unit_price_rows": 199,
  "missing_price_quantity": 259.0,
  "missing_prices_by_status": {
    "completed": 176,
    "returned": 13,
    "canceled": 10
  },
  "missing_prices_by_month": {
    "2024-01": 4,
    "2024-02": 5,
    "2024-03": 5,
    "2024-04": 8,
    "2024-05": 6,
    "2024-06": 4,
    "2024-07": 8,
    "2024-08": 7,
    "2024-09": 2,
    "2024-10": 9,
    "2024-11": 12,
    "2024-12": 11,
    "2025-01": 10,
    "2025-02": 9,
    "2025-03": 8,
    "2025-04": 8,
    "2025-05": 10,
    "2025-06": 7,
    "2025-07": 12,
    "2025-08": 8,
    "2025-09": 5,
    "2025-10": 7,
    "2025-11": 24,
    "2025-12": 10
  },
  "missing_prices_by_product": {
    "1070": 8,
    "1015": 5,
    "1060": 5,
    "1074": 5,
    "1006": 5,
    "1087": 5,
    "1088": 4,
    "1053": 4,
    "1029": 4,
    "1076": 4,
    "1014": 4,
    "1020": 4,
    "1085": 4,
    "1090": 4,
    "1054": 4,
    "1009": 4,
    "1079": 4,
    "1068": 4,
    "1072": 3,
    "1069": 3,
    "1077": 3,
    "1002": 3,
    "1010": 3,
    "1032": 3,
    "1063": 3,
    "1089": 3,
    "1012": 3,
    "1075": 3,
    "1030": 3,
    "1013": 3,
    "1066": 3,
    "1022": 3,
    "1078": 3,
    "1028": 3,
    "1058": 3,
    "1086": 2,
    "1037": 2,
    "1041": 2,
    "1027": 2,
    "1004": 2,
    "1042": 2,
    "1003": 2,
    "1026": 2,
    "1024": 2,
    "1039": 2,
    "1017": 2,
    "1007": 2,
    "1051": 2,
    "1081": 2,
    "1080": 2,
    "1048": 2,
    "1083": 2,
    "1005": 2,
    "1016": 2,
    "1082": 2,
    "1018": 2,
    "1071": 2,
    "1052": 2,
    "1084": 2,
    "1045": 1,
    "1050": 1,
    "1059": 1,
    "1038": 1,
    "1033": 1,
    "1023": 1,
    "1021": 1,
    "1008": 1,
    "1031": 1,
    "1035": 1,
    "1034": 1,
    "1057": 1,
    "1056": 1,
    "1019": 1,
    "1043": 1,
    "1064": 1,
    "1044": 1,
    "1067": 1,
    "1001": 1
  },
  "missing_prices_by_category": {
    "Kitchen": 30,
    "Decor": 27,
    "Storage": 22,
    "Outdoor": 17,
    "Lighting": 16,
    "Bath": 16,
    "Bedding": 13,
    "decor": 12,
    "Furniture": 8,
    "Storage ": 6,
    " Kitchen": 5,
    "bedding": 4,
    " Outdoor": 4,
    "KITCHEN": 3,
    " Bedding": 3,
    "bath": 3,
    "Furniture ": 2,
    "BEDDING": 2,
    "LIGHTING": 2,
    "Kitchen ": 2,
    "FURNITURE": 1,
    "furniture": 1
  },
  "known_prices_different_from_list": 8273,
  "products_with_multiple_transaction_prices": 90,
  "nonpositive_quantity": 0,
  "fractional_quantity": 0,
  "discount_above_known_line_gross": 0,
  "negative_known_line_net": 0,
  "unit_cost_above_list_price": 0,
  "missing_price_rates_by_status": {
    "canceled": {
      "sum": 10,
      "count": 559,
      "mean": 0.017889087656529516
    },
    "completed": {
      "sum": 176,
      "count": 14283,
      "mean": 0.01232234124483652
    },
    "returned": {
      "sum": 13,
      "count": 766,
      "mean": 0.016971279373368148
    }
  },
  "missing_price_rates_by_month": {
    "2024-01": {
      "sum": 4,
      "count": 489,
      "mean": 0.0081799591002045
    },
    "2024-02": {
      "sum": 5,
      "count": 530,
      "mean": 0.009433962264150943
    },
    "2024-03": {
      "sum": 5,
      "count": 570,
      "mean": 0.008771929824561403
    },
    "2024-04": {
      "sum": 8,
      "count": 530,
      "mean": 0.01509433962264151
    },
    "2024-05": {
      "sum": 6,
      "count": 601,
      "mean": 0.009983361064891847
    },
    "2024-06": {
      "sum": 4,
      "count": 540,
      "mean": 0.007407407407407408
    },
    "2024-07": {
      "sum": 8,
      "count": 590,
      "mean": 0.013559322033898305
    },
    "2024-08": {
      "sum": 7,
      "count": 523,
      "mean": 0.01338432122370937
    },
    "2024-09": {
      "sum": 2,
      "count": 519,
      "mean": 0.0038535645472061657
    },
    "2024-10": {
      "sum": 9,
      "count": 561,
      "mean": 0.016042780748663103
    },
    "2024-11": {
      "sum": 12,
      "count": 949,
      "mean": 0.012644889357218124
    },
    "2024-12": {
      "sum": 11,
      "count": 815,
      "mean": 0.013496932515337423
    },
    "2025-01": {
      "sum": 10,
      "count": 568,
      "mean": 0.017605633802816902
    },
    "2025-02": {
      "sum": 9,
      "count": 530,
      "mean": 0.016981132075471698
    },
    "2025-03": {
      "sum": 8,
      "count": 657,
      "mean": 0.0121765601217656
    },
    "2025-04": {
      "sum": 8,
      "count": 680,
      "mean": 0.011764705882352941
    },
    "2025-05": {
      "sum": 10,
      "count": 698,
      "mean": 0.014326647564469915
    },
    "2025-06": {
      "sum": 7,
      "count": 689,
      "mean": 0.010159651669085631
    },
    "2025-07": {
      "sum": 12,
      "count": 624,
      "mean": 0.019230769230769232
    },
    "2025-08": {
      "sum": 8,
      "count": 680,
      "mean": 0.011764705882352941
    },
    "2025-09": {
      "sum": 5,
      "count": 598,
      "mean": 0.008361204013377926
    },
    "2025-10": {
      "sum": 7,
      "count": 679,
      "mean": 0.010309278350515464
    },
    "2025-11": {
      "sum": 24,
      "count": 1151,
      "mean": 0.020851433536055605
    },
    "2025-12": {
      "sum": 10,
      "count": 837,
      "mean": 0.011947431302270013
    }
  },
  "missing_price_rates_by_category_normalized": {
    "bath": {
      "sum": 19,
      "count": 1740,
      "mean": 0.010919540229885057
    },
    "bedding": {
      "sum": 22,
      "count": 1932,
      "mean": 0.011387163561076604
    },
    "decor": {
      "sum": 39,
      "count": 3073,
      "mean": 0.01269118125610153
    },
    "furniture": {
      "sum": 12,
      "count": 1045,
      "mean": 0.011483253588516746
    },
    "kitchen": {
      "sum": 40,
      "count": 3195,
      "mean": 0.012519561815336464
    },
    "lighting": {
      "sum": 18,
      "count": 1295,
      "mean": 0.013899613899613899
    },
    "outdoor": {
      "sum": 21,
      "count": 1476,
      "mean": 0.014227642276422764
    },
    "storage": {
      "sum": 28,
      "count": 1852,
      "mean": 0.01511879049676026
    }
  }
}
```

For missing-price diagnostics only, the order lookup collapses exact duplicate order records in memory; conflicting order IDs would stop the audit. Source item rows remain intact. The raw join inflation is reported above.
The record-level investigation is saved under data/profile/ (ignored by Git). Product-level observed prices are evidence, not proof of the missing transaction price. Current list price may differ from the historical price.

## Proposed cleaning rules

1. Preserve source CSVs; record hashes above identify the audited versions. Parse dates explicitly and keep identifiers as text in prepared data.
2. Treat blank discount codes as “no code recorded”; do not assume a zero discount from this field alone. Use discount_amount for the recorded line discount (project README definition).
3. Review exact duplicate item rows against their order/product keys. There is no line identifier to establish whether identical lines are accidental duplicates.
4. Retain missing prices while investigating. Do not substitute list price or a product average automatically. Revenue calculations must report the affected rows and coverage until a rule is adopted.
5. Review negative/zero values, label collisions and join failures reported above. Outlying values alone do not establish errors.
6. Define eligible order statuses and revenue separately before sales analysis. Returned/cancelled orders must not silently enter completed-sales revenue.

No cleaning corrections or exclusions have been applied. See cleaning_log.md for the audit and proposed decisions.
