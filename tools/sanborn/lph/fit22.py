"""Georeference 1922 vol. 1 plate halves 3, 6, 26 (main), 29 (L/R) for the Lower Price Hill seam fix.
Model per half: similarity (a, c, tx, ty) or affine (6), linear least squares with Huber reweighting.
Observations:
  osm  : name pair with an OSM intersection (sbg/fit/osmx.pkl, surviving streets)
  bas  : name pair read on a fitted basin frame (sbg/fit/tf.json, deck sheets excluded), world point = cluster median
  tie  : same name pair on two halves
Deck 1904 sheets are NOT used: they are what this corrects.
"""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, os, glob, pickle, collections, itertools, numpy as np
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'sbg'); sys.path.insert(0, _ws.CODE + 'sbg/fit')
from names import key
import os as _os
HALVES = _os.environ.get('HALVES', '3L,3R,6L,6R,26L,26R,29L,29R').split(',')
DECK = {33, 34, 35, 47, 57, 58, 67, 68, 69, 77, 201, 202, 211, 212, 221, 222, 233, 234, 245, 246, 253, 254}
ALIAS = {'vanhorne': 'vanhorn', 'saint michael': 'st michael', 'pardee al': 'pardee', 'dutten': 'dutton', 'mt hope rd': 'mount hope', 'mount hope rd': 'mount hope'}
def K(n):
    k = key(n)
    return ALIAS.get(k, k)
def pair(a, b): return tuple(sorted((K(a), K(b))))

def load22():
    R = []
    for h in HALVES:
        d = json.load(open(SP + f'sbg/picks22/s22-{h}.json'))
        for p in d['intersections']:
            if p.get('part') == 'inset': continue
            if '?' in (p['a'], p['b']): continue
            R.append(dict(fr=h, a=p['a'], b=p['b'], k=pair(p['a'], p['b']), x=float(p['x']), y=float(p['y'])))
    return R

def basin_points():
    from load import load
    TF = json.load(open(SP + 'sbg/fit/tf.json'))
    if _os.environ.get('USE_ALL'):
        TA = json.load(open(SP + 'lph/tf_all.json'))
        for k, v in TA.items(): TF[k] = v
    recs, _ = load()
    def ap(p, x, y):
        if len(p) == 6: return p[0] * x + p[1] * y + p[4], p[2] * x + p[3] * y + p[5]
        a, c, tx, ty = p; return a * x + c * y + tx, c * x - a * y + ty
    G = collections.defaultdict(list)
    for r in recs:
        if (r['s'] in DECK and not _os.environ.get('USE_ALL')) or not r['fr'] or r['fr'] not in TF: continue
        E, N = ap(TF[r['fr']], r['x'], r['y'])
        G[pair(r['a'], r['b'])].append((E, N))
    out = {}
    for k, v in G.items():
        v = np.array(v); m = np.median(v, 0)
        # split far-apart readings (same pair at two places) into clusters
        cl = []
        for q in v:
            for c in cl:
                if np.hypot(*(q - np.median(c, 0))) < 25: c.append(q); break
            else: cl.append([q])
        out[k] = [tuple(np.median(c, 0)) for c in cl]
    return out

def osm_points():
    d = pickle.load(open(SP + 'lph/' + _os.environ.get('OSMPKL', 'osm2.pkl'), 'rb'))
    out = collections.defaultdict(list)
    for k, v in d.items():
        kk = tuple(sorted((ALIAS.get(k[0], k[0]), ALIAS.get(k[1], k[1]))))
        out[kk] += [tuple(map(float, p)) for p in v]
    if _os.environ.get('USE_T12'):            # 1912 survey corners (sbg/picks12), as OSM-grade control
        for f in sorted(glob.glob(SP + 'sbg/picks12/*.json')):
            for q in json.load(open(f))['intersections']:
                out[pair(q['a'], q['b'])].append((float(q['E']), float(q['N'])))
    return out

def ncoef(model): return 4 if model == 'sim' else 6
def rows(model, x, y):
    if model == 'sim': return {0: x, 1: y, 2: 1}, {0: -y, 1: x, 3: 1}
    return {0: x, 1: y, 4: 1}, {2: x, 3: y, 5: 1}
def ap(p, x, y):
    if len(p) == 6: return p[0] * x + p[1] * y + p[4], p[2] * x + p[3] * y + p[5]
    a, c, tx, ty = p; return a * x + c * y + tx, c * x - a * y + ty

def fit_sim(src, dst):
    z = src[:, 0] - 1j * src[:, 1]; w = dst[:, 0] + 1j * dst[:, 1]
    M = np.c_[z, np.ones_like(z)]; sol, *_ = np.linalg.lstsq(M, w, rcond=None); return sol[0], sol[1]

def ransac(src, dst, thr=15.0):
    n = len(src); best = None
    for i, j in itertools.combinations(range(n), 2):
        if np.hypot(*(src[i] - src[j])) < 800: continue
        A, B = fit_sim(src[[i, j]], dst[[i, j]])
        z = src[:, 0] - 1j * src[:, 1]; r = np.abs(A * z + B - (dst[:, 0] + 1j * dst[:, 1]))
        inl = r < thr; sc = inl.sum() - 1e-3 * r[inl].sum()
        if best is None or sc > best[0]: best = (sc, inl, A, B)
    if best is None: return None
    inl = best[1]
    for _ in range(3):
        A, B = fit_sim(src[inl], dst[inl])
        z = src[:, 0] - 1j * src[:, 1]; r = np.abs(A * z + B - (dst[:, 0] + 1j * dst[:, 1])); inl = r < thr
    return np.array([A.real, A.imag, B.real, B.imag]), inl

def main(model='sim', gate=(25, 12, 8), w_bas=1.0, w_osm=1.0, w_tie=1.0, verbose=True, out='tf22.json'):
    R = load22(); OSM = osm_points(); BAS = basin_points()
    frames = HALVES
    # candidate controls per pick
    def cands(r):
        c = [('osm', p) for p in OSM.get(r['k'], [])] + [('bas', p) for p in BAS.get(r['k'], [])]
        return c
    # start: ransac per frame on unique candidates
    P = {}
    for h in frames:
        src, dst = [], []
        for r in R:
            if r['fr'] != h: continue
            for typ, p in cands(r): src.append((r['x'], r['y'])); dst.append(p)
        src, dst = np.array(src), np.array(dst)
        res = ransac(src, dst) if len(src) >= 3 else None
        if res is None: print('no start', h, len(src)); continue
        p, inl = res; P[h] = p
        if verbose: print(f'start {h}: {inl.sum()}/{len(src)} scale {1/np.hypot(p[0],p[1]):.3f} px/m rot {np.degrees(np.arctan2(p[1],p[0])):.2f}')
    if model == 'aff':
        P = {h: np.array([p[0], p[1], p[1], -p[0], p[2], p[3]]) for h, p in P.items()}
    # ties
    byk = collections.defaultdict(list)
    for r in R:
        if r['fr'] in P: byk[r['k']].append(r)
    for g in gate:
        obs = []
        for r in R:
            h = r['fr']
            if h not in P: continue
            E, N = ap(P[h], r['x'], r['y'])
            best = None
            for typ, q in cands(r):
                d = np.hypot(E - q[0], N - q[1])
                if best is None or d < best[0]: best = (d, typ, q)
            if best and best[0] < g:
                obs.append(dict(t=best[1], fr=h, x=r['x'], y=r['y'], q=best[2], lab=f"{r['a']}/{r['b']}", w=w_osm if best[1] == 'osm' else w_bas))
        for k, rs in byk.items():
            for r1, r2 in itertools.combinations(rs, 2):
                if r1['fr'] == r2['fr']: continue
                E1, N1 = ap(P[r1['fr']], r1['x'], r1['y']); E2, N2 = ap(P[r2['fr']], r2['x'], r2['y'])
                if np.hypot(E1 - E2, N1 - N2) < g:
                    obs.append(dict(t='tie', fr=r1['fr'], x=r1['x'], y=r1['y'], fr2=r2['fr'], x2=r2['x'], y2=r2['y'], lab=f"{r1['a']}/{r1['b']}", w=w_tie))
        idx = {h: i for i, h in enumerate(sorted(P))}; nc = ncoef(model); nP = nc * len(idx)
        hub = np.ones(len(obs))
        for it in range(8):
            A, b, W = [], [], []
            for o, hw in zip(obs, hub):
                rE, rN = rows(model, o['x'], o['y'])
                for comp in (0, 1):
                    row = np.zeros(nP)
                    for j, v in (rE if comp == 0 else rN).items(): row[idx[o['fr']] * nc + j] += v
                    if o['t'] == 'tie':
                        r2E, r2N = rows(model, o['x2'], o['y2'])
                        for j, v in (r2E if comp == 0 else r2N).items(): row[idx[o['fr2']] * nc + j] -= v
                        rhs = 0.0
                    else: rhs = o['q'][comp]
                    A.append(row); b.append(rhs); W.append(o['w'] * hw)
            A, b, W = np.array(A), np.array(b), np.sqrt(np.array(W))
            # center the translation unknowns numerically: solve directly (well conditioned enough with px coords)
            sol, *_ = np.linalg.lstsq(A * W[:, None], b * W, rcond=None)
            for h, i in idx.items(): P[h] = sol[i * nc:(i + 1) * nc]
            res = []
            for o in obs:
                E, N = ap(P[o['fr']], o['x'], o['y'])
                if o['t'] == 'tie': E2, N2 = ap(P[o['fr2']], o['x2'], o['y2']); res.append(np.hypot(E - E2, N - N2))
                else: res.append(np.hypot(E - o['q'][0], N - o['q'][1]))
            res = np.array(res); hub = np.where(res < 2.0, 1.0, 2.0 / np.maximum(res, 1e-9))
        if verbose:
            print(f'gate {g}: {len(obs)} obs', {t: (int((np.array([o["t"] for o in obs]) == t).sum()), round(float(np.median(res[np.array([o["t"] for o in obs]) == t])), 2) if (np.array([o["t"] for o in obs]) == t).any() else None) for t in ('osm', 'bas', 'tie')})
    rep = {}
    for h in sorted(P):
        p = P[h]
        rr = [(o['t'], round(float(r), 2), o['lab']) for o, r in zip(obs, res) if o['fr'] == h or o.get('fr2') == h]
        sc = 1 / np.hypot(p[0], p[2] if len(p) == 6 else p[1]) if len(p) == 6 else 1 / np.hypot(p[0], p[1])
        rep[h] = dict(n=len(rr), med=float(np.median([r[1] for r in rr])) if rr else None, mx=max([r[1] for r in rr]) if rr else None,
                      by={t: sum(1 for r in rr if r[0] == t) for t in ('osm', 'bas', 'tie')}, scale=float(sc))
        if verbose: print(h, rep[h])
    json.dump({h: list(map(float, p)) for h, p in P.items()}, open(SP + 'lph/' + out, 'w'), indent=1)
    pickle.dump(dict(obs=obs, res=res, P=P), open(SP + 'lph/' + out.replace('.json', '.pkl'), 'wb'))
    return P, obs, res

if __name__ == '__main__':
    main(model=sys.argv[1] if len(sys.argv) > 1 else 'sim')
