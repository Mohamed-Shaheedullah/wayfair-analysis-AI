"""Calculate the agreed initial metrics from validated cleaned files.

Money is calculated in integer cents. Unknown prices remain unknown.
Run from any directory with the project's Python environment.
"""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import hashlib
import json

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def cents(value):
    amount = Decimal(value) * 100
    require(amount.is_finite() and amount == amount.to_integral_value(),
            f'Expected finite whole cents: {value}')
    return int(amount)


def dollars(value):
    return f'{Decimal(int(value)) / 100:.2f}'


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def summarize(orders):
    completed = orders.loc[orders.status.eq('completed')]
    priced = completed.loc[completed.price_complete]
    total = len(orders)
    completed_count = len(completed)
    complete_count = len(priced)
    item_count = int(completed.item_lines.sum())
    known_count = int(completed.known_price_lines.sum())
    aov = (Decimal(int(priced.known_revenue_cents.sum())) / 100 / complete_count
           ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if complete_count else None
    return {
        'all_orders': total,
        'completed_orders': completed_count,
        'canceled_orders': int(orders.status.eq('canceled').sum()),
        'returned_orders': int(orders.status.eq('returned').sum()),
        'cancellation_rate': ratio(int(orders.status.eq('canceled').sum()), total),
        'return_rate': ratio(int(orders.status.eq('returned').sum()), total),
        'completed_units_sold': int(completed.units.sum()),
        'known_price_merchandise_revenue_usd': dollars(completed.known_revenue_cents.sum()),
        'completed_shipping_income_usd': dollars(completed.shipping_cents.sum()),
        'completed_item_lines': item_count,
        'completed_known_price_lines': known_count,
        'completed_missing_price_lines': item_count - known_count,
        'completed_missing_price_units': int(completed.missing_price_units.sum()),
        'completed_line_price_coverage': ratio(known_count, item_count),
        'completed_orders_with_all_prices': complete_count,
        'completed_orders_with_missing_prices': completed_count - complete_count,
        'completed_order_price_coverage': ratio(complete_count, completed_count),
        'fully_priced_completed_order_revenue_usd': dollars(priced.known_revenue_cents.sum()),
        'aov_fully_priced_completed_orders_usd': str(aov) if aov is not None else None,
    }


def main():
    manifest = json.loads((ROOT / 'reports/cleaning_validation.json').read_text())
    hashes = {}
    tables = {}
    for name in ('orders', 'order_items', 'products'):
        path = ROOT / 'data/cleaned' / f'{name}.csv'
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        require(hashes[name] == manifest['cleaned_sha256'][name],
                f'{name} changed since cleaning validation; review before calculation.')
        tables[name] = pd.read_csv(path, dtype=str, keep_default_na=False)

    orders, items = tables['orders'], tables['order_items']
    require(orders.order_id.is_unique, 'Orders must have unique IDs.')
    require(set(orders.status) == {'completed', 'canceled', 'returned'}, 'Unexpected statuses.')
    missing = items.unit_price.eq('')
    require(items.unit_price_missing.eq('True').equals(missing), 'Missing-price flag differs.')
    items['quantity'] = pd.to_numeric(items.quantity, errors='raise').astype('int64')
    items['discount_cents'] = items.discount_amount.map(cents)
    # Nullable integers ensure missing-price lines cannot contribute a fabricated amount.
    items['unit_price_cents'] = pd.array(
        [None if value == '' else cents(value) for value in items.unit_price], dtype='Int64')
    items['line_revenue_cents'] = items.quantity * items.unit_price_cents - items.discount_cents
    items['known_price'] = ~missing
    items['missing_price_units'] = items.quantity.where(missing, 0)
    require(items.line_revenue_cents.dropna().ge(0).all(), 'Negative known line revenue.')
    require(items.order_id.isin(orders.order_id).all(), 'Unmatched item orders.')

    by_order = items.groupby('order_id', as_index=False).agg(
        item_lines=('product_id', 'size'), known_price_lines=('known_price', 'sum'),
        units=('quantity', 'sum'), missing_price_units=('missing_price_units', 'sum'),
        known_revenue_cents=('line_revenue_cents', lambda values: values.sum(min_count=1)))
    by_order['price_complete'] = by_order.item_lines.eq(by_order.known_price_lines)
    orders = orders.merge(by_order, on='order_id', validate='one_to_one', how='left')
    require(orders.item_lines.notna().all(), 'Order without items.')
    orders['shipping_cents'] = orders.shipping_fee.map(cents)
    orders['order_date'] = pd.to_datetime(orders.order_date, utc=True, errors='raise')
    orders['year'] = orders.order_date.dt.year
    orders['complete_revenue_cents'] = orders.known_revenue_cents.where(orders.price_complete)

    overall = summarize(orders)
    annual = {str(year): summarize(group) for year, group in orders.groupby('year')}
    money_fields = ('known_price_merchandise_revenue_usd', 'completed_shipping_income_usd',
                    'fully_priced_completed_order_revenue_usd')
    count_fields = ('all_orders', 'completed_orders', 'canceled_orders', 'returned_orders',
                    'completed_units_sold', 'completed_item_lines', 'completed_known_price_lines',
                    'completed_missing_price_lines', 'completed_missing_price_units',
                    'completed_orders_with_all_prices', 'completed_orders_with_missing_prices')
    for field in count_fields:
        require(sum(row[field] for row in annual.values()) == overall[field], f'Annual count: {field}')
    for field in money_fields:
        require(sum(Decimal(row[field]) for row in annual.values()) == Decimal(overall[field]),
                f'Annual money reconciliation: {field}')
    eligible = orders.loc[orders.status.eq('completed'), 'order_id']
    direct = items.loc[items.order_id.isin(eligible), 'line_revenue_cents'].sum(min_count=1)
    require(dollars(direct) == overall['known_price_merchandise_revenue_usd'], 'Line/order revenue mismatch.')
    require(sum(overall[field] for field in ('completed_orders', 'canceled_orders', 'returned_orders'))
            == overall['all_orders'], 'Status count mismatch.')

    output = ROOT / 'data/metrics'
    output.mkdir(exist_ok=True)
    orders.to_csv(output / 'order_metrics.csv', index=False)
    pd.DataFrame.from_dict(annual, orient='index').rename_axis('year').to_csv(output / 'annual_metrics.csv')
    result = {'cleaned_sha256': hashes, 'overall': overall, 'annual': annual,
              'validation': 'Passed: cleaned file hashes, join cardinality, line/order revenue, '
                            'status counts, annual counts and monetary reconciliations.'}
    (ROOT / 'reports/metrics_results.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    definitions = '''# Initial metrics: 2024–2025

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

'''
    rows = [
        ('All orders', 'all_orders', 'count'),
        ('Completed orders', 'completed_orders', 'count'),
        ('Canceled orders', 'canceled_orders', 'count'),
        ('Returned orders', 'returned_orders', 'count'),
        ('Cancellation rate', 'cancellation_rate', 'pct'),
        ('Return rate', 'return_rate', 'pct'),
        ('Completed units sold', 'completed_units_sold', 'count'),
        ('Known-price merchandise revenue (USD)', 'known_price_merchandise_revenue_usd', 'money'),
        ('Completed shipping income (USD)', 'completed_shipping_income_usd', 'money'),
        ('AOV: fully priced completed orders (USD)', 'aov_fully_priced_completed_orders_usd', 'money'),
        ('Fully priced completed-order revenue (USD)', 'fully_priced_completed_order_revenue_usd', 'money'),
        ('Completed orders with all prices', 'completed_orders_with_all_prices', 'count'),
        ('Completed orders with missing prices', 'completed_orders_with_missing_prices', 'count'),
        ('Completed-order price coverage', 'completed_order_price_coverage', 'pct'),
        ('Completed item lines', 'completed_item_lines', 'count'),
        ('Completed missing-price lines', 'completed_missing_price_lines', 'count'),
        ('Completed missing-price units', 'completed_missing_price_units', 'count'),
        ('Completed-line price coverage', 'completed_line_price_coverage', 'pct'),
    ]
    columns = {'2024–2025': overall, **annual}
    lines = ['| Metric | ' + ' | '.join(columns) + ' |', '|---|' + '---:|' * len(columns)]
    for label, key, kind in rows:
        values = []
        for record in columns.values():
            value = record[key]
            values.append('N/A' if value is None else
                          f'{value:.2%}' if kind == 'pct' else
                          f'${Decimal(value):,.2f}' if kind == 'money' else f'{value:,}')
        lines.append('| ' + label + ' | ' + ' | '.join(values) + ' |')
    ending = '''

## Reproduction and validation

Run `.\\.venv\\Scripts\\python.exe scripts\\calculate_metrics.py` from the project root.
Uses only `data/cleaned/` inputs verified against the cleaning manifest. Sources and cleaned inputs are unchanged.
Detailed order calculations and annual exports are under `data/metrics/` (excluded from Git).
Machine-readable totals, input hashes and validation results are in `reports/metrics_results.json`.
Validation passed for cleaned-file hashes, joins, line-to-order revenue, status counts, and annual-to-overall counts and money. AOV is recomputed from its matching numerator and denominator for each period, not averaged across years.

These are initial metric calculations. Monthly comparisons, category/product analysis, charts and final recommendations remain later steps.
'''
    (ROOT / 'reports/metrics.md').write_text(definitions + '\n'.join(lines) + ending, encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
