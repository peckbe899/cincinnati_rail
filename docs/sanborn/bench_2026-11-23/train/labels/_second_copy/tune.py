"""Tune the pseudo-label thresholds on plate 1A ONLY (pseudo labels from 1A's batch outputs against 1A's map labels
from Ben). Nothing is written outside bench_2026-11-23/train/labels/tune/.
    cd data/sanborn;  PY -B bench_2026-11-23/train/labels/tune/tune.py STAGE   (STAGE: alley | area | lines | final)"""
import json, sys, time, itertools
import numpy as np, cv2
sys.path.insert(0, 'bench_2026-11-23/train/staged/tools/sanborn/unet')
import make_labels_v2 as M
T = 'bench_2026-11-23/train/labels/tune/'; MAP = 'bench_2026-11-23/train/labels/out/'
N = '44' if '--report44' in sys.argv else '1A'
assert N == '1A' or sys.argv[1] == 'final', 'tuning is on 1A only; 44 is only reported (stage final --report44)'
kw = dict(outlines='bench_2026-11-23/train/labels/batch44/outlines.json', edges='bench_2026-11-23/train/labels/batch44/44_edges.json') if N == '44' else {}
t0 = time.time(); I = M.pseudo_inputs(N, **kw); ftpi = M.scale_ft(N) or 100
ml = cv2.imread(MAP + N + '/label.png', 0); mt = cv2.imread(MAP + N + '/lines.png', 0); sm = json.load(open(MAP + N + '/streetmap.json', encoding='utf8'))
print('loaded', round(time.time() - t0, 1), 's', flush=True)
stage = sys.argv[1]; rows = []
def run(th, al, tag):
    lab, t, edge, c = M.pseudo_labels(I, th, ftpi, al)
    r = M.compare_arrays(N, lab, t, ml, mt, sm)
    row = dict(tag=tag, th={k: v for k, v in th.items()}, alley_px=c['alley_px'], area=r['area'], lines=r['lines']); rows.append(row)
    a, l = r['area'], r['lines']
    print(f"{tag:40s} blkP {a['block_precision']} stP {a['street_precision']} cov {a['coverage_of_decided']} (blk {a['coverage_of_decided_block']} st {a['coverage_of_decided_street']}) | posP {l['pos_precision']} ben neg {l['ben_lines']['wrongly_negative']} (pr {l['ben_printed']['wrongly_negative']} dr {l['ben_drawn']['wrongly_negative']}) 255 {l['ben_lines']['left_255']} pos {l['ben_lines']['taught_positive']} | negcov {l['neg_coverage_of_map_neg']} negagree {l['neg_agree_with_map']}", flush=True)
    return lab, t
base = dict(M.PSEUDO)
if stage == 'alley':
    t0 = time.time(); al, found = M.alley_strips(I, ftpi); print('alley strips', len(found), round(time.time() - t0, 1), 's'); json.dump(found, open(T + f'{N}_alleys.json', 'w'), indent=0)
    run(base, None, 'no alley'); run(base, al, 'alley')
    # how much of the strips is Ben's block (cost) and how many of his drawn lines they cover
    print('alley px', int(al.sum()), 'of which map block', round(float((ml[al] == 1).mean()), 3), 'map street', round(float((ml[al] == 0).mean()), 3), 'map 255', round(float((ml[al] == 255).mean()), 3))
    cv2.imwrite(T + f'{N}_alley.png', al.astype(np.uint8) * 255)
elif stage == 'area':
    al, _ = M.alley_strips(I, ftpi)
    for hi, lo, d, ds in itertools.product((0.5, 0.8, 0.9, 0.95, 0.98), (0.02, 0.05, 0.1, 0.2, 0.5), (4, 8, 12, 16), (2, 6, 10)):
        th = dict(base, hi=hi, lo=lo, d=d, ds=ds); run(th, al, f'hi{hi} lo{lo} d{d} ds{ds}')
elif stage == 'lines':                       # one parameter at a time around the base (the area thresholds from the area stage)
    al, _ = M.alley_strips(I, ftpi); base = dict(base, **json.loads(sys.argv[2])) if len(sys.argv) > 2 and sys.argv[2].startswith('{') else base
    run(base, al, 'base')
    for k, vals in (('tl', (0.02, 0.05, 0.2, 0.3, 0.5)), ('ms', (6, 20, 30, 45)), ('mr', (3, 12, 20)), ('mu', (0, 2, 10, 20, 30, 45)), ('me', (10, 20, 30)), ('ll', (80, 120, 150, 200, 300)), ('gmin', (100, 150, 200, 300))):
        for v in vals: run(dict(base, **{k: v}), al, f'{k}={v}')
elif stage == 'joint':
    al, _ = M.alley_strips(I, ftpi); base = dict(base, **json.loads(sys.argv[2]))
    for combo in json.loads(sys.argv[3]): run(dict(base, **combo), al, json.dumps(combo))
elif stage == 'final':
    al, _ = M.alley_strips(I, ftpi) if base.get('alley') else (None, [])
    base = dict(base, **json.loads(sys.argv[2])) if len(sys.argv) > 2 and sys.argv[2].startswith('{') else base
    lab, t = run(base, al, 'final ' + N)
    for part in ('train', 'val'):
        r = M.compare_arrays(N, lab, t, ml, mt, sm, part); rows.append(dict(tag='final ' + N + ' ' + part, th=base, area=r['area'], lines=r['lines'])); print(part, json.dumps(r))
json.dump(rows, open(T + f'{N}_{stage}.json', 'w'), indent=0, default=float)
