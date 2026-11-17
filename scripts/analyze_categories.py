"""Point 4: category revenue by year, combined product quantities and monthly mix."""
import calendar
import json
from decimal import Decimal

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, PercentFormatter
import pandas as pd

from calculate_metrics import ROOT, prepare_orders, summarize, require, dollars


def aggregate(lines, keys):
    """Keep unknown revenue missing; coverage counts describe records, not dollars."""
    result = lines.groupby(keys, as_index=False).agg(
        revenue_cents=('line_revenue_cents', lambda x: x.sum(min_count=1)),
        completed_units=('quantity', 'sum'), completed_lines=('quantity', 'size'),
        priced_lines=('known_price', 'sum'), missing_price_units=('missing_price_units', 'sum'))
    result['missing_price_lines'] = result.completed_lines - result.priced_lines
    result['line_price_coverage'] = result.priced_lines / result.completed_lines
    return result


def export_records(frame):
    result = frame.copy()
    if 'revenue_cents' in result:
        result['known_price_revenue_usd'] = result.pop('revenue_cents').map(
            lambda value: None if pd.isna(value) else dollars(value))
    return result


def style(ax):
    ax.spines[['top', 'right']].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis='x', alpha=0.18)


def charts(annual, products, monthly, categories, colors):
    figures = ROOT / 'reports/figures'
    figures.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, 6.5))
    fig.subplots_adjust(left=0.18, right=0.96, top=0.81, bottom=0.22)
    positions = list(range(len(categories)))
    for year, offset, color in [(2024, -0.19, '#2563a6'), (2025, 0.19, '#b54920')]:
        values = annual.loc[annual.year.eq(year)].set_index('category').loc[categories]
        bars = ax.barh([p + offset for p in positions], values.revenue_cents.astype(float) / 100,
                       height=0.36, color=color, label=str(year))
        ax.bar_label(bars, labels=[f'${v / 100000:,.1f}k' for v in values.revenue_cents],
                     padding=4, fontsize=8)
    ax.set_yticks(positions, categories)
    ax.invert_yaxis()
    ax.set_xlim(0, float(annual.revenue_cents.max()) / 100 * 1.24)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'${v / 1000:,.0f}k'))
    ax.set_xlabel('Known-price merchandise revenue (USD)')
    ax.legend(frameon=False, title='Order year')
    style(ax)
    fig.suptitle('Category revenue: 2024 vs 2025', x=0.18, ha='left', fontsize=17, weight='bold')
    fig.text(0.18, 0.87, 'Categories sorted by combined 2024–2025 revenue', fontsize=11)
    fig.text(0.18, 0.07, 'Completed orders · after line discounts · shipping excluded. Missing-price lines excluded.\n'
             'Source: cleaned project data; UTC order placement dates and final status.', fontsize=9, linespacing=1.6)
    fig.savefig(figures / 'category_revenue.png', dpi=180)
    plt.close(fig)

    top = products.head(10)
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.subplots_adjust(left=0.36, right=0.94, top=0.81, bottom=0.20)
    bars = ax.barh(range(len(top)), top.completed_units, color='#2563a6')
    ax.set_yticks(range(len(top)), [f'{r.product_name} (ID {r.product_id})' for r in top.itertuples()])
    ax.invert_yaxis()
    ax.bar_label(bars, padding=5, fmt='%d')
    ax.set_xlim(0, top.completed_units.max() * 1.15)
    ax.set_xlabel('Units sold in completed orders')
    style(ax)
    fig.suptitle('Top 10 products by quantity: 2024–2025', x=0.06, ha='left', fontsize=17, weight='bold')
    fig.text(0.06, 0.87, 'Both years combined · products kept distinct by ID', fontsize=11)
    fig.text(0.06, 0.07, 'Includes completed units with missing selling prices. Canceled and returned orders excluded.\n'
             'Source: cleaned project data. Quantity ties ordered by numeric product ID.', fontsize=9, linespacing=1.6)
    fig.savefig(figures / 'top_products.png', dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.10, right=0.98, top=0.79, bottom=0.20, hspace=0.30)
    for ax, year in zip(axes, (2024, 2025)):
        values = monthly.loc[monthly.year.eq(year)].pivot(index='month_number', columns='category', values='revenue_share')
        bottom = pd.Series(0.0, index=range(1, 13))
        for category in categories:
            heights = values[category].reindex(range(1, 13))
            ax.bar(range(1, 13), heights, bottom=bottom, color=colors[category], label=category, width=0.8)
            bottom += heights
        ax.set_title(str(year), loc='left', weight='bold')
        ax.set_ylim(0, 1)
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.set_ylabel('Revenue share')
        ax.spines[['top', 'right']].set_visible(False)
        ax.set_xticks(range(1, 13), list(calendar.month_abbr)[1:])
        ax.tick_params(labelbottom=True)
    axes[-1].set_xlabel('Order month (UTC)')
    fig.suptitle('Monthly category mix: share of revenue', x=0.10, ha='left', fontsize=17, weight='bold')
    fig.legend(*axes[0].get_legend_handles_labels(), loc='upper center', bbox_to_anchor=(0.54, 0.91),
               ncol=4, frameon=False)
    fig.text(0.10, 0.06, 'Each month totals 100% of known-price completed merchandise revenue; shipping excluded.\n'
             'Missing-price lines excluded; shares may differ if their prices were known.\n'
             'Source: cleaned project data; UTC order placement dates and final status.', fontsize=9, linespacing=1.5)
    fig.savefig(figures / 'monthly_category_mix.png', dpi=180)
    plt.close(fig)


def main():
    orders, items, hashes = prepare_orders()
    baseline = json.loads((ROOT / 'reports/metrics_results.json').read_text(encoding='utf-8'))
    monthly_baseline = json.loads((ROOT / 'reports/monthly_results.json').read_text(encoding='utf-8'))
    for previous in (baseline, monthly_baseline):
        require(hashes == previous['cleaned_sha256'], 'Baseline input hashes differ.')
        require(summarize(orders) == previous['overall'], 'Baseline overall metrics differ.')
    catalog = pd.read_csv(ROOT / 'data/cleaned/products.csv', dtype=str, keep_default_na=False)
    require(catalog.product_id.is_unique, 'Catalog IDs must be unique.')
    require(catalog.category.ne('').all(), 'Missing category.')
    lines = items.merge(orders[['order_id', 'status', 'order_date', 'year']],
                        on='order_id', how='left', validate='many_to_one')
    lines = lines.merge(catalog[['product_id', 'product_name', 'category']],
                        on='product_id', how='left', validate='many_to_one', indicator=True)
    require(len(lines) == len(items) and lines['_merge'].eq('both').all(), 'Product join lost or multiplied lines.')
    lines = lines.loc[lines.status.eq('completed')].copy()
    lines['month'] = lines.order_date.dt.strftime('%Y-%m')
    lines['month_number'] = lines.order_date.dt.month

    annual = aggregate(lines, ['year', 'category'])
    overall = aggregate(lines, ['category']).sort_values('revenue_cents', ascending=False).reset_index(drop=True)
    categories = overall.category.tolist()
    require(set(categories) == set(catalog.category), 'A catalog category has no completed sales; review coverage.')
    annual['revenue_share'] = annual.revenue_cents / annual.groupby('year').revenue_cents.transform('sum')
    overall['revenue_share'] = overall.revenue_cents / overall.revenue_cents.sum()
    monthly = aggregate(lines, ['month', 'year', 'month_number', 'category'])
    # Explicit zero activity for absent month/category pairs, while preserving missing-only revenue as unknown.
    grid = pd.MultiIndex.from_product([sorted(monthly_baseline['monthly']), categories], names=['month', 'category'])
    monthly = monthly.set_index(['month', 'category']).reindex(grid)
    absent = monthly.completed_lines.isna()
    for field in ['revenue_cents', 'completed_units', 'completed_lines', 'priced_lines', 'missing_price_units', 'missing_price_lines']:
        monthly.loc[absent, field] = 0
        monthly[field] = monthly[field].astype('Int64')
    monthly = monthly.reset_index()
    monthly['year'] = monthly.month.str[:4].astype(int)
    monthly['month_number'] = monthly.month.str[-2:].astype(int)
    monthly['revenue_share'] = monthly.revenue_cents / monthly.groupby('month').revenue_cents.transform('sum')
    require(monthly.revenue_share.notna().all(), 'Unknown category/month share; chart requires review.')

    products = aggregate(lines, ['product_id', 'product_name', 'category'])
    products['numeric_product_id'] = pd.to_numeric(products.product_id, errors='raise')
    products = products.sort_values(['completed_units', 'numeric_product_id'], ascending=[False, True]).drop(columns='numeric_product_id')
    products.insert(0, 'rank', range(1, len(products) + 1))

    def reconcile(group, expected, label):
        require(dollars(group.revenue_cents.sum()) == expected['known_price_merchandise_revenue_usd'], f'{label}: revenue')
        for actual, key in [('completed_units', 'completed_units_sold'), ('completed_lines', 'completed_item_lines'),
                            ('missing_price_lines', 'completed_missing_price_lines'), ('missing_price_units', 'completed_missing_price_units')]:
            require(int(group[actual].sum()) == expected[key], f'{label}: {key}')

    reconcile(overall, baseline['overall'], 'Overall categories')
    reconcile(products, baseline['overall'], 'Products')
    for year, group in annual.groupby('year'):
        expected = summarize(orders.loc[orders.year.eq(year)])
        require(expected == baseline['annual'][str(year)], 'Annual baseline changed.')
        reconcile(group, expected, str(year))
    for month, group in monthly.groupby('month'):
        reconcile(group, monthly_baseline['monthly'][month], month)
        require(abs(float(group.revenue_share.sum()) - 1) < 1e-12, 'Monthly shares do not sum to 100%.')
    for category in categories:
        expected = overall.loc[overall.category.eq(category)].iloc[0]
        for frame in (annual, monthly, products):
            group = frame.loc[frame.category.eq(category)]
            require(int(group.revenue_cents.sum()) == int(expected.revenue_cents), 'Category revenue mismatch.')
            require(int(group.completed_units.sum()) == int(expected.completed_units), 'Category quantity mismatch.')

    colors = dict(zip(categories, ['#2563a6', '#e69f00', '#009e73', '#cc79a7', '#56b4e9', '#d55e00', '#8073ac', '#666666']))
    require(len(colors) == len(categories), 'Extend chart palette for additional categories.')
    charts(annual, products, monthly, categories, colors)
    reports = ROOT / 'reports'
    tables = {'category_revenue_annual': annual, 'category_revenue_overall': overall,
              'monthly_category_mix': monthly, 'product_rankings': products}
    for name, frame in tables.items():
        export_records(frame).to_csv(reports / f'{name}.csv', index=False)

    leader = overall.iloc[0]
    top = products.iloc[0]
    findings = [f'{leader.category} generated the most combined known-price revenue: '
                f'${Decimal(dollars(leader.revenue_cents)):,.2f} ({leader.revenue_share:.2%} of 2024–2025 revenue).',
                f'{top.product_name} (ID {top.product_id}) ranked first by completed quantity: {top.completed_units:,} units.']
    yearly = annual.pivot(index='category', columns='year', values='revenue_share')
    shift = yearly[2025] - yearly[2024]
    biggest = shift.abs().idxmax()
    findings.append(f'{biggest} had the largest absolute annual revenue-share change: '
                    f'{yearly.loc[biggest, 2024]:.2%} in 2024 to {yearly.loc[biggest, 2025]:.2%} in 2025 '
                    f'({shift[biggest] * 100:+.2f} percentage points).')
    for category in ('Outdoor', 'Decor'):
        if category in categories:
            peaks = []
            for year in (2024, 2025):
                group = monthly.loc[monthly.category.eq(category) & monthly.year.eq(year)]
                peak = group.loc[group.revenue_share.idxmax()]
                peaks.append(f'{calendar.month_name[peak.month_number]} {year} ({peak.revenue_share:.2%})')
            findings.append(f'{category} reached its highest monthly revenue share in ' + ' and '.join(peaks)
                            + '. These are composition peaks, not necessarily peak dollar sales.')
    validation = ('Passed: cleaned hashes and baseline metrics; joins preserve item rows; category, product, '
                  'annual and all 24 monthly revenues, units and missing-price counts reconcile; '
                  'category totals reconcile across views; monthly shares sum to 100%.')
    result = dict(cleaned_sha256=hashes, findings=findings, validation=validation,
                  **{name: json.loads(export_records(frame).to_json(orient='records', double_precision=15))
                     for name, frame in tables.items()})
    (reports / 'category_results.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')

    text = ['# Category and product analysis: 2024–2025', '', '## Definitions and scope', '',
            'Uses [the agreed revenue definition](metrics.md): known-price lines from completed orders, '
            'quantity × historical unit price − line discount, excluding shipping. No prices are estimated. '
            'Revenue is calculated in integer cents and grouped by UTC order placement date and final status. '
            'Canceled and returned orders are excluded. Products and categories are joined by product ID.', '',
            'Category share = category known-price revenue ÷ total known-price revenue for the same period. '
            'Monthly shares use each month’s total; annual shares use each year’s total. '
            'Missing prices may affect the revenue ranking and mix. Line coverage is record coverage, '
            'not the percentage of dollar revenue captured. Product quantities include completed units '
            'even when their selling price is missing. Rankings use product ID to keep names distinct; '
            'ties are ordered by numeric product ID, with exactly ten products shown.', '',
            '## Observations', ''] + [f'- {f}' for f in findings]
    text += ['', '## Category revenue by year', '', '![Category revenue](figures/category_revenue.png)', '',
             '| Category | 2024 revenue | 2024 share | 2025 revenue | 2025 share | YoY revenue | Share change (pp) |',
             '|---|---:|---:|---:|---:|---:|---:|---:|']
    for category in categories:
        rows = annual.loc[annual.category.eq(category)].set_index('year')
        a, b = rows.loc[2024], rows.loc[2025]
        growth = f'{(int(b.revenue_cents) / int(a.revenue_cents) - 1):+.2%}' if a.revenue_cents else 'N/A'
        text.append(f'| {category} | ${Decimal(dollars(a.revenue_cents)):,.2f} | {a.revenue_share:.2%} | '
                    f'${Decimal(dollars(b.revenue_cents)):,.2f} | {b.revenue_share:.2%} | {growth} | '
                    f'{(b.revenue_share - a.revenue_share) * 100:+.2f} |')
    text += ['', '### Category price coverage', '',
             '| Year | Category | Completed lines | Missing-price lines | Missing-price units | Line coverage |',
             '|---|---|---:|---:|---:|---:|']
    for row in annual.itertuples():
        text.append(f'| {row.year} | {row.category} | {row.completed_lines:,} | {row.missing_price_lines:,} | '
                    f'{row.missing_price_units:,} | {row.line_price_coverage:.2%} |')
    text += ['', '## Top 10 products by completed quantity', '', '![Top products](figures/top_products.png)', '',
             '| Rank | Product ID | Product | Category | Units |', '|---:|---|---|---|---:|']
    for row in products.head(10).itertuples():
        text.append(f'| {row.rank} | {row.product_id} | {row.product_name} | {row.category} | {row.completed_units:,} |')
    text += ['', '## Monthly category revenue mix', '', '![Monthly category mix](figures/monthly_category_mix.png)', '',
             'Both panels use January–December, the same category colors and stack order, and a 0–100% scale. '
             'Each bar describes composition; see [monthly revenue](monthly_revenue.md) for total dollar changes. '
             'These are revenue shares, not quantity shares. A share change alone does not establish a change '
             'in customer preferences or its cause.', '',
             '| Category | 2024 lowest / highest monthly share | 2025 lowest / highest monthly share |',
             '|---|---|---|']
    for category in categories:
        cells = []
        for year in (2024, 2025):
            group = monthly.loc[monthly.category.eq(category) & monthly.year.eq(year)]
            low, high = group.loc[group.revenue_share.idxmin()], group.loc[group.revenue_share.idxmax()]
            cells.append(f'{calendar.month_abbr[low.month_number]} {low.revenue_share:.2%} / '
                         f'{calendar.month_abbr[high.month_number]} {high.revenue_share:.2%}')
        text.append(f'| {category} | ' + ' | '.join(cells) + ' |')
    text += ['', '## Reproduction and validation', '',
             'Run `.\\.venv\\Scripts\\python.exe scripts\\analyze_categories.py` after points 1–3. '
             'Section 4 of the notebook runs the same script and displays its outputs.', '', validation, '',
             'Aggregate exports: category_revenue_annual.csv, category_revenue_overall.csv, '
             'monthly_category_mix.csv, product_rankings.csv and category_results.json. '
             'Shares/coverage in CSV and JSON are fractions (0.10 means 10%). '
             'Missing-only revenue remains unknown; an absent category/month receives zero revenue and units '
             'and undefined line coverage. Detailed records stay under ignored data/. '
             'Category outcomes and the final summary remain separate later steps.', '']
    (reports / 'category_analysis.md').write_text('\n'.join(text), encoding='utf-8')
    print('\n'.join(findings))
    print(validation)


if __name__ == '__main__':
    main()
