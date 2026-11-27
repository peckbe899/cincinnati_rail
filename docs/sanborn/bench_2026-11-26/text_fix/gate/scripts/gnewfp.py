"""gnewfp.py (final gate): where does finder4 call non-text ink text that finder3 did not? And which of those pixels
lie on straight runs (the straight-run proxy)?

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/gate/scripts/gnewfp.py GSCORE.npz OUT_DIR

New false text = truth 1 (non-text ink) called text (2/3) by finder4 and not by finder3, on every sealed crop.
Grouped within 4 px; every group is listed (OUT_DIR/newfp.json) with how many of its px lie on straight runs of 61 px
or more (full crops only, the proxy); the biggest 16 and every group with straight-run px are drawn
(OUT_DIR/newfp_*.png: scan | truth | finder3 | finder4, colours as gpics.py).
"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.argv, _argv = [sys.argv[0], sys.argv[1], sys.argv[1] + '.json', sys.argv[2]], sys.argv   # gpics reads argv at import
import importlib
TR = 'bench_2026-11-26/text_fix/sealed_final'
Z = np.load(_argv[1]); out = _argv[2]; os.makedirs(out, exist_ok=True)
from gscore import straight_runs  # noqa: E402
crops = json.load(open(os.path.join(TR, 'crops.json'), encoding='utf8'))
groups = []
for cid, c in crops.items():
    T = cv2.imread(os.path.join(TR, f'{cid}_mask.png'), cv2.IMREAD_UNCHANGED)
    a = np.isin(Z[f'cut|finder3|{cid}'], (2, 3)); b = np.isin(Z[f'cut|finder4|{cid}'], (2, 3))
    new = (T == 1) & b & ~a; lost = (T == 1) & a & ~b
    if lost.any(): print('finder4 took back false text in', cid, int(lost.sum()))
    if not new.any(): continue
    st = straight_runs(T == 1) if c.get('kind') == 'full' else np.zeros(T.shape, bool)
    n, lb = cv2.connectedComponents(cv2.dilate(new.astype(np.uint8), np.ones((9, 9), np.uint8)), connectivity=8)
    for i in range(1, n):
        m = (lb == i) & new; k = int(m.sum())
        if not k: continue
        ys, xs = np.nonzero(m); x0, y0 = c['win'][:2]
        groups.append(dict(crop=cid, plate=c['plate'], ft=c['scale_ft_per_inch'], kind=c.get('kind'), px=k, straight_px=int((m & st).sum()),
                           box=[int(xs.min() + x0), int(ys.min() + y0), int(xs.max() + x0 + 1), int(ys.max() + y0 + 1)]))
groups.sort(key=lambda g: -g['px'])
by_kind = {}
for g in groups: by_kind[g['kind']] = by_kind.get(g['kind'], 0) + g['px']
json.dump(dict(total_new_fp=sum(g['px'] for g in groups), by_crop_kind=by_kind, straight_px=sum(g['straight_px'] for g in groups), groups=groups),
          open(os.path.join(out, 'newfp.json'), 'w'), indent=1)
print('new false text px', sum(g['px'] for g in groups), 'groups', len(groups), 'by crop kind', by_kind, 'on straight runs', sum(g['straight_px'] for g in groups))
# pictures with gpics' tile()
sys.argv = [sys.argv[0], _argv[1], 'bench_2026-11-26/text_fix/gate/scores/boot_sealed.json', out]
src = open(os.path.join(HERE, 'gpics.py'), encoding='utf8').read().split('\nfor kind in')[0]   # only the helpers
ns = {}; exec(compile(src, 'gpics_helpers', 'exec'), ns)
pick = groups[:16] + [g for g in groups[16:] if g['straight_px']]
tl = [ns['tile'](g['crop'], g['box'], f"new fp #{i + 1} {g['crop']} plate {g['plate']} {g['ft']} ft at {g['box'][0]},{g['box'][1]}: {g['px']} px new, {g['straight_px']} on straight runs", pad=30)
      for i, g in enumerate(pick)]
ns['out'] = out; ns['sheets'](tl, 'newfp', per=4)
