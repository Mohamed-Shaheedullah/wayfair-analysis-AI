"""Create validated cleaned CSV copies; source CSVs are never written."""
from pathlib import Path
import hashlib
import json
from decimal import Decimal
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DEST = DATA / 'cleaned'
NAMES = ('orders', 'order_items', 'products')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    before = {n: digest(DATA / f'{n}.csv') for n in NAMES}
    sources = {n: pd.read_csv(DATA / f'{n}.csv', dtype=str, keep_default_na=False) for n in NAMES}
    cleaned = {n: d.copy() for n, d in sources.items()}
    events = []

    def record(name, row, column, old, new, rule, action='correction'):
        events.append(dict(file=f'{name}.csv', source_csv_row=int(row), column=column,
                           original_value=old, cleaned_value=new, rule=rule, action=action))

    orders = cleaned['orders']
    duplicate = orders.duplicated(keep='first')
    for idx in orders.index[duplicate]:
        record('orders', idx+2, '*', json.dumps(orders.loc[idx].to_dict()), '', 'C001', 'excluded exact duplicate')
    cleaned['orders'] = orders = orders.loc[~duplicate].copy()
    require(orders.order_id.is_unique, 'Conflicting order IDs: review before cleaning.')
    dates = pd.to_datetime(orders.order_date, format='%Y-%m-%d %H:%M:%S', errors='raise', utc=True)
    normalized_dates = dates.dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    for idx in orders.index:
        record('orders', idx+2, 'order_date', orders.at[idx, 'order_date'], normalized_dates.at[idx], 'C006')
    orders['order_date'] = normalized_dates

    products = cleaned['products']
    canonical = {'kitchen': 'Kitchen', 'decor': 'Decor', 'storage': 'Storage', 'outdoor': 'Outdoor',
                 'lighting': 'Lighting', 'bath': 'Bath', 'bedding': 'Bedding', 'furniture': 'Furniture'}
    mapped = products.category.str.strip().str.casefold().map(canonical)
    require(mapped.notna().all(), 'Unexpected category: update the reviewed mapping.')
    for idx in products.index[products.category.ne(mapped)]:
        record('products', idx+2, 'category', products.at[idx, 'category'], mapped.at[idx], 'C002')
    products['category'] = mapped

    items = cleaned['order_items']
    items['unit_price_missing'] = items.unit_price.str.strip().eq('')
    require(items.loc[items.unit_price_missing, 'unit_price'].eq('').all(), 'Unexpected whitespace-only price: review source.')
    for idx in items.index[items.unit_price_missing]:
        record('order_items', idx+2, 'unit_price_missing', '', 'True', 'C003', 'flag missing price')

    # Validate types in memory while retaining decimal source strings in CSV exports.
    numeric_columns = {'orders': ['shipping_fee'], 'products': ['list_price', 'unit_cost'],
                       'order_items': ['quantity', 'unit_price', 'discount_amount']}
    for name, columns in numeric_columns.items():
        for column in columns:
            s = cleaned[name][column]
            known = s[s.ne('')]
            require(len(known) == len(s) or (name, column) == ('order_items', 'unit_price'), f'Unexpected missing {name}.{column}')
            values = pd.to_numeric(known, errors='raise')
            require(values.ge(0).all(), f'Negative {name}.{column}')
            require(values.map(lambda x: float('-inf') < x < float('inf')).all(), f'Nonfinite {column}')
    quantity = pd.to_numeric(items.quantity)
    require((quantity.gt(0) & quantity.mod(1).eq(0)).all(), 'Invalid quantity')
    for name, d in cleaned.items():
        for col in d.columns:
            if col.endswith('_id'):
                require(d[col].str.fullmatch(r'\d+').all(), f'Invalid {name}.{col}')
    require(products.product_id.is_unique, 'Duplicate product IDs')
    require(items.order_id.isin(orders.order_id).all(), 'Unmatched order IDs')
    require(items.product_id.isin(products.product_id).all(), 'Unmatched product IDs')
    joined = items.merge(orders, on='order_id', validate='many_to_one').merge(products, on='product_id', validate='many_to_one')
    require(len(joined) == len(items), 'Join changed item count')
    require(items.drop(columns='unit_price_missing').equals(sources['order_items']), 'Item source values changed')
    require(orders.drop(columns='order_date').equals(sources['orders'].loc[~duplicate].drop(columns='order_date')), 'Unexpected order changes')
    require(products.drop(columns='category').equals(sources['products'].drop(columns='category')), 'Unexpected product changes')

    # Exact decimal reconciliation avoids floating-point tolerances for money.
    totals = {}
    for name, columns in numeric_columns.items():
        totals[name] = {c: str(sum((Decimal(v) for v in cleaned[name][c] if v != ''), Decimal(0))) for c in columns}
    manifest = dict(source_sha256=before, rows_before={n: len(d) for n,d in sources.items()},
                    rows_after={n: len(d) for n,d in cleaned.items()},
                    excluded_duplicate_orders=int(duplicate.sum()), category_values_changed=int(sources['products'].category.ne(mapped).sum()),
                    categories_before=int(sources['products'].category.nunique()), categories_after=int(mapped.nunique()),
                    missing_prices=int(items.unit_price_missing.sum()), missing_prices_imputed=0,
                    joined_item_rows=len(joined), numeric_totals_after=totals,
                    assumptions=['IDs are text; CSV readers must specify string types to preserve this.',
                                 'order_date is UTC per project documentation; exported as ISO 8601 with Z suffix.',
                                 'Blank discount_code means no code recorded; it remains blank.',
                                 'No revenue or status exclusions applied. Missing prices remain blank.',
                                 'Numeric CSV values preserve source decimal spelling; parse explicitly on import.'])
    DEST.mkdir(exist_ok=True)
    for name, d in cleaned.items():
        target = DEST / f'{name}.csv'
        d.to_csv(target, index=False)
        check = pd.read_csv(target, dtype=str, keep_default_na=False)
        expected = d.astype(str).reset_index(drop=True)
        require(check.equals(expected), f'CSV round-trip failed: {name}')
    pd.DataFrame(events).to_csv(DEST / 'cleaning_changes.csv', index=False)
    require(before == {n: digest(DATA / f'{n}.csv') for n in NAMES}, 'Source hash changed')
    manifest['cleaned_sha256'] = {n: digest(DEST / f'{n}.csv') for n in NAMES}
    manifest['validation'] = 'Passed: source hashes, CSV round-trips, allowed changes, numeric checks, key integrity and join counts.'
    (ROOT / 'reports' / 'cleaning_validation.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
