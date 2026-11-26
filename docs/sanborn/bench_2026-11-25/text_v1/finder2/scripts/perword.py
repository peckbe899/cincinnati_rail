"""Per-word recall on truth v2 T1-T7 for chosen kinds (finder2, 25 Nov 2026). Same pixel rule as score_text.py.

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/finder2/scripts/perword.py MASK_PATTERN CODES [kind,kind] [--max 0.9]

Prints every word of the kinds whose recall is under --max (default 1.01: all), with where its missed pixels went
(by mask code)."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
TRUTH = os.path.normpath(os.path.join(HERE, '..', '..', 'truth'))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', '..', 'code')))
from score_text import poly_fill

a = [x for i, x in enumerate(sys.argv[1:], 1) if not x.startswith('--') and sys.argv[i - 1] != '--max']
pat, codes = a[0], [int(v) for v in a[1].split(',')]; kinds = a[2].split(',') if len(a) > 2 else None
mx = float(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 1.01
crops = json.load(open(os.path.join(TRUTH, 'crops.json'))); cache = {}
for tid in ('T1', 'T2', 'T3', 'T4', 'T6', 'T7'):
    c = crops[tid]; x0, y0, x1, y1 = c['win']; p = pat.replace('{plate}', c['plate'])
    if p not in cache: cache[p] = cv2.imread(p, 0)
    code = cache[p][y0:y1, x0:x1]; truth = cv2.imread(os.path.join(TRUTH, f'{tid}_mask.png'), 0); t2 = truth == 2
    for w in json.load(open(os.path.join(TRUTH, f'{tid}_words.json'), encoding='utf8'))['words']:
        if kinds and w['kind'] not in kinds or not w.get('poly'): continue
        pm = poly_fill(truth.shape, w['poly'], np.array([x0, y0])) & t2; n = int(pm.sum())
        if not n: continue
        f = int((pm & np.isin(code, codes)).sum())
        if f / n < mx:
            miss = {int(v): int(((code == v) & pm).sum()) for v in range(6) if v not in codes and ((code == v) & pm).any()}
            print(f"{tid} {w['kind']:6s} {w['reading'][:22]:22s} h {w.get('height', 0):5.1f}  recall {f / n:.3f} ({f}/{n})  missed by code {miss}  aabb {w.get('aabb')}")
