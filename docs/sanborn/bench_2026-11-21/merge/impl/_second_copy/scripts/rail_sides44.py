"""merge/impl: how right are the sides the merged outline step calls 'on rail', on plate 44? (21 Nov 2026)

    python -B rail_sides44.py RUN [RUN ...]        RUN = a folder of bench44_runs (outlines.json from the staged step)

For every side that is not paper_edge: its length, and the share of its length (1 px samples) within 5 px and 20 degrees
of one of Ben's street-map lines (streetmap/22-44.json; bench44's own matcher, staged tools bench44.py). Grouped by
state, so 'on rail' sides can be compared with the others, and by the rail threshold (share of the side on rail ink, the
'rail' field) for sides whose 'was' state is kept. Also the same for RAIL_TOL 3 vs 5 and RAIL_SHARE 0.3/0.5/0.7, from
the bins named on the command line (--bins PNG) -> rail_sides44.json
"""
import json, os, sys
import numpy as np
import cv2
import common as C
C.step4_mod()
sys.path.insert(0, C.SU)
import bench44 as B  # the staged tools bench44 (its truth loader and line matcher)

T = B.load_truth(); ben = B.LineSet(T['lines'], 20.0)
args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith('--') and sys.argv[i - 1] != '--bins']
bins = sys.argv[sys.argv.index('--bins') + 1] if '--bins' in sys.argv else C.U + '44_bins.png'
R = cv2.imread(bins, 0); rail0 = np.isin(R, (4, 5)).astype(np.uint8); rr0 = (R == 4).astype(np.uint8)
el = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
Hh, Ww = R.shape
def along(img, a, b):
    d = b - a; L = np.hypot(*d); t = np.linspace(0.06, 0.94, max(10, int(L))); q = a + np.outer(t, d)
    return img[np.clip(q[:, 1].round().astype(int), 0, Hh - 1), np.clip(q[:, 0].round().astype(int), 0, Ww - 1)]
out = {}
for run in args:
    d = C.IMPL + 'bench44_runs/' + run + '/'
    polys = json.load(open(d + 'outlines.json', encoding='utf8'))
    S = [s for p in polys for s in p if not s.get('paper_edge')]
    ls = B.LineSet([(np.array(s['a'], float), np.array(s['b'], float), s['state']) for s in S], 20.0)
    dist = ls.dist_to(ben); ok = B.per_line(ls, dist, 5.0); L = np.array([np.hypot(*(np.array(s['b']) - np.array(s['a']))) for s in S])
    res = {}
    for st in sorted({s['state'] for s in S}):
        m = np.array([s['state'] == st for s in S])
        res[st] = dict(sides=int(m.sum()), len_px=round(float(L[m].sum())), on_ben_share_by_len=round(float((ok[m] * L[m]).sum() / max(1, L[m].sum())), 4))
    onr = np.array([s['state'] == 'on rail' for s in S])
    if onr.any():
        res['on rail by was'] = {w: dict(sides=int(sum(1 for s, o in zip(S, onr) if o and s.get('was') == w)), len_px=round(float(sum(l for s, o, l in zip(S, onr, L) if o and s.get('was') == w))),
                                         on_ben_share_by_len=round(float(sum(k * l for s, o, k, l in zip(S, onr, ok, L) if o and s.get('was') == w) / max(1, sum(l for s, o, l in zip(S, onr, L) if o and s.get('was') == w))), 4))
                                 for w in sorted({s.get('was') for s, o in zip(S, onr) if o})}
        res['on rail, railroad bin only'] = None
    # thresholds and tolerance, recomputed on the same sides (the state before demotion)
    sweep = {}
    for tol in (2, 3, 5):
        for kind, base in (('rail 4+5', rail0), ('railroad 4', rr0)):
            rm = cv2.dilate(base, el(tol))
            share = np.array([float(along(rm, np.array(s['a'], float), np.array(s['b'], float)).mean()) for s in S])
            for thr in (0.3, 0.5, 0.7):
                m = share > thr
                sweep[f'{kind} tol{tol} share>{thr}'] = dict(sides=int(m.sum()), len_px=round(float(L[m].sum())), on_ben_len_px=round(float((ok[m] * L[m]).sum())),
                                                            on_ben_share_by_len=round(float((ok[m] * L[m]).sum() / max(1, L[m].sum())), 4))
    out[run] = dict(by_state=res, sweep=sweep, bins=bins)
    print(run, json.dumps(res, indent=None)[:1500]); [print('  ', k, v) for k, v in sweep.items()]
json.dump(out, open(C.IMPL + 'rail_sides44.json', 'w'), indent=1)
