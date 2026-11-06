try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# 1904 sheets on the page vs the 1922 plates: every 1904 crossing (sbg/picks/sNNN.json) placed with its frame (similarity + lph/tps.pkl),
# matched by street names to the same crossing on a 1922 plate within 45 m. Writes cuf/x1904.json.
import json, sys, glob, pickle, collections, numpy as np
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'sbg'); sys.path.insert(0, _ws.CODE + 'cuf'); sys.path.insert(0, _ws.CODE + 'lph')
import common as C, mosn, tps
from names import key, base     # 2026-10-21: crossings matched on base names, so East/West halves match (West Charlton at Vine = East Charlton at Vine)
from matplotlib.path import Path
TF = {}
for fn in ('lph/tf_all.json', 'lph/tf_ext.json', 'lph/tf_ext2.json', 'lph/tf_ext3.json'): TF.update(json.load(open(SP + fn)))
import os
MOD = pickle.load(open(SP + ('lph/tps_pre1922.pkl' if os.path.exists(SP + 'lph/tps_pre1922.pkl') else 'lph/tps.pkl'), 'rb'))     # positions before the 1922 bend
PX = {}
for fn in ('lph/panels_ext.json', 'lph/panels_ext2.json', 'lph/panels_ext3.json'): PX.update(json.load(open(SP + fn)))
def place(fr, x, y):
    E, N = mosn.ap(TF[fr], np.array([x], float), np.array([y], float))
    if fr in MOD: dE, dN = tps.disp(fr, E, N, MOD); E, N = E + dE, N + dN
    return float(E[0]), float(N[0])
# 1922 crossings
X22 = []
def add22(files, plate, fn_world):
    seen = []
    for f in files:
        for p in json.load(open(f))['intersections']:
            if '?' in p['a'] + p['b']: continue
            k = tuple(sorted((base(key(p['a'])), base(key(p['b'])))))
            q = next((s for s in seen if s['k'] == k and np.hypot(s['x'] - p['x'], s['y'] - p['y']) < 60), None)
            if q: q['xs'].append(p['x']); q['ys'].append(p['y']); q['x'] = float(np.mean(q['xs'])); q['y'] = float(np.mean(q['ys']))
            else: seen.append(dict(k=k, a=p['a'], b=p['b'], x=p['x'], y=p['y'], xs=[p['x']], ys=[p['y']], plate=plate))
    for s in seen: s['E'], s['N'] = fn_world(s['x'], s['y']); X22.append(s)
add22(sorted(glob.glob(SP + 'sbg/picks22/s22-35N_*.json')), '22-35N', lambda x, y: tuple(float(v) for v in C.px2ben(x, y)))
import os
if os.path.exists(SP + 'cuf38/fwd38.pkl'):
    sys.path.insert(0, _ws.CODE + 'cuf38'); import fwd38lib
    add22(sorted(glob.glob(SP + 'sbg/picks22/s22-38_*.json')), '22-38', fwd38lib.world)
sys.path.insert(0, _ws.CODE + 'cufp'); import fwdlib          # 2026-10-21: plates 66-70
for _n in ('66', '67', '68', '69', '70'):
    if os.path.exists(SP + f'cufp/{_n}/fwd.pkl'): add22(sorted(glob.glob(SP + f'sbg/picks22/s22-{_n}_*.json')), '22-' + _n, (lambda n: lambda x, y: fwdlib.world(n, x, y))(_n))
for _h in ('34L', '34R', '37L', '37R', '16R'):     # 2026-10-22: the vol. 1 halves under Northside / Camp Washington, refitted (cuf_cw/fit.py)
    if os.path.exists(SP + f'cuf_cw/{_h}/fwd.pkl'): add22([SP + f'sbg/picks22/s22-{_h}.json'] + sorted(glob.glob(SP + f'sbg/picks22/s22-{_h}_*.json')), '22-' + _h, (lambda n: lambda x, y: fwdlib.world(n, x, y))(_h))
print('1922 crossings', len(X22), collections.Counter(s['plate'] for s in X22))
FR = sys.argv[1].split(',')
out = []
for fr in FR:
    sh = ''.join(ch for ch in fr if ch.isdigit())
    J = json.load(open(SP + f'sbg/picks/s{sh}.json'))
    # which picks belong to this frame: inside its own panel if it has one; else outside the panels of its sibling frames
    sibs = [k for k in PX if ''.join(ch for ch in k if ch.isdigit()) == sh and k != fr]
    for p in J['intersections']:
        if '?' in p['a'] + p['b']: continue
        if fr in PX and not Path(np.array(PX[fr])).contains_point((p['x'], p['y'])): continue
        if any(Path(np.array(PX[s])).contains_point((p['x'], p['y'])) for s in sibs): continue
        k = tuple(sorted((base(key(p['a'])), base(key(p['b']))))); E, N = place(fr, p['x'], p['y'])
        c = [s for s in X22 if s['k'] == k and np.hypot(s['E'] - E, s['N'] - N) < 45]
        r = dict(fr=fr, a=p['a'], b=p['b'], x=p['x'], y=p['y'], E=E, N=N, k=k)
        if c:
            s = min(c, key=lambda s: np.hypot(s['E'] - E, s['N'] - N)); r.update(E22=s['E'], N22=s['N'], plate=s['plate'], d=float(np.hypot(s['E'] - E, s['N'] - N)))
        out.append(r)
json.dump(out, open(SP + 'cuf/x1904.json', 'w'), indent=1)
for fr in FR:
    m = [r for r in out if r['fr'] == fr]; h = [r for r in m if 'd' in r]
    if h: dd = np.array([r['d'] for r in h]); v = np.array([[r['E22'] - r['E'], r['N22'] - r['N']] for r in h]).mean(0)
    print(f"{fr:5s} crossings {len(m):3d} matched {len(h):3d}" + (f"  median {np.median(dd):5.1f} m  max {dd.max():5.1f}  mean shift ({v[0]:+.1f}, {v[1]:+.1f})" if h else ''))
