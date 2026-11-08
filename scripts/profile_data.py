"""Read-only source audit. Run from any directory with the project Python environment."""
from pathlib import Path
import csv
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports'
NAMES = ['orders', 'order_items', 'products']


def main():
    OUT.mkdir(exist_ok=True)
    raw, frames, profiles = {}, {}, {}
    lines = ['# CSV data profile', '', 'Scope: orders, order_items and products. Customer data is outside the project scope.',
             'All checks are observational. No source values have been changed or records excluded.',
             'Blank means empty or whitespace-only. Literal null markers are reported separately. IDs remain text.', '']
    for name in NAMES:
        path = ROOT / 'data' / f'{name}.csv'
        content = path.read_bytes()
        text = content.decode('utf-8-sig')
        records = list(csv.reader(text.splitlines()))
        header = records[0]
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        raw[name] = df
        frames[name] = pd.read_csv(path, dtype={c: str for c in df.columns if c.endswith('_id')})
        profile = {'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content),
                   'rows': len(df), 'columns': header, 'encoding': 'UTF-8 compatible',
                   'delimiter': ',', 'malformed_row_widths': sum(len(r) != len(header) for r in records[1:]),
                   'duplicate_headers': len(header) - len(set(header)),
                   'exact_duplicate_excess_rows': int(df.duplicated().sum()), 'fields': {}}
        lines += [f'## {name}.csv', '', f'{len(df):,} rows; {len(header)} columns; {profile["exact_duplicate_excess_rows"]:,} excess exact duplicate rows.',
                  f'SHA-256: `{profile["sha256"]}`', '',
                  '| Column | Inferred type | Blank | Distinct nonblank | Range / values |', '|---|---|---:|---:|---|']
        for col in df:
            s = df[col]
            present = s[s.str.strip().ne('')]
            num = pd.to_numeric(present, errors='coerce')
            info = {'inferred_type': str(frames[name][col].dtype), 'blank': int(len(s)-len(present)),
                    'distinct_nonblank': int(present.nunique()), 'surrounding_whitespace': int(s.ne(s.str.strip()).sum()),
                    'literal_null_markers': present[present.str.lower().isin(['null', 'none', 'nan', 'n/a', 'na'])].value_counts().to_dict()}
            if len(present) and num.notna().all() and not col.endswith('_id'):
                info.update(min=float(num.min()), max=float(num.max()), negative=int(num.lt(0).sum()),
                            zero=int(num.eq(0).sum()), non_integer=int(num.mod(1).ne(0).sum()),
                            quantiles={str(k): float(v) for k,v in num.quantile([.01,.25,.5,.75,.99]).items()})
                summary = f'{num.min():g} to {num.max():g}; negative={info["negative"]}; zero={info["zero"]}'
            elif 'date' in col:
                dates = pd.to_datetime(present, format='%Y-%m-%d %H:%M:%S', errors='coerce')
                info.update(invalid_dates=int(dates.isna().sum()), earliest=str(dates.min()), latest=str(dates.max()),
                            monthly_counts=dates.dt.strftime('%Y-%m').value_counts().sort_index().to_dict())
                summary = f'{dates.min()} to {dates.max()}; invalid={info["invalid_dates"]}'
            else:
                # Customer IDs are only profiled in aggregate; never export samples.
                info['top_values'] = {} if col == 'customer_id' else present.value_counts().head(15).to_dict()
                normalized = present.str.strip().str.casefold()
                info['normalization_collisions'] = {k: sorted(set(present[normalized.eq(k)])) for k in normalized.unique()
                                                   if present[normalized.eq(k)].nunique() > 1} if present.nunique() < 200 else {}
                summary = ', '.join(f'{k} ({v})' for k,v in info['top_values'].items()) if present.nunique() <= 15 else 'High cardinality; see JSON profile'
            profile['fields'][col] = info
            lines.append(f'| {col} | {"text identifier" if col.endswith("_id") else info["inferred_type"]} | {info["blank"]} | {info["distinct_nonblank"]} | {summary} |')
        profiles[name] = profile
        lines += ['', f'Malformed row widths: {profile["malformed_row_widths"]}; duplicate headers: {profile["duplicate_headers"]}.', '']

    o, i, p = (raw[n] for n in NAMES)
    joins = {}
    for label, parent, child, key in [('orders_to_items', o, i, 'order_id'), ('products_to_items', p, i, 'product_id')]:
        counts = parent[key].value_counts()
        joins[label] = {'parent_duplicate_key_excess': int(parent.duplicated(key).sum()),
                        'parent_blank_keys': int(parent[key].str.strip().eq('').sum()),
                        'child_blank_keys': int(child[key].str.strip().eq('').sum()),
                        'unmatched_child_rows': int((~child[key].isin(parent[key])).sum()),
                        'unmatched_child_ids': sorted(set(child[key])-set(parent[key])),
                        'unused_parent_rows': int((~parent[key].isin(child[key])).sum()),
                        'unused_parent_ids': sorted(set(parent[key])-set(child[key])),
                        'child_rows_before': len(child),
                        'left_join_rows_after': int(child[key].map(counts).fillna(1).sum())}
    lines += ['## Identifier and join checks', '', '```json', json.dumps(joins, indent=2), '```', '',
              'Order items have no line ID. A repeated order ID is expected for multi-line orders. Exact duplicate lines and repeated order/product pairs require review before deletion.', '']
    pairs = i.groupby(['order_id','product_id']).size()
    diagnostics = {'repeated_order_product_pairs': int(pairs.gt(1).sum()),
                   'rows_in_repeated_pairs': int(pairs[pairs.gt(1)].sum()),
                   'exact_duplicate_item_rows_including_first': int(i.duplicated(keep=False).sum())}
    order_view = frames['orders'].drop_duplicates()
    assert order_view.order_id.is_unique, 'Conflicting order records need investigation'
    merged = frames['order_items'].merge(frames['products'], on='product_id', how='left', validate='many_to_one').merge(
        order_view, on='order_id', how='left', validate='many_to_one')
    missing = merged['unit_price'].isna()
    known = merged[~missing]
    price_groups = known.groupby('product_id')['unit_price'].agg(['count','nunique','min','max'])
    missing_detail = merged[missing].copy()
    missing_detail['source_csv_row'] = missing_detail.index + 2
    for col in ['count','nunique','min','max']:
        missing_detail[f'known_product_price_{col}'] = missing_detail['product_id'].map(price_groups[col])
    diagnostics.update(missing_unit_price_rows=int(missing.sum()),
                       missing_price_quantity=float(merged.loc[missing,'quantity'].sum()),
                       missing_prices_by_status=merged.loc[missing,'status'].value_counts(dropna=False).to_dict(),
                       missing_prices_by_month=merged.loc[missing,'order_date'].str[:7].value_counts().sort_index().to_dict(),
                       missing_prices_by_product=merged.loc[missing,'product_id'].value_counts().to_dict(),
                       missing_prices_by_category=merged.loc[missing,'category'].value_counts().to_dict(),
                       known_prices_different_from_list=int((known.unit_price.round(2) != known.list_price.round(2)).sum()),
                       products_with_multiple_transaction_prices=int(price_groups['nunique'].gt(1).sum()),
                       nonpositive_quantity=int(merged.quantity.le(0).sum()),
                       fractional_quantity=int(merged.quantity.mod(1).ne(0).sum()),
                       discount_above_known_line_gross=int((merged.discount_amount > merged.quantity*merged.unit_price).sum()),
                       negative_known_line_net=int((merged.quantity*merged.unit_price-merged.discount_amount).lt(0).sum()),
                       unit_cost_above_list_price=int((frames['products'].unit_cost > frames['products'].list_price).sum()))
    for label, group in [('status', merged.status), ('month', merged.order_date.str[:7]),
                         ('category_normalized', merged.category.str.strip().str.casefold())]:
        rates = pd.DataFrame({'group': group, 'missing': missing}).groupby('group')['missing'].agg(['sum', 'count', 'mean'])
        diagnostics[f'missing_price_rates_by_{label}'] = rates.to_dict(orient='index')
    category_map = p[['category']].drop_duplicates().copy()
    category_map['proposed_category'] = category_map.category.str.strip().str.title()
    category_map['product_count'] = category_map.category.map(p.category.value_counts())
    lines += ['## Category label mapping proposed for review', '', '| Original label (quoted to expose spaces) | Proposed label | Products |', '|---|---|---:|']
    lines += [f'| `{r.category}` | {r.proposed_category} | {r.product_count} |' for r in category_map.itertuples()]
    lines += ['']
    lines += ['## Missing-price investigation and business-rule checks', '', '```json', json.dumps(diagnostics, indent=2), '```', '',
              'For missing-price diagnostics only, the order lookup collapses exact duplicate order records in memory; conflicting order IDs would stop the audit. Source item rows remain intact. The raw join inflation is reported above.',
              'The record-level investigation is saved under data/profile/ (ignored by Git). Product-level observed prices are evidence, not proof of the missing transaction price. Current list price may differ from the historical price.', '',
              '## Proposed cleaning rules', '',
              '1. Preserve source CSVs; record hashes above identify the audited versions. Parse dates explicitly and keep identifiers as text in prepared data.',
              '2. Treat blank discount codes as “no code recorded”; do not assume a zero discount from this field alone. Use discount_amount for the recorded line discount (project README definition).',
              '3. Review exact duplicate item rows against their order/product keys. There is no line identifier to establish whether identical lines are accidental duplicates.',
              '4. Retain missing prices while investigating. Do not substitute list price or a product average automatically. Revenue calculations must report the affected rows and coverage until a rule is adopted.',
              '5. Review negative/zero values, label collisions and join failures reported above. Outlying values alone do not establish errors.',
              '6. Define eligible order statuses and revenue separately before sales analysis. Returned/cancelled orders must not silently enter completed-sales revenue.', '',
              'No cleaning corrections or exclusions have been applied. See cleaning_log.md for the audit and proposed decisions.']
    detaildir = ROOT / 'data' / 'profile'
    detaildir.mkdir(exist_ok=True)
    missing_detail.to_csv(detaildir / 'missing_price_investigation.csv', index=False)
    i[i.duplicated(keep=False)].to_csv(detaildir / 'duplicate_item_candidates.csv', index=False)
    o.assign(source_csv_row=range(2,len(o)+2)).loc[o.duplicated(keep=False)].to_csv(detaildir / 'duplicate_order_candidates.csv', index=False)
    (OUT/'data_profile.json').write_text(json.dumps({'files': profiles, 'joins': joins, 'diagnostics': diagnostics}, indent=2), encoding='utf-8')
    (OUT/'data_profile.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    for name in NAMES:
        assert hashlib.sha256((ROOT/'data'/f'{name}.csv').read_bytes()).hexdigest() == profiles[name]['sha256']
    print(json.dumps({'rows': {n:len(raw[n]) for n in NAMES}, 'joins': joins, 'diagnostics': diagnostics}, indent=2))


if __name__ == '__main__':
    main()
