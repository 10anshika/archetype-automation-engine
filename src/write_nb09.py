import json, pathlib

CELLS = []

def md(src): 
    CELLS.append({"cell_type":"markdown","metadata":{},"source":[src]})

def code(src): 
    CELLS.append({"cell_type":"code","execution_count":None,"metadata":{},"outputs":[],"source":[src]})

md("# 09_threshold_diagnostic\nHL, SL, BP only (no BS/DF). Checks if threshold=0.70 creates oversized buckets.")

code("""import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pickle, sys, os, warnings
warnings.filterwarnings('ignore')

_src_path = os.path.abspath(os.path.join(os.getcwd(), '..', 'src'))
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
from channel_registry import get_channel

CHANNELS = ['TT', 'EC', 'MT']
FOCUS_DIVS = ['HL', 'SL', 'BP']
EXAMPLES_PER_DIV = 3

print('Loaded. Focus:', FOCUS_DIVS)
""")

code("""def _mean_series(pivot, group):
    valid = [b for b in group if b in pivot.index]
    return pivot.loc[valid].mean(axis=0) if valid else pd.Series(0.0, index=pivot.columns)

def _merge_cost(pivot, g1, g2):
    s1, s2 = _mean_series(pivot, g1), _mean_series(pivot, g2)
    if s1.std() < 1e-9 or s2.std() < 1e-9:
        return 1.0
    return (1.0 - float(np.corrcoef(s1.values, s2.values)[0, 1])) / 2.0

def cluster_segment_auto(pivot, seg_vol, cfg, threshold_override=None):
    MIN_HISTORY_MONTHS = cfg['min_history_months']
    NOISE_FLOOR_PCT    = cfg['noise_floor_pct']
    MAX_K              = cfg['max_k']
    THRESHOLD = threshold_override if threshold_override is not None else cfg['trend_similarity_threshold']

    total_vol = seg_vol.sum()
    if total_vol == 0:
        return {b: 1 for b in pivot.index}

    months_active = (pivot > 0).sum(axis=1)
    active = sorted([b for b in pivot.index
                     if months_active[b] >= MIN_HISTORY_MONTHS
                     and seg_vol.get(b, 0) / total_vol >= NOISE_FLOOR_PCT])
    if not active:
        active = sorted(pivot.index.tolist())
    if len(active) == 1:
        max_b = int(max(seg_vol.index)) if len(seg_vol) else active[0]
        return {b: 1 for b in range(0, max_b + 100, 100)}

    working  = [[b] for b in active]
    cost_seq = []
    k_seq    = [len(working)]
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
            if cs / total_cost >= THRESHOLD:
                chosen_k = k_seq[i + 1]
                break
    chosen_k = max(2, min(chosen_k, MAX_K, len(active)))

    groups = [[b] for b in active]
    while len(groups) > chosen_k:
        costs = [_merge_cost(pivot, groups[i], groups[i+1]) for i in range(len(groups)-1)]
        best  = int(np.argmin(costs))
        groups[best] = groups[best] + groups[best+1]
        del groups[best+1]

    nb_map = {b: nb for nb, g in enumerate(groups, 1) for b in g}
    max_b    = int(max(seg_vol.index))
    a_sorted = sorted(nb_map)
    final    = {}
    for b in range(0, max_b + 100, 100):
        final[b] = nb_map[b] if b in nb_map else nb_map[min(a_sorted, key=lambda x: abs(x - b))]

    seen = []
    for b in sorted(final):
        if final[b] not in seen:
            seen.append(final[b])
    remap = {old: new+1 for new, old in enumerate(seen)}
    return {b: remap[c] for b, c in final.items()}

def get_k(pivot, seg_vol, cfg, thr=None):
    nb_map = cluster_segment_auto(pivot, seg_vol, cfg, thr)
    return len(set(nb_map.values())), nb_map

print('Clustering helpers defined.')
""")

code("""channel_data = {}

for CH in CHANNELS:
    cfg = get_channel(CH)
    out = cfg['out_path']
    pkl_path = os.path.join(out, '03_segment_pivots.pkl')
    bts_path = os.path.join(out, '02_fine_bucket_ts.csv')
    print(f'[{CH}] looking for: {os.path.abspath(pkl_path)}')
    if not os.path.exists(pkl_path):
        print(f'  SKIP - pkl not found')
        continue
    if not os.path.exists(bts_path):
        print(f'  SKIP - bts not found')
        continue
    with open(pkl_path, 'rb') as f:
        pivots = pickle.load(f)
    bts = pd.read_csv(bts_path)
    channel_data[CH] = {'pivots': pivots, 'bucket_ts': bts, 'cfg': cfg}
    print(f'  OK - {len(pivots)} segments')

print('Available:', list(channel_data.keys()))
""")

code("""def peak_concentration(blist, seg_vol):
    blist = sorted(blist)
    if len(blist) <= 1:
        return None
    vols    = [seg_vol.get(b, 0) for b in blist]
    total_v = sum(vols)
    if total_v == 0:
        return None
    span_total = blist[-1] - blist[0]
    if span_total < 400:
        return None
    best = None
    n = len(blist)
    for w in range(1, n+1):
        for start in range(n - w + 1):
            wv = sum(vols[start:start+w])
            if wv / total_v >= 0.60:
                ws = blist[start+w-1] - blist[start]
                if best is None or ws < best['peak_span']:
                    best = {
                        'peak_start': blist[start], 'peak_end': blist[start+w-1],
                        'peak_span': ws, 'span_total': span_total,
                        'pct_in_peak': round(100*wv/total_v, 1),
                        'flagged': span_total > 400 and ws/max(span_total,1) < 0.40
                    }
                break
        if best and best['peak_span'] < span_total * 0.30:
            break
    return best

def diagnose(seg_key, pivots, bucket_ts, cfg):
    info  = pivots[seg_key]
    pivot = info['pivot']
    div, portal, size = info['div'], info['portal'], info['size']
    seg_vol   = (bucket_ts[(bucket_ts['Division']==div) &
                            (bucket_ts['Portal']==portal) &
                            (bucket_ts['Size']==size)]
                 .groupby('bucket_min')['qty'].sum())
    total_vol = seg_vol.sum()
    res = {'seg_key': seg_key, 'Division': div, 'Portal': portal,
           'Size': size, 'total_vol': int(total_vol)}
    for thr in [0.70, 0.60, 0.50]:
        k, nb_map = get_k(pivot, seg_vol, cfg, thr)
        res[f'k_{int(thr*100)}'] = k
        if thr == 0.70:
            clusters = {}
            for b, nb in nb_map.items():
                if seg_vol.get(b, 0) > 0:
                    clusters.setdefault(nb, []).append(b)
            flagged = []
            for nb, bl in clusters.items():
                c = peak_concentration(bl, seg_vol)
                if c and c['flagged']:
                    flagged.append({'nb': nb, 'range': f'{min(bl)}-{max(bl)}',
                                    'peak': f\"{c['peak_start']}-{c['peak_end']}\",
                                    'pct': c['pct_in_peak']})
            res['flagged'] = flagged
            res['needs_tuning'] = len(flagged) > 0
    res['k_diff_60'] = res.get('k_60', 0) - res.get('k_70', 0)
    return res

print('Diagnostic function defined.')
""")

code("""all_res = []

for CH, data in channel_data.items():
    for seg_key in sorted(data['pivots'].keys()):
        div = data['pivots'][seg_key]['div']
        if div not in FOCUS_DIVS:
            continue
        r = diagnose(seg_key, data['pivots'], data['bucket_ts'], data['cfg'])
        r['channel'] = CH
        all_res.append(r)

print(f'Segments analysed: {len(all_res)}')
flagged = [r for r in all_res if r['needs_tuning']]
print(f'Flagged: {len(flagged)}')
print()
print(f'{\"CH\":<5} {\"Div\":<5} {\"Size\":<8} {\"Segment\":<28} {\"K70\":>4} {\"K60\":>4} {\"K50\":>4} {\"Flag\":>5}')
print('-'*65)
for r in all_res:
    f = f'{len(r[\"flagged\"])}x' if r['needs_tuning'] else ''
    print(f'{r[\"channel\"]:<5} {r[\"Division\"]:<5} {r[\"Size\"]:<8} {r[\"seg_key\"]:<28} '
          f'{r.get(\"k_70\",\"?\")!s:>4} {r.get(\"k_60\",\"?\")!s:>4} {r.get(\"k_50\",\"?\")!s:>4} {f:>5}')
""")

code("""if 'EC' in channel_data:
    DIAG_OUT = channel_data['EC']['cfg']['out_path'].replace('EC/', '')
elif channel_data:
    DIAG_OUT = list(channel_data.values())[0]['cfg']['out_path']
else:
    DIAG_OUT = 'data/outputs/'

os.makedirs(DIAG_OUT, exist_ok=True)

rows = [{'channel': r['channel'], 'seg_key': r['seg_key'], 'Division': r['Division'],
         'Portal': r['Portal'], 'Size': r['Size'], 'total_vol': r['total_vol'],
         'k_at_070': r.get('k_70',''), 'k_at_060': r.get('k_60',''), 'k_at_050': r.get('k_50',''),
         'k_diff_60': r.get('k_diff_60',0), 'needs_tuning': r['needs_tuning'],
         'flagged_details': str(r['flagged'])} for r in all_res]

df = pd.DataFrame(rows)
out = os.path.join(DIAG_OUT, '09_threshold_diagnostic.csv')
df.to_csv(out, index=False)
print(f'Saved: {os.path.abspath(out)}')
print(f'Rows: {len(df)}')
print()
print(df.groupby(['channel','Division'])[['needs_tuning','k_diff_60']].agg({'needs_tuning':'sum','k_diff_60':'mean'}).round(2))
""")

code("""from collections import defaultdict as _dd

def make_chart(seg_key, pivots, bucket_ts, cfg, out_dir):
    info  = pivots.get(seg_key)
    if info is None: return
    pivot = info['pivot']
    div, portal, size = info['div'], info['portal'], info['size']
    seg_vol   = (bucket_ts[(bucket_ts['Division']==div) &
                            (bucket_ts['Portal']==portal) &
                            (bucket_ts['Size']==size)]
                 .groupby('bucket_min')['qty'].sum())
    total_vol = seg_vol.sum()
    if total_vol == 0: return

    active = sorted([b for b in pivot.index
                     if seg_vol.get(b,0)/total_vol >= cfg['noise_floor_pct']
                     and (pivot.loc[b]>0).sum() >= cfg['min_history_months']])
    if not active: return

    months = [str(c)[:7] for c in pivot.columns]
    fig, axes = plt.subplots(3, 1, figsize=(max(14, len(months)*0.35), 13))

    # Row 0 - volume bar
    vols = [100*seg_vol.get(b,0)/total_vol for b in active]
    axes[0].bar([str(b) for b in active], vols, color='steelblue', alpha=0.7)
    axes[0].axhline(5, color='red', linestyle='--', linewidth=0.8)
    axes[0].set_title(f'{seg_key} - Volume distribution', fontweight='bold')
    axes[0].set_ylabel('% volume')
    axes[0].tick_params(axis='x', rotation=60, labelsize=6)

    COLORS = plt.cm.tab10.colors

    for row_i, thr in enumerate([0.70, 0.60], start=1):
        ax = axes[row_i]
        _, nb_map = get_k(pivot, seg_vol, cfg, thr)
        bmap = {b: nb_map[b] for b in active if b in nb_map}
        k = len(set(bmap.values()))
        for b, nb in bmap.items():
            ax.plot(months, pivot.loc[b].values, color=COLORS[(nb-1)%10], alpha=0.45, linewidth=1)
        groups = _dd(list)
        for b, nb in bmap.items(): groups[nb].append(b)
        for nb, bl in sorted(groups.items()):
            ax.plot(months, pivot.loc[bl].mean(axis=0).values,
                    color=COLORS[(nb-1)%10], linewidth=2.5, label=f'NB{nb}')
        ax.set_title(f'Trends at threshold={thr}  K={k}', fontweight='bold')
        ax.set_ylabel('% share')
        ax.legend(fontsize=7, ncol=min(k,6))
        ax.tick_params(axis='x', rotation=45, labelsize=6)
        ax.set_xticks(range(0, len(months), max(1, len(months)//10)))
        ax.set_xticklabels(months[::max(1, len(months)//10)], rotation=45, fontsize=6)

    plt.suptitle(f'{seg_key} - Threshold diagnostic', fontweight='bold')
    plt.tight_layout()
    p = os.path.join(out_dir, f'{seg_key.replace("/","_")}.png')
    plt.savefig(p, dpi=120, bbox_inches='tight')
    plt.close()
    return p

# pick top examples: flagged first, then largest k_diff_60
chart_dir = os.path.join(DIAG_OUT, '09_threshold_diagnostic_charts')
os.makedirs(chart_dir, exist_ok=True)

seen_keys = set()
examples  = []
for CH in CHANNELS:
    for div in FOCUS_DIVS:
        subset = sorted([r for r in all_res if r['channel']==CH and r['Division']==div],
                        key=lambda r: (-int(r['needs_tuning']), -r.get('k_diff_60',0)))
        for r in subset[:EXAMPLES_PER_DIV]:
            if r['seg_key'] not in seen_keys:
                examples.append(r)
                seen_keys.add(r['seg_key'])

saved = []
for r in examples:
    CH = r['channel']
    if CH not in channel_data: continue
    d = channel_data[CH]
    p = make_chart(r['seg_key'], d['pivots'], d['bucket_ts'], d['cfg'], chart_dir)
    if p:
        saved.append(p)
        print(f'  {os.path.basename(p)}')

print(f'Charts saved: {len(saved)}')
print(f'Chart dir: {os.path.abspath(chart_dir)}')
""")

code("""print('='*70)
print('THRESHOLD FINE-TUNING ASSESSMENT')
print('Focus: HL, SL, BP  |  Excl: BS, DF  |  Baseline threshold: 0.70')
print('='*70)
for CH in CHANNELS:
    ch = [r for r in all_res if r['channel']==CH]
    if not ch: continue
    fl = [r for r in ch if r['needs_tuning']]
    kc = [r for r in ch if r.get('k_diff_60',0) > 0]
    print(f'\\n[{CH}] {len(ch)} segments')
    print(f'  Flagged (wide bucket, tight peak): {len(fl)}')
    print(f'  K increases when threshold -> 0.60: {len(kc)}')
    if fl:
        for r in sorted(fl, key=lambda x: -x.get('k_diff_60',0)):
            print(f'    {r[\"seg_key\"]:<30} K70={r.get(\"k_70\",\"?\")}  K60={r.get(\"k_60\",\"?\")}  +{r.get(\"k_diff_60\",0)}')
            for fd in r['flagged']:
                print(f'      NB{fd[\"nb\"]}: {fd[\"range\"]} -> peak {fd[\"peak\"]} ({fd[\"pct\"]}% vol)')
    if not fl and not kc:
        print('  No fine-tuning needed.')
print()
print('CSV:', os.path.abspath(os.path.join(DIAG_OUT, \"09_threshold_diagnostic.csv\")))
print('Charts:', os.path.abspath(chart_dir))
""")

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10.0"}
    },
    "cells": CELLS
}

out = pathlib.Path('../notebooks/09_threshold_diagnostic.ipynb')
out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding='utf-8')
print(f'Written: {out}  ({len(CELLS)} cells)')

# verify
nb2 = json.loads(out.read_text(encoding='utf-8'))
for i, cell in enumerate(nb2['cells']):
    if cell['cell_type'] == 'code':
        src = ''.join(cell['source'])
        status = 'BAD - has null' if 'null' in src else 'OK'
        print(f'  Code cell {i}: {status} ({len(src)} chars)')