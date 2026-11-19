"""Compare final order statuses and average order value by category."""
import json
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd

from analyze_categories import aggregate, export_records, plt, style
from calculate_metrics import ROOT, prepare_orders, require, summarize
from matplotlib.ticker import PercentFormatter


def plot_rates(results, path):
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.7), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.23, right=0.96, top=0.76, bottom=0.19, wspace=0.18)
    positions = range(len(results))
    labels = [f'{row.category} ({row.all_orders:,})' for row in results.itertuples()]
    rate_limit = max(0.01, 1.2 * results[['return_rate', 'cancellation_rate']].max().max())

    for ax, column, title, color in (
        (axes[0], 'return_rate', 'Return rate', '#2563a6'),
        (axes[1], 'cancellation_rate', 'Cancellation rate', '#b54920'),
    ):
        rates = results[column]
        bars = ax.barh(positions, rates, color=color, height=0.62)
        ax.bar_label(bars, labels=[f'{rate:.2%}' for rate in rates], padding=5, fontsize=9)
        ax.set_title(title, loc='left', weight='bold')
        ax.set_xlim(0, rate_limit)
        ax.xaxis.set_major_formatter(PercentFormatter(1))
        ax.tick_params(axis='y', length=0)
        style(ax)

    axes[0].set_yticks(positions, labels)
    axes[0].invert_yaxis()
    fig.suptitle('Returns and cancellations by category', x=0.23, y=0.95,
                 ha='left', fontsize=17, weight='bold')
    fig.text(0.23, 0.87, '2024–2025 combined · category labels include distinct order counts', fontsize=10)
    fig.text(0.23, 0.06, 'Share of orders containing each category, based on final order status.\n'
             'An order can appear in several categories. Source: cleaned project data.', fontsize=9)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_report(results, path):
    highest_return = results.iloc[0]
    highest_cancel = results.loc[results.cancellation_rate.idxmax()]
    highest_aov = results.dropna(subset=['category_aov_usd']).sort_values(
        'category_aov_usd', key=lambda values: values.map(Decimal), ascending=False).iloc[0]
    lines = [
        '# Category order outcomes, 2024–2025', '',
        'Return and cancellation rates divide the respective final-status counts by all distinct '
        'orders containing the category. Each order counts once per category. An order that '
        'contains several categories contributes its final status to each one. The data records '
        'status at order level, so the figures describe orders containing a category.', '',
        'Category average order value (AOV) divides the category’s known-price merchandise revenue '
        'from completed orders by all completed orders containing that category, including orders '
        'with missing prices. Only revenue from the category’s own lines contributes to this '
        'measure. Shipping is excluded. Missing prices can pull AOV down. Price coverage is the '
        'share of completed category lines with a known unit price. The storewide AOV in '
        'metrics.md uses fully priced completed orders and measures whole baskets.', '',
        '## Observations', '',
        f'- {highest_return.category} had the highest return rate at {highest_return.return_rate:.2%} '
        f'({highest_return.returned_orders:,} of {highest_return.all_orders:,} orders).',
        f'- {highest_cancel.category} had the highest cancellation rate at {highest_cancel.cancellation_rate:.2%} '
        f'({highest_cancel.canceled_orders:,} of {highest_cancel.all_orders:,} orders).',
        f'- {highest_aov.category} had the highest category AOV at ${Decimal(highest_aov.category_aov_usd):,.2f}.',
        '',
        '![Return and cancellation rates by category](figures/category_outcomes.png)', '',
        '## Category detail', '',
        '| Category | All orders | Completed | Returned | Return rate | Canceled | Cancellation rate | Category AOV (USD) | Line price coverage |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for row in results.itertuples():
        aov = f'${Decimal(row.category_aov_usd):,.2f}' if row.category_aov_usd is not None else 'N/A'
        coverage = f'{row.line_price_coverage:.2%}' if pd.notna(row.line_price_coverage) else 'N/A'
        lines.append(f'| {row.category} | {row.all_orders:,} | {row.completed_orders:,} | '
                     f'{row.returned_orders:,} | {row.return_rate:.2%} | {row.canceled_orders:,} | '
                     f'{row.cancellation_rate:.2%} | {aov} | {coverage} |')
    lines += [
        '', '## Reproduction and validation', '',
        r'Run section 5 of the notebook or `.\.venv\Scripts\python.exe scripts\analyze_category_outcomes.py` '
        'after regenerating the point 4 results. Rates and line price coverage in the companion CSV are '
        'fractions. AOV uses integer-cent revenue and is rounded half up to two decimal places.', '',
        'Validation checked the cleaned input hashes, join cardinality, distinct storewide counts by '
        'status and the revenue and line coverage counts for every category against point 4.', '',
    ]
    path.write_text('\n'.join(lines), encoding='utf-8')


def main():
    orders, items, hashes = prepare_orders()
    reports = ROOT / 'reports'
    metrics = json.loads((reports / 'metrics_results.json').read_text(encoding='utf-8'))
    categories = json.loads((reports / 'category_results.json').read_text(encoding='utf-8'))
    require(hashes == metrics['cleaned_sha256'] == categories['cleaned_sha256'], 'Baseline input hashes differ.')
    require(set(orders.year) == {2024, 2025}, 'Expected orders for 2024 and 2025.')
    require(summarize(orders) == metrics['overall'], 'Baseline overall metrics differ.')

    catalog = pd.read_csv(ROOT / 'data/cleaned/products.csv', dtype=str, keep_default_na=False)
    lines = items.merge(catalog[['product_id', 'category']], on='product_id',
                        how='left', validate='many_to_one')
    require(len(lines) == len(items) and lines.category.fillna('').ne('').all(),
            'Every item line must map to a product category.')
    lines = lines.merge(orders[['order_id', 'status']], on='order_id', validate='many_to_one')
    require(len(lines) == len(items), 'Order join lost or multiplied item lines.')

    category_orders = lines[['category', 'order_id', 'status']].drop_duplicates()
    statuses = ['completed', 'returned', 'canceled']
    for status in statuses:
        distinct_orders = category_orders.loc[category_orders.status.eq(status), 'order_id'].nunique()
        require(distinct_orders == metrics['overall'][f'{status}_orders'], f'{status} order count mismatch.')
    results = (category_orders.groupby(['category', 'status']).size().unstack(fill_value=0)
               .reindex(columns=statuses, fill_value=0).add_suffix('_orders').reset_index())
    results.columns.name = None
    results['all_orders'] = results[[f'{status}_orders' for status in statuses]].sum(axis=1)
    results['return_rate'] = results.returned_orders / results.all_orders
    results['cancellation_rate'] = results.canceled_orders / results.all_orders
    results = results.sort_values(['return_rate', 'category'], ascending=[False, True])

    completed = aggregate(lines.loc[lines.status.eq('completed')], ['category'])
    expected = pd.DataFrame(categories['category_revenue_overall']).set_index('category')
    actual = export_records(completed).set_index('category').sort_index()
    fields = ['known_price_revenue_usd', 'completed_lines', 'priced_lines']
    require(actual[fields].equals(expected[fields].sort_index()), 'Point 4 category totals differ.')
    results = results.merge(actual[fields + ['line_price_coverage']], left_on='category',
                            right_index=True, how='left', validate='one_to_one')
    results['category_aov_usd'] = [
        str((Decimal(row.known_price_revenue_usd) / Decimal(row.completed_orders))
            .quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        if row.completed_orders and pd.notna(row.known_price_revenue_usd) else None
        for row in results.itertuples()
    ]

    results.to_csv(reports / 'category_outcomes.csv', index=False)
    plot_rates(results, reports / 'figures/category_outcomes.png')
    write_report(results, reports / 'category_outcomes.md')
    print(f'Verified category outcomes across {len(results)} categories.')


if __name__ == '__main__':
    main()
