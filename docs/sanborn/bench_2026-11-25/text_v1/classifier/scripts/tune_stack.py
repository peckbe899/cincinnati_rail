"""Set finder3's thresholds for the combiner (stack.py) on T1-T7, from LEAVE-ONE-CROP-OUT predictions (classifier step,
26 Nov 2026). DEV ONLY, never the held-out crops.
    cd data/sanborn; python -B bench_2026-11-25/text_v1/classifier/scripts/tune_stack.py [COMBINER_loco.npz] [--small] [--p JSON]
           [--write TJ TT DIR]   (writes that setting's leave-one-crop-out code images, cut to each crop, for score_text.py)
Each crop's pieces carry P(text) from a combiner that never saw that crop; finder3's stage_b and finder2's shared_ink make
the code image; scored as score_text.py (codes 2, 3). Flip rules: finder2 text -> other when P(text) <= 1 - tj; finder2
other -> text when P(text) >= tt (with finder3's guards)."""
import json, os, sys, itertools
sys.dont_write_bytecode = True
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from tune import Dev, load_state, finder3  # noqa
OUT = os.path.join(HERE, '..', 'out')
a = sys.argv[1:]; L = np.load(a[0] if a and a[0].endswith('.npz') else os.path.join(OUT, 'combiner_cnn2_loco.npz'))
dev = Dev(); S = {N: load_state(N) for N in ('44', '1A', '5')}; pj = {}
for N in S:
    p = np.full(len(S[N]['bbox']), np.nan, np.float32); m = L['plate'] == N; p[L['idx'][m]] = 1 - L['p_loco'][m]; pj[N] = p
allk = ('glyph', 'cluster', 'stroke', 'dot', 'eq', 'jog', 'blob', 'long')
res = {}
grid = [(tj, tt) for tj in (0.5, 0.6, 0.7, 0.8, 0.9, 2) for tt in (0.5, 0.6, 0.7, 0.8, 0.9, 2)]
if '--small' in a: grid = [(tj, tt) for tj in (0.5, 0.6, 0.7) for tt in (0.5, 0.6, 0.7)] + [(2, 2)]
extra = json.loads(a[a.index('--p') + 1]) if '--p' in a else {}
if '--write' in a: grid = []
for tj, tt in grid:
    codes = {}; fl = {}
    for N in S: codes[N], info = finder3.stage_b(S[N], pj[N], dict(dict(tj=tj, tt=tt, tj_kinds=allk), **extra)); fl[N] = (info['to_other'], info['to_text'])
    r = dev.score(codes); r['flips'] = fl; res[f'tj={tj} tt={tt}'] = r; k = r['kinds']
    print(f"tj {tj} tt {tt}: P {r['P']:.4f} R {r['R']:.4f} F1 {r['F1']:.4f} nontext {r['nontext']:.4f} | street {k.get('street')} block {k.get('block')} adj {k.get('adj')} | flips {fl} | {r['per']}", flush=True)
if grid: json.dump(res, open(os.path.join(OUT, 'tune_stack.json'), 'w'), indent=1)
if '--write' in a:   # write the leave-one-crop-out code images of one setting, cut to each crop, for score_text.py
    import cv2
    tj, tt, d = float(a[a.index('--write') + 1]), float(a[a.index('--write') + 2]), a[a.index('--write') + 3]; os.makedirs(d, exist_ok=True)
    codes = {N: finder3.stage_b(S[N], pj[N], dict(dict(tj=tj, tt=tt, tj_kinds=allk), **extra))[0] for N in S}
    for t in ('T1', 'T2', 'T3', 'T4', 'T6', 'T7'):
        c = dev.crops[t]; x0, y0, x1, y1 = c['win']; g = 4; sub = codes[c['plate']][y0 - g:y1 + g, x0 - g:x1 + g].copy()
        sub, _ = finder3.finder2.shared_ink(sub, (sub > 0).astype(np.uint8)); cv2.imwrite(os.path.join(d, f'{t}_text.png'), sub[g:-g, g:-g])
    print('wrote', d)
