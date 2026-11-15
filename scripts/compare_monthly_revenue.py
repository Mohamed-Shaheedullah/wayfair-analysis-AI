"""Point 3: monthly comparison, coverage, reconciliation and one revenue chart."""
import calendar
from decimal import Decimal, ROUND_HALF_UP
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd

from calculate_metrics import ROOT, prepare_orders, require, summarize


MONEY = ('known_price_merchandise_revenue_usd', 'completed_shipping_income_usd',
         'fully_priced_completed_order_revenue_usd')
COUNTS = ('all_orders', 'completed_orders', 'canceled_orders', 'returned_orders',
          'completed_units_sold', 'completed_item_lines', 'completed_known_price_lines',
          'completed_missing_price_lines', 'completed_missing_price_units',
          'completed_orders_with_all_prices', 'completed_orders_with_missing_prices')


def change(current, previous):
    """A zero base has no defined percentage change."""
    return float((Decimal(str(current)) / Decimal(str(previous))) - 1) if Decimal(str(previous)) else None


def reconcile(records, expected):
    for key in COUNTS:
        require(sum(row[key] for row in records) == expected[key], f'Count reconciliation: {key}')
    for key in MONEY:
        require(sum(Decimal(row[key]) for row in records) == Decimal(expected[key]),
                f'Money reconciliation: {key}')
    # Recompute AOV from its components, never from the mean of monthly AOVs.
    numerator = sum(Decimal(row['fully_priced_completed_order_revenue_usd']) for row in records)
    denominator = sum(row['completed_orders_with_all_prices'] for row in records)
    aov = str((numerator / denominator).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)) if denominator else None
    require(aov == expected['aov_fully_priced_completed_orders_usd'], 'AOV reconciliation')


def main():
    orders, _, hashes = prepare_orders()
    baseline = json.loads((ROOT / 'reports/metrics_results.json').read_text(encoding='utf-8'))
    require(hashes == baseline['cleaned_sha256'], 'Initial results use different inputs.')
    require(summarize(orders) == baseline['overall'], 'Initial overall metrics changed.')

    dates = orders.order_date
    require(dates.min() >= pd.Timestamp('2024-01-01', tz='UTC') and
            dates.max() < pd.Timestamp('2026-01-01', tz='UTC'), 'Unexpected date range.')
    orders['month'] = dates.dt.strftime('%Y-%m')
    expected_months = pd.period_range('2024-01', '2025-12', freq='M').astype(str).tolist()
    require(sorted(orders.month.unique()) == expected_months, 'Missing or unexpected months.')

    monthly = {}
    coverage = []
    for month, group in orders.groupby('month', sort=True):
        monthly[month] = summarize(group)
        year, number = map(int, month.split('-'))
        calendar_days = calendar.monthrange(year, number)[1]
        observed_days = group.order_date.dt.normalize().nunique()
        coverage.append(dict(month=month, first_order_utc=group.order_date.min().isoformat(),
                             last_order_utc=group.order_date.max().isoformat(),
                             calendar_days=calendar_days, observed_order_days=int(observed_days),
                             days_without_recorded_orders=calendar_days-int(observed_days)))

    for year in ('2024', '2025'):
        expected = baseline['annual'][year]
        require(summarize(orders.loc[orders.year.eq(int(year))]) == expected, 'Annual baseline changed.')
        reconcile([record for month, record in monthly.items() if month.startswith(year)], expected)
    reconcile(list(monthly.values()), baseline['overall'])

    comparison = []
    for number in range(1, 13):
        previous = monthly[f'2024-{number:02}']
        current = monthly[f'2025-{number:02}']
        row = {'month_number': number, 'month': calendar.month_abbr[number]}
        for label, key in [('revenue', 'known_price_merchandise_revenue_usd'),
                           ('completed_orders', 'completed_orders'),
                           ('aov', 'aov_fully_priced_completed_orders_usd')]:
            for year, record in [('2024', previous), ('2025', current)]:
                row[f'{label}_{year}'] = record[key]
            row[f'{label}_yoy_change'] = (format(Decimal(str(current[key])) - Decimal(str(previous[key])), 'f')
                                         if current[key] is not None and previous[key] is not None else None)
            row[f'{label}_yoy_rate'] = (change(current[key], previous[key])
                                       if current[key] is not None and previous[key] is not None else None)
        comparison.append(row)

    annual_growth = change(baseline['annual']['2025']['known_price_merchandise_revenue_usd'],
                           baseline['annual']['2024']['known_price_merchandise_revenue_usd'])
    findings = [f'Known-price merchandise revenue increased {annual_growth:.2%} from 2024 to 2025. '
                f'2025 revenue exceeded the matching 2024 month in '
                f'{sum(row["revenue_yoy_rate"] > 0 for row in comparison)} of 12 months.']
    for year in ('2024', '2025'):
        ranked = sorted(((month, row) for month, row in monthly.items() if month.startswith(year)),
                        key=lambda pair: Decimal(pair[1]['known_price_merchandise_revenue_usd']), reverse=True)
        top = ', '.join(f'{calendar.month_name[int(month[-2:])]} '
                        f'(${Decimal(row["known_price_merchandise_revenue_usd"]):,.2f})'
                        for month, row in ranked[:2])
        findings.append(f'The two highest revenue months in {year} were {top}.')
    low = min(monthly, key=lambda month: monthly[month]['completed_line_price_coverage'])
    high = max(monthly, key=lambda month: monthly[month]['completed_line_price_coverage'])
    findings.append(f'Completed-line price coverage ranged from '
                    f'{monthly[low]["completed_line_price_coverage"]:.2%} ({low}) to '
                    f'{monthly[high]["completed_line_price_coverage"]:.2%} ({high}). '
                    'These are record coverage rates, not percentages of revenue captured; '
                    'unknown selling prices could affect the comparisons.')
    peaks = [{month[-2:] for month, _ in sorted(
        ((m, r) for m, r in monthly.items() if m.startswith(year)),
        key=lambda pair: Decimal(pair[1]['known_price_merchandise_revenue_usd']), reverse=True)[:2]}
        for year in ('2024', '2025')]
    recurring = sorted(peaks[0] & peaks[1])
    findings.append(('Both years place ' + ', '.join(calendar.month_name[int(m)] for m in recurring)
                     + ' among their two highest revenue months. This suggests a recurring peak, '
                     'but two years cannot establish a stable seasonal pattern or its cause.') if recurring else
                    'The two highest revenue months differ between years; two years are insufficient '
                    'to establish a stable seasonal pattern.')

    figures = ROOT / 'reports/figures'
    figures.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(10.5, 6))
    fig.subplots_adjust(left=0.12, right=0.97, top=0.81, bottom=0.23)
    for year, color, marker in [('2024', '#2563a6', 'o'), ('2025', '#b54920', 's')]:
        ax.plot(range(1, 13), [float(monthly[f'{year}-{m:02}']['known_price_merchandise_revenue_usd'])
                              for m in range(1, 13)], label=year, color=color, marker=marker, linewidth=2)
    ax.set_xticks(range(1, 13), list(calendar.month_abbr)[1:])
    ax.set_xlim(0.7, 12.3)
    ax.set_ylim(bottom=0)
    ax.set_xlabel('Order month (UTC)')
    ax.set_ylabel('Known-price merchandise revenue (USD)')
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f'${value / 1000:,.0f}k'))
    ax.grid(axis='y', alpha=0.2)
    ax.spines[['top', 'right']].set_visible(False)
    ax.legend(frameon=False, title='Order year')
    fig.suptitle('Monthly merchandise revenue: 2024 vs 2025', x=0.12, ha='left', fontsize=17, weight='bold')
    fig.text(0.12, 0.87, 'Completed orders · after line discounts · shipping excluded', fontsize=11, color='#444444')
    excluded = {year: baseline['annual'][year]['completed_missing_price_lines'] for year in ('2024', '2025')}
    fig.text(0.12, 0.09, f'Missing-price lines excluded: {excluded["2024"]} in 2024; '
             f'{excluded["2025"]} in 2025. No prices estimated.\n'
             'Source: cleaned project data. Final order status, grouped by order placement date.',
             fontsize=9, color='#444444', linespacing=1.6)
    fig.savefig(figures / 'monthly_revenue.png', dpi=180)
    plt.close(fig)

    reports = ROOT / 'reports'
    pd.DataFrame.from_dict(monthly, orient='index').rename_axis('month').to_csv(reports / 'monthly_metrics.csv')
    pd.DataFrame(comparison).to_csv(reports / 'monthly_yoy.csv', index=False)
    pd.DataFrame(coverage).to_csv(reports / 'monthly_date_coverage.csv', index=False)
    result = dict(cleaned_sha256=hashes, overall=baseline['overall'], annual=baseline['annual'],
                  monthly=monthly, yoy=comparison, date_coverage=coverage, findings=findings,
                  validation='Passed: input hashes, 24 months present, unchanged overall/annual baselines, '
                             'monthly-to-annual and overall counts, exact money and AOV reconciliation.')
    (reports / 'monthly_results.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    missing_days = sum(row['days_without_recorded_orders'] for row in coverage)
    text = ['# Monthly revenue comparison: 2024 and 2025', '', '## Scope and date coverage', '',
            'Uses the definitions in [metrics.md](metrics.md). Revenue includes known-price completed lines; '
            'AOV uses only completed orders with every line priced. Shipping is separate. '
            'Missing prices are not estimated. All periods use UTC order dates and final recorded status.', '',
            f'All 24 expected months are present. First order: {dates.min().isoformat()}; '
            f'last order: {dates.max().isoformat()}. There are {missing_days} calendar days without recorded orders. '
            'See monthly_date_coverage.csv for month boundaries and observed day counts. '
            'Recorded transactions across the period do not independently prove the source extract is complete. '
            'February has 29 days in 2024 and 28 in 2025; comparisons use calendar-month totals, not daily averages.', '',
            '## Observations', '']
    text += [f'- {finding}' for finding in findings]
    text += ['', '## Revenue comparison', '', '![Monthly revenue](figures/monthly_revenue.png)', '',
             '| Month | 2024 revenue | 2025 revenue | Change (USD) | YoY |', '|---|---:|---:|---:|---:|']
    for row in comparison:
        text.append(f'| {row["month"]} | ${Decimal(row["revenue_2024"]):,.2f} | '
                    f'${Decimal(row["revenue_2025"]):,.2f} | ${Decimal(row["revenue_yoy_change"]):+,.2f} | '
                    f'{row["revenue_yoy_rate"]:+.2%} |')
    text += ['', '## Order counts, AOV and price coverage', '',
             'The AOV population is the fully priced completed-order count. Completed orders include those '
             'with missing prices. Revenue and AOV therefore use different, explicitly labelled populations.', '',
             '| Month | Completed orders | Fully priced orders | AOV (USD) | Missing-price lines | Line coverage | Order coverage |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for month, row in monthly.items():
        text.append(f'| {month} | {row["completed_orders"]:,} | {row["completed_orders_with_all_prices"]:,} | '
                    f'${Decimal(row["aov_fully_priced_completed_orders_usd"]):,.2f} | '
                    f'{row["completed_missing_price_lines"]} | {row["completed_line_price_coverage"]:.2%} | '
                    f'{row["completed_order_price_coverage"]:.2%} |')
    text += ['', '## Reproduction and validation', '',
             'Run `.\\.venv\\Scripts\\python.exe scripts\\compare_monthly_revenue.py`. '
             'This reads validated cleaned inputs and compares against reports/metrics_results.json; '
             'run scripts/calculate_metrics.py first if reproducing the project from scratch.', '',
             result['validation'], '',
             'Monthly metrics, year-over-year changes (including order counts and AOV), date coverage and '
             'machine-readable validation are saved in reports/monthly_metrics.csv, monthly_yoy.csv, '
             'monthly_date_coverage.csv and monthly_results.json. Rate fields in CSV/JSON are fractions '
             '(0.10 means 10%); YoY is (2025 / 2024) - 1, with an undefined zero-base rate left blank. '
             'AOV is recalculated from matching revenue and order counts at each level. '
             'Source and cleaned data are unchanged. Category/product analysis and final conclusions remain later steps.', '']
    (reports / 'monthly_revenue.md').write_text('\n'.join(text), encoding='utf-8')
    print('\n'.join(findings))
    print(result['validation'])


if __name__ == '__main__':
    main()
