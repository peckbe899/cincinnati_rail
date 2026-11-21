"""merge/impl/r2: the ink sorting of unplaced plates from the round-2 block step, before and after (21 Nov 2026).

    python -B bins12.py [N ...]     -> merge/impl/r2/bins12/N_bins.png and .json, merge/impl/r2/bins12.json

After: the staged ink_bins.py N --edges r2/plates_final/N/N_edges.json --outlines r2/plates_final/N/outlines.json --save
(system python, the shim _ws first). The outline step's N_outlines.json and N_mapground.png are read from beside the
outlines, as a real run reads them from unet_data after the block step; none of these plates has edges_ben.json.
Before: the repo's unet_data/N_bins.json (the batch's; for 90 the 14:09 editor-button run with Ben's rail).
The same plates as merge/v-batch's bins12.py, plus round 1 (merge/v-batch/bins/N_bins.json, the first staged merge).
"""
import concurrent.futures as cf, json, os, sys
import common as C
PL = sys.argv[1:] or ['90', '30', '79', '60B', '64A', '26A', '5', '1B', '1A', '3', '47', '93A']
O = C.IMPL + 'bins12/'; os.makedirs(O, exist_ok=True)
NAMES = ['block line', 'lot line', 'building outline', 'railroad', 'streetcar', 'water pipe', 'sewer', 'text and numbers', 'not sorted']


def one(n):
    d = C.IMPL + f'plates_final/{n}/'
    out, js = C.ink_bins(n, O + f'{n}_bins.png', ['--edges', d + f'{n}_edges.json', '--outlines', d + 'outlines.json'])
    b = json.load(open(C.U + f'{n}_bins.json', encoding='utf8')); r1f = C.MERGE + f'v-batch/bins/{n}_bins.json'; r1 = json.load(open(r1f)) if os.path.exists(r1f) else None
    px = lambda j: {v['name']: v['px'] for v in j['bins'].values()} if j else None
    return n, dict(before=px(b), round1=px(r1), after=px(js), ground_from=js.get('ground_from'), outline_version=js.get('outline_version'), map_ground=('map ground' in js.get('made_from', {})))


with cf.ThreadPoolExecutor(4) as ex: res = dict(ex.map(one, PL))
json.dump(res, open(C.IMPL + 'bins12.json', 'w'), indent=1)
for n, r in res.items():
    print(n, r['ground_from'], ' | '.join(f"{k} {r['before'][k]:,} -> {r['after'][k]:,}" + (f" (r1 {r['round1'][k]:,})" if r['round1'] else '') for k in NAMES if k in ('block line', 'lot line', 'water pipe', 'sewer', 'not sorted', 'railroad')))
