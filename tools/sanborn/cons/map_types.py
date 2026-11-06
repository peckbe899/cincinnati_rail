try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Metro construction type along each deck-page piece, from the Rail Profiles page (its own typeAt on the saved / default profiles)
import json, sys, numpy as np
from pyproj import Transformer
from scipy.spatial import cKDTree
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'rer1023'); from metro400 import frame
TR = Transformer.from_crs(4326, 26916, always_xy=True)
D = json.load(open(SP + 'rprof/types.json'))
BORED = {'shield', 'deep'}
prof = {}
for lid, v in D.items():
    P = np.array([TR.transform(p[1], p[2]) for p in v['pts']]); B = np.array([p[3] in BORED for p in v['pts']]); T = [p[3] for p in v['pts']]
    prof[lid.replace('_', ' ')] = (P, B, T, cKDTree(P))
def piece_types(C, tol=40.0):
    out = {}
    for m in C['metro']:
        g, ds, P, nr = frame(m)
        key = m['name']
        if key not in prof: out[m['id']] = None; continue
        PP, B, T, kd = prof[key]
        d, i = kd.query(P)
        b = np.where(d <= tol, B[i].astype(float), np.nan); typ = [T[j] if dd <= tol else None for dd, j in zip(d, i)]
        out[m['id']] = dict(ds=ds, P=P, nr=nr, g=g, b=b, t=typ, d=d)
    return out
if __name__ == '__main__':
    C = json.load(open(SP + 'deckpage/context.json'))
    R = piece_types(C)
    for k, v in R.items():
        if v is None: print(k, 'no profile'); continue
        cov = np.isfinite(v['b']).mean(); print(k, round(v['g'].length), 'covered %.0f%%' % (100 * cov), 'bored %.0f%%' % (100 * np.nanmean(v['b']) if cov > 0 else 0), 'median dist %.1f' % np.median(v['d']))
