import json, pathlib

CELLS = []

def md(src):
    CELLS.append({"cell_type":"markdown","metadata":{},"source":[src]})

def code(src):
    CELLS.append({"cell_type":"code","execution_count":None,"metadata":{},"outputs":[],"source":[src]})

md("# 10_pivot_detail.ipynb\nFor each flagged segment, produce a year×month pivot table showing qty and net_sales by New Bucket.\nHelps analyst verify granularity before deciding on threshold fine-tuning.")

code("""import pandas as pd
import numpy as np
import os, sys, pickle, warnings
warnings.filterwarnings('ignore')

_src_path = os.path.abspath(os.path.join(os.getcwd(), '..', 'src'))
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
from channel_registry import get_channel

CHANNELS   = ['TT', 'EC', 'MT']
FOCUS_DIVS = ['HL', 'SL', 'BP']

# Load diagnostic CSV to know which segments need attention
DIAG_CSV = 'data/outputs/09_threshold_diagnostic.csv'
if not os.path.exists(DIAG_CSV):
    raise FileNotFoundError(f'Run NB09 first: {DIAG_CSV} not found')

diag = pd.read_csv(DIAG_CSV)
print(f'Diagnostic loaded: {len(diag)} rows')
print(f'Flagged: {diag[\"needs_tuning\"].sum()}')
""")

code("""def _mean_series(pivot, group):
    valid = [b for b in group if b in pivot.index]
    return pivot.loc[valid].mean(axis=0) if valid else pd.Series(0.0, index=pivot.columns)

def _merge_cost(pivot, g1, g2):
    s1, s2 = _mean_series(pivot, g1), _mean_series(pivot, g2)
    if s1.std() < 1e-9 or s2.std() < 1e-9:
        return 1.0
    return (1.0 - float(np.corrcoef(s1.values, s2.values)[0, 1])) / 2.0

def cluster_auto(pivot, seg_vol, cfg, thr=None):
    MIN_H  = cfg['min_history_months']
    NOISE  = cfg['noise_floor_pct']
    MAX_K  = cfg['max_k']
    THRESH = thr if thr is not None else cfg['trend_similarity_threshold']
    total  = seg_vol.sum()
    if total == 0:
        return {b: 1 for b in pivot.index}
    months_active = (pivot > 0).sum(axis=1)
    active = sorted([b for b in pivot.index
                     if months_active[b] >= MIN_H
                     and seg_vol.get(b, 0) / total >= NOISE])
    if not active:
        active = sorted(pivot.index.tolist())
    if len(active) == 1:
        return {b: 1 for b in range(0, int(max(seg_vol.index))+100, 100)}
    working = [[b] for b in active]
    cost_seq, k_seq = [], [len(working)]
    while len(working) > 1:
        costs = [_merge_cost(pivot, working[i], working[i+1]) for i in range(len(working)-1)]
        best  = int(np.argmin(costs))
        cost_seq.append(costs[best])
        working[best] = working[best] + working[best+1]
        del working[best+1]
        k_seq.append(len(working))
    costs_arr  = np.array(cost_seq)
    total_cost = costs_arr.sum()
    chosen_k   = 1
    if total_cost > 0:
        for i, cs in enumerate(np.cumsum(costs_arr)):
            if cs / total_cost >= THRESH:
                chosen_k = k_seq[i+1]
                break
    chosen_k = max(2, min(chosen_k, MAX_K, len(active)))
    groups = [[b] for b in active]
    while len(groups) > chosen_k:
        costs = [_merge_cost(pivot, groups[i], groups[i+1]) for i in range(len(groups)-1)]
        best  = int(np.argmin(costs))
        groups[best] = groups[best] + groups[best+1]
        del groups[best+1]
    nb_map   = {b: nb for nb, g in enumerate(groups, 1) for b in g}
    max_b    = int(max(seg_vol.index))
    a_sorted = sorted(nb_map)
    final    = {}
    for b in range(0, max_b+100, 100):
        final[b] = nb_map[b] if b in nb_map else nb_map[min(a_sorted, key=lambda x: abs(x-b))]
    seen = []
    for b in sorted(final):
        if final[b] not in seen: seen.append(final[b])
    remap = {old: new+1 for new, old in enumerate(seen)}
    return {b: remap[c] for b, c in final.items()}

print('Clustering helpers ready.')
""")

code("""channel_data = {}
for CH in CHANNELS:
    cfg = get_channel(CH)
    pkl = os.path.join(cfg['out_path'], '03_segment_pivots.pkl')
    bts = os.path.join(cfg['out_path'], '02_fine_bucket_ts.csv')
    abt = os.path.join(cfg['out_path'], '07_analytical_base_table.csv')
    if not os.path.exists(pkl):
        print(f'[{CH}] SKIP - no pkl')
        continue
    with open(pkl, 'rb') as f:
        pivots = pickle.load(f)
    bucket_ts = pd.read_csv(bts)
    # Try to load ABT for net_sales; fall back to bucket_ts only
    if os.path.exists(abt):
        abt_df = pd.read_csv(abt)
        abt_df['year']  = pd.to_datetime(abt_df['sale_date']).dt.year
        abt_df['month'] = pd.to_datetime(abt_df['sale_date']).dt.month
    else:
        abt_df = None
        print(f'[{CH}] Note: ABT not found, net_sales will be omitted')
    channel_data[CH] = {'pivots': pivots, 'bucket_ts': bucket_ts, 'abt': abt_df, 'cfg': cfg}
    print(f'[{CH}] loaded {len(pivots)} segments')
print('Available:', list(channel_data.keys()))
""")

code("""def make_pivot_detail(seg_key, channel, threshold_override=None):
    \"\"\"
    For a single segment, build two pivot tables:
      1. qty  pivot: rows=New_Bucket, cols=(year, month)
      2. ns   pivot: rows=New_Bucket, cols=(year, month)  [if ABT available]
    Also builds a 'vol_pct' version of qty pivot.
    Returns dict of DataFrames.
    \"\"\"
    if channel not in channel_data:
        return None
    d       = channel_data[channel]
    pivots  = d['pivots']
    bts     = d['bucket_ts']
    abt     = d['abt']
    cfg     = d['cfg']

    if seg_key not in pivots:
        return None

    info = pivots[seg_key]
    pivot_matrix = info['pivot']
    div, portal, size = info['div'], info['portal'], info['size']

    # Segment volume
    seg_vol = (bts[(bts['Division']==div) &
                   (bts['Portal']==portal) &
                   (bts['Size']==size)]
               .groupby('bucket_min')['qty'].sum())

    # Cluster at chosen threshold
    thr    = threshold_override if threshold_override is not None \
             else cfg['trend_similarity_threshold']
    nb_map = cluster_auto(pivot_matrix, seg_vol, cfg, thr)

    # Attach NB to bucket_ts rows
    seg_bts = bts[(bts['Division']==div) &
                  (bts['Portal']==portal) &
                  (bts['Size']==size)].copy()
    seg_bts['sale_date'] = pd.to_datetime(seg_bts['sale_date'])
    seg_bts['year']  = seg_bts['sale_date'].dt.year
    seg_bts['month'] = seg_bts['sale_date'].dt.month
    seg_bts['New_Bucket'] = seg_bts['bucket_min'].map(nb_map)
    seg_bts = seg_bts.dropna(subset=['New_Bucket'])
    seg_bts['New_Bucket'] = seg_bts['New_Bucket'].astype(int)

    if seg_bts.empty:
        return None

    k = len(set(nb_map.values()))

    # ── Qty pivot: rows=NB, cols=(year,month) ──────────────────────────
    qty_grp = (seg_bts.groupby(['New_Bucket','year','month'])['qty']
               .sum().reset_index())
    qty_pivot = qty_grp.pivot_table(index='New_Bucket',
                                    columns=['year','month'],
                                    values='qty',
                                    aggfunc='sum',
                                    fill_value=0)
    qty_pivot.columns = [f'{y}-{m:02d}' for y, m in qty_pivot.columns]
    qty_pivot['TOTAL_QTY'] = qty_pivot.sum(axis=1)
    qty_pivot['VOL_PCT']   = (100 * qty_pivot['TOTAL_QTY'] /
                               qty_pivot['TOTAL_QTY'].sum()).round(1)

    # Also add price range per NB
    price_ranges = {}
    for b, nb in nb_map.items():
        price_ranges.setdefault(nb, []).append(b)
    qty_pivot.insert(0, 'price_range',
                     qty_pivot.index.map(
                         lambda nb: f\"{min(price_ranges.get(nb,[0]))}-{max(price_ranges.get(nb,[0]))+99}\"
                     ))

    results = {'qty': qty_pivot, 'k': k, 'threshold': thr}

    # ── Net sales pivot from ABT ────────────────────────────────────────
    if abt is not None:
        seg_abt = abt[(abt['Division']==div) &
                      (abt['Portal']==portal) &
                      (abt['Size']==size)].copy()
        if not seg_abt.empty and 'New_Bucket' in seg_abt.columns:
            ns_grp = (seg_abt.groupby(['New_Bucket','year','month'])['net_sales']
                      .sum().reset_index())
            ns_pivot = ns_grp.pivot_table(index='New_Bucket',
                                          columns=['year','month'],
                                          values='net_sales',
                                          aggfunc='sum',
                                          fill_value=0)
            ns_pivot.columns = [f'{y}-{m:02d}' for y, m in ns_pivot.columns]
            ns_pivot['TOTAL_NS'] = ns_pivot.sum(axis=1)
            results['ns'] = ns_pivot

    return results

print('Pivot detail function ready.')
""")

code("""# ── Determine output directory ─────────────────────────────────────────────
if 'EC' in channel_data:
    BASE_OUT = channel_data['EC']['cfg']['out_path'].replace('EC/', '')
elif channel_data:
    BASE_OUT = list(channel_data.values())[0]['cfg']['out_path']
else:
    BASE_OUT = 'data/outputs/'

PIVOT_DIR = os.path.join(BASE_OUT, '10_pivot_detail')
os.makedirs(PIVOT_DIR, exist_ok=True)
print(f'Output dir: {os.path.abspath(PIVOT_DIR)}')

# ── Determine threshold per segment ────────────────────────────────────────
# Segments with k_diff_60 >= 2 AND total_vol > 10000 get threshold = 0.60
# Everything else stays at 0.70
threshold_map = {}
for _, row in diag.iterrows():
    if row['k_diff_60'] >= 2 and row['total_vol'] > 10000:
        threshold_map[row['seg_key']] = 0.60
    else:
        threshold_map[row['seg_key']] = 0.70

tuned = [k for k, v in threshold_map.items() if v == 0.60]
print(f'Segments using threshold=0.60: {len(tuned)}')
print(f'Segments using threshold=0.70: {len(threshold_map)-len(tuned)}')
""")

code("""# ── Generate pivot CSVs for ALL flagged segments ──────────────────────────
# One Excel file per segment with two sheets: Qty and NS
# Also writes a master summary Excel

from io import BytesIO
try:
    import openpyxl
    USE_EXCEL = True
except ImportError:
    USE_EXCEL = False
    print('openpyxl not found - writing CSV only')

saved = []
skipped = []

for _, row in diag[diag['needs_tuning'] == True].iterrows():
    CH      = row['channel']
    seg_key = row['seg_key']
    div     = row['Division']

    if div not in FOCUS_DIVS:
        continue
    if CH not in channel_data:
        continue

    thr = threshold_map.get(seg_key, 0.70)
    res = make_pivot_detail(seg_key, CH, threshold_override=thr)

    if res is None:
        skipped.append(seg_key)
        continue

    qty_piv = res['qty']
    k       = res['k']

    if USE_EXCEL:
        fname = os.path.join(PIVOT_DIR, f'{seg_key}_pivot_detail.xlsx')
        with pd.ExcelWriter(fname, engine='openpyxl') as writer:
            qty_piv.to_excel(writer, sheet_name=f'QTY_K{k}_thr{int(thr*100)}')
            if 'ns' in res:
                res['ns'].to_excel(writer, sheet_name=f'NS_K{k}_thr{int(thr*100)}')
            # Add a metadata sheet
            meta = pd.DataFrame([{
                'seg_key': seg_key, 'channel': CH, 'Division': div,
                'Portal': row['Portal'], 'Size': row['Size'],
                'total_vol': row['total_vol'],
                'k_at_070': row['k_at_070'], 'k_at_060': row['k_at_060'],
                'threshold_used': thr, 'k_produced': k,
                'flagged_details': row['flagged_details']
            }])
            meta.to_excel(writer, sheet_name='INFO', index=False)
    else:
        fname = os.path.join(PIVOT_DIR, f'{seg_key}_qty_pivot.csv')
        qty_piv.to_csv(fname)
        if 'ns' in res:
            res['ns'].to_csv(os.path.join(PIVOT_DIR, f'{seg_key}_ns_pivot.csv'))

    saved.append(seg_key)
    print(f'  {seg_key:<35} K={k}  thr={thr}  {"XLSX" if USE_EXCEL else "CSV"}')

print(f'\\nSaved: {len(saved)}  |  Skipped: {len(skipped)}')
print(f'Output: {os.path.abspath(PIVOT_DIR)}')
if skipped:
    print(f'Skipped segments: {skipped}')
""")

code("""# ── Master summary: one row per NB per segment ─────────────────────────────
# Useful for quick cross-segment comparison

master_rows = []

for _, row in diag[diag['needs_tuning'] == True].iterrows():
    CH      = row['channel']
    seg_key = row['seg_key']
    div     = row['Division']

    if div not in FOCUS_DIVS or CH not in channel_data:
        continue

    thr = threshold_map.get(seg_key, 0.70)
    res = make_pivot_detail(seg_key, CH, threshold_override=thr)
    if res is None:
        continue

    qty_piv = res['qty']
    for nb in qty_piv.index:
        master_rows.append({
            'channel':        CH,
            'seg_key':        seg_key,
            'Division':       row['Division'],
            'Portal':         row['Portal'],
            'Size':           row['Size'],
            'New_Bucket':     nb,
            'price_range':    qty_piv.loc[nb, 'price_range'],
            'total_qty':      qty_piv.loc[nb, 'TOTAL_QTY'],
            'vol_pct':        qty_piv.loc[nb, 'VOL_PCT'],
            'threshold_used': thr,
            'k_produced':     res['k'],
            'k_at_070':       row['k_at_070'],
            'k_diff_60':      row['k_diff_60'],
        })

df_master = pd.DataFrame(master_rows)
master_path = os.path.join(PIVOT_DIR, '10_master_nb_summary.csv')
df_master.to_csv(master_path, index=False)
print(f'Master summary saved: {os.path.abspath(master_path)}')
print(f'Rows: {len(df_master)}  |  Segments: {df_master["seg_key"].nunique()}')
print()
print(df_master.groupby(['channel','Division'])['seg_key'].nunique().rename('segments'))
""")

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name":"Python 3","language":"python","name":"python3"},
        "language_info": {"name":"python","version":"3.10.0"}
    },
    "cells": CELLS
}

out = pathlib.Path('../notebooks/10_pivot_detail.ipynb')
out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding='utf-8')
print(f'Written: {out}  ({len(CELLS)} cells)')

nb2 = json.loads(out.read_text(encoding='utf-8'))
for i, cell in enumerate(nb2['cells']):
    if cell['cell_type'] == 'code':
        src = ''.join(cell['source'])
        print(f'  Code cell {i}: {"BAD" if "null" in src else "OK"} ({len(src)} chars)')