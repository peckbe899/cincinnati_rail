"""Joint georeference of the 1904 Sanborn basin sheets (deck method).
Frames: CHPL scans (vol 1, vol 2) affine with soft similarity priors; LOC scans (vol 3) similarity.
Observations: OSM corners (surviving streets), 1912 corners (demolished streets, low weight),
ties between the same named intersection on overlapping sheets. Deck sheets held fixed.
"""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import json, sys, os, pickle, collections, itertools, numpy as np
HERE = _ws.data_dir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, _ws.code_dir(HERE)); sys.path.insert(0, _ws.code_dir(os.path.dirname(HERE)))
from load import load, DECK
from names import key, base, key2
SP = _ws.DATA
S0 = {'chpl': 1 / 11.19, 'loc': 1 / 19.73}
SIZES = {int(k): v[0] for k, v in json.load(open(os.path.join(HERE, 'sizes.json'))).items()}
def sheet_of(fr): return int(''.join(c for c in fr if c.isdigit()))
def s0_of(fr):
    s = sheet_of(fr); W = SIZES[s][0]
    return S0['loc'] * 6500 / W if 200 <= s < 300 else S0['chpl'] * 4125 / W
def kind(fr): return 'loc' if 200 <= sheet_of(fr) < 300 else 'chpl'
def npar(fr): return 4 if kind(fr) == 'loc' else 6
def apply(p, x, y):
    if len(p) == 6: return p[0] * x + p[1] * y + p[4], p[2] * x + p[3] * y + p[5]
    a, c, tx, ty = p; return a * x + c * y + tx, c * x - a * y + ty
def coef(fr, x, y):
    """rows (E, N) as dicts param-index -> coefficient"""
    if npar(fr) == 6: return {0: x, 1: y, 4: 1}, {2: x, 3: y, 5: 1}
    return {0: x, 1: y, 2: 1}, {0: -y, 1: x, 3: 1}
def sim_to_par(fr, A, B):
    a, c = A.real, A.imag
    return np.array([a, c, c, -a, B.real, B.imag]) if npar(fr) == 6 else np.array([a, c, B.real, B.imag])
def fit_sim(src, dst):
    z = src[:, 0] - 1j * src[:, 1]; w = dst[:, 0] + 1j * dst[:, 1]
    M = np.c_[z, np.ones_like(z)]; sol, *_ = np.linalg.lstsq(M, w, rcond=None); return sol[0], sol[1]
def ransac_sim(src, dst, s0, thr=12.0, min_in=3, rng=np.random.default_rng(0)):
    n = len(src)
    if n < 2: return None
    pairs = list(itertools.combinations(range(n), 2))
    if len(pairs) > 800: pairs = [tuple(rng.choice(n, 2, replace=False)) for _ in range(800)]
    best = None
    for i, j in pairs:
        if np.hypot(*(src[i] - src[j])) < 300: continue
        A, B = fit_sim(src[[i, j]], dst[[i, j]])
        if not (0.85 < abs(A) / s0 < 1.18): continue
        z = src[:, 0] - 1j * src[:, 1]; r = np.abs(A * z + B - (dst[:, 0] + 1j * dst[:, 1]))
        inl = r < thr
        sc = inl.sum() - 1e-3 * r[inl].sum()
        if best is None or sc > best[0]: best = (sc, inl)
    if best is None or best[1].sum() < min_in: return None
    inl = best[1]
    for _ in range(3):
        A, B = fit_sim(src[inl], dst[inl])
        z = src[:, 0] - 1j * src[:, 1]; r = np.abs(A * z + B - (dst[:, 0] + 1j * dst[:, 1])); inl = r < thr
        if inl.sum() < min_in: return None
    return A, B, inl, r

def main():
    R, O = load()
    R = [r for r in R if r['fr']]
    for r in R: r['k2a'], r['k2b'] = key2(r['a']), key2(r['b']); r['pk'] = tuple(sorted((r['ka'], r['kb'])))
    X = pickle.load(open(os.path.join(HERE, 'osmx.pkl'), 'rb')); osm, t12 = X['osm'], X['t12']
    osmkeys = set(k for p in osm for k in p); t12keys = set(k for p in t12 for k in p)
    def okey(k, keys):
        if k in keys: return [k]
        b = base(k); c = [q for q in keys if base(q) == b]
        return c
    def cands(r):
        """candidate world points for a pick: list of (E, N, src)"""
        out = []
        if r['a'] and '(' in r['a'] or r['b'] and '(' in r['b']:
            if not (r['k2a'] and '|' not in r['k2a'] and r['k2b'] and '|' not in r['k2b']): return out
        if r['ka'] in ('', '?') or r['kb'] in ('', '?'): return out
        for src, D, keys in (('osm', osm, osmkeys), ('t12', t12, t12keys)):
            for A in okey(r['ka'], keys):
                for B in okey(r['kb'], keys):
                    if src == 'osm' and (A in EXC or B in EXC): continue
                    for p in D.get(tuple(sorted((A, B))), []): out.append((p[0], p[1], src, (A, B)))
            if out and src == 'osm': break
        return out
    EXC = set()
    for r in R: r['cand'] = cands(r)
    frames = sorted({r['fr'] for r in R}, key=lambda f: (sheet_of(f), f))
    TF = json.load(open(SP + 'deck/sheet_tf.json'))
    fixed = {f: np.array(TF[f]) for f in frames if f in TF and sheet_of(f) in DECK}
    print('frames', len(frames), 'fixed', sorted(fixed, key=sheet_of))
    byfr = collections.defaultdict(list)
    for i, r in enumerate(R): byfr[r['fr']].append(i)
    bypair = collections.defaultdict(list)
    for i, r in enumerate(R):
        if r['k2a'] and r['k2b']: bypair[tuple(sorted((r['k2a'], r['k2b'])))].append(i)
    SCLK = {"chpl": 11.19 / 11.40, "loc": 19.73 / 20.0}   # pages fit at about 11.4 px/m (CHPL) and 20.0 px/m (LOC)
    P = dict(fixed)
    # ---- initialisation: RANSAC similarity from controls, then propagate through ties
    def try_init(f, use_ties):
        src, dst = [], []
        for i in byfr[f]:
            r = R[i]
            for c in r['cand']: src.append((r['x'], r['y'])); dst.append(c[:2])
            if use_ties and r['k2a'] and r['k2b']:
                for j in bypair[tuple(sorted((r['k2a'], r['k2b'])))]:
                    q = R[j]
                    if q['fr'] != f and q['fr'] in P: src.append((r['x'], r['y'])); dst.append(apply(P[q['fr']], q['x'], q['y']))
        if len(src) < 3: return None
        res = ransac_sim(np.array(src, float), np.array(dst, float), s0_of(f), thr=15.0, min_in=3)
        if res is None: return None
        A, B, inl, rr = res
        return sim_to_par(f, A, B), int(inl.sum()), len(src)
    log = []
    for f in frames:
        if f in P: continue
        t = try_init(f, False)
        if t and t[1] >= 4: P[f] = t[0]; log.append((f, 'ctrl', t[1], t[2]))
    for rnd in range(12):
        prog = False
        for f in frames:
            if f in P: continue
            t = try_init(f, True)
            if t: P[f] = t[0]; log.append((f, f'tie{rnd}', t[1], t[2])); prog = True
        if not prog: break
    # fallback for frames with too few points: rotation and scale of the best-tied initialised frame, translation from ties
    ROT0 = {}
    def rot_of(p): return np.arctan2(p[2], p[0]) if len(p) == 6 else np.arctan2(p[1], p[0])
    for f in frames:
        if f in P: continue
        pts = []; refs = collections.Counter()
        for i in byfr[f]:
            r = R[i]
            if r['k2a'] and r['k2b']:
                for j in bypair[tuple(sorted((r['k2a'], r['k2b'])))]:
                    q = R[j]
                    if q['fr'] != f and q['fr'] in P: pts.append(((r['x'], r['y']), apply(P[q['fr']], q['x'], q['y']))); refs[q['fr']] += 1
        if not pts: continue
        ref = refs.most_common(1)[0][0]; th = rot_of(P[ref]); A = s0_of(f) * np.exp(1j * th)
        B = np.mean([complex(*w) - A * (x - 1j * y) for (x, y), w in pts])
        P[f] = sim_to_par(f, A, B); ROT0[f] = th; log.append((f, 'fallback', len(pts), ref))
    # frames whose rotation the solve cannot pin (picks on two parallel lines, few ties): rotation from their tied neighbours
    # sheet 18: Carr and Freeman are its only N-S lines; the free solve rotated it 15 deg (OSM check, items A057/A062)
    ROT_FIX = {'18': -3.5}
    for f, deg in ROT_FIX.items():
        pts = []
        for i in byfr[f]:
            r = R[i]
            if r['k2a'] and r['k2b']:
                for j in bypair[tuple(sorted((r['k2a'], r['k2b'])))]:
                    q = R[j]
                    if q['fr'] != f and q['fr'] in P and q['fr'] not in ROT_FIX: pts.append(((r['x'], r['y']), apply(P[q['fr']], q['x'], q['y'])))
        th = np.radians(deg); A = s0_of(f) * SCLK[kind(f)] * np.exp(1j * th)
        B = np.mean([complex(*w) - A * (x - 1j * y) for (x, y), w in pts])
        P[f] = sim_to_par(f, A, B); ROT0[f] = th; log.append((f, 'rotfix', len(pts)))
    miss = [f for f in frames if f not in P]
    print('init', len(P), 'missing', miss, 'fallback', list(ROT0))
    # ---- joint least squares with gating and Huber IRLS
    free = [f for f in frames if f in P and f not in fixed]
    off = {}; n = 0
    for f in free: off[f] = n; n += npar(f)
    SIG = {'osm': 2.0, 't12': 6.0, 'tie': 1.5}
    def build_obs(gate):
        obs = []   # (type, i, j or None, E, N, sigma)
        used = set()
        for i, r in enumerate(R):
            f = r['fr']
            if f not in P or not r['cand'] or f in fixed: continue
            e, nn = apply(P[f], r['x'], r['y'])
            best = min(r['cand'], key=lambda c: np.hypot(c[0] - e, c[1] - nn))
            d = np.hypot(best[0] - e, best[1] - nn)
            if d < gate: obs.append(('c', i, None, best[0], best[1], SIG[best[2]], best[2], best[3]))
        for pk, idx in bypair.items():
            for i, j in itertools.combinations(idx, 2):
                fi, fj = R[i]['fr'], R[j]['fr']
                if fi == fj or fi not in P or fj not in P: continue
                ei, ni = apply(P[fi], R[i]['x'], R[i]['y']); ej, nj = apply(P[fj], R[j]['x'], R[j]['y'])
                d = np.hypot(ei - ej, ni - nj)
                if d > gate: continue
                # mutual nearest among same-pair picks of the two frames
                oi = [k for k in idx if R[k]['fr'] == fj]; oj = [k for k in idx if R[k]['fr'] == fi]
                def dd(a, b):
                    ea, na = apply(P[R[a]['fr']], R[a]['x'], R[a]['y']); eb, nb = apply(P[R[b]['fr']], R[b]['x'], R[b]['y']); return np.hypot(ea - eb, na - nb)
                if min(oi, key=lambda k: dd(i, k)) != j or min(oj, key=lambda k: dd(j, k)) != i: continue
                if fi in fixed and fj in fixed: continue
                if fi in fixed: obs.append(('c', j, None, ei, ni, SIG['tie'], 'tie-fixed'))
                elif fj in fixed: obs.append(('c', i, None, ej, nj, SIG['tie'], 'tie-fixed'))
                else: obs.append(('t', i, j, 0, 0, SIG['tie'], 'tie'))
        return obs
    def resid(o):
        r = R[o[1]]; e, nn = apply(P[r['fr']], r['x'], r['y'])
        if o[0] == 'c': return np.hypot(e - o[3], nn - o[4])
        q = R[o[2]]; e2, n2 = apply(P[q['fr']], q['x'], q['y']); return np.hypot(e - e2, nn - n2)
    def solve(obs, iters=8, delta=2.5):
        global_w = np.ones(len(obs))
        for it in range(iters):
            rows, cols, vals, rhs, wts = [], [], [], [], []
            rid = 0
            def add(cdict, b, w):
                nonlocal rid
                for (f, k), v in cdict.items(): rows.append(rid); cols.append(off[f] + k); vals.append(v)
                rhs.append(b); wts.append(w); rid += 1
            for oi, o in enumerate(obs):
                w = global_w[oi] / o[5] ** 2
                r = R[o[1]]; f = r['fr']; cE, cN = coef(f, r['x'], r['y'])
                if o[0] == 'c':
                    add({(f, k): v for k, v in cE.items()}, o[3], w); add({(f, k): v for k, v in cN.items()}, o[4], w)
                else:
                    q = R[o[2]]; g = q['fr']; dE, dN = coef(g, q['x'], q['y'])
                    for c1, c2 in ((cE, dE), (cN, dN)):
                        d = {(f, k): v for k, v in c1.items()}
                        for k, v in c2.items(): d[(g, k)] = d.get((g, k), 0) - v
                        add(d, 0, w)
            L = 4000.0
            for f in free:
                s0 = s0_of(f); p = P[f]
                if f in WEAK:
                    th = WEAK[f]; i0, i2 = (0, 2) if npar(f) == 6 else (0, 1)
                    add({(f, i2): L * np.cos(th), (f, i0): -L * np.sin(th)}, 0, 1 / 0.5 ** 2)
                if npar(f) == 6:
                    add({(f, 1): L, (f, 2): -L}, 0, 1 / 2.0 ** 2); add({(f, 3): L, (f, 0): L}, 0, 1 / 2.0 ** 2)
                    nx = np.hypot(p[0], p[2]); add({(f, 0): L * p[0] / nx, (f, 2): L * p[2] / nx}, L * s0 * SCLK[kind(f)], 1 / 4.0 ** 2)
                else:
                    nx = np.hypot(p[0], p[1]); add({(f, 0): L * p[0] / nx, (f, 1): L * p[1] / nx}, L * s0 * SCLK[kind(f)], 1 / 4.0 ** 2)
            from scipy.sparse import csr_matrix
            from scipy.sparse.linalg import lsqr
            A = csr_matrix((vals, (rows, cols)), shape=(rid, n)); b = np.array(rhs); W = np.sqrt(np.array(wts))
            from scipy.sparse import diags
            Aw = diags(W) @ A; x0 = np.concatenate([P[f] for f in free])
            sol = lsqr(Aw, b * W - Aw @ x0, atol=1e-14, btol=1e-14, iter_lim=20000)[0] + x0
            for f in free: P[f] = sol[off[f]:off[f] + npar(f)]
            res = np.array([resid(o) for o in obs])
            global_w = np.where(res < delta, 1.0, delta / np.maximum(res, 1e-9))
        return res
    from osmx import lines_osm
    from shapely.geometry import Point
    from shapely.ops import unary_union
    OL = {k: unary_union(v) for k, v in lines_osm().items()}
    def normal(k, e, n):
        g = OL[k]; d = g.project(Point(e, n)); a = g.interpolate(max(0, d - 15)); b = g.interpolate(d + 15)
        t = np.array([b.x - a.x, b.y - a.y]); t /= (np.hypot(*t) + 1e-9); return np.array([-t[1], t[0]])
    bias_log = {}
    WEAK = {}
    def weak_frames(obs):
        pts = collections.defaultdict(set)
        for o in obs:
            pts[R[o[1]]['fr']].add(o[1])
            if o[2] is not None: pts[R[o[2]]['fr']].add(o[2])
        W = {}
        for f in free:
            xy = np.array([(R[i]['x'], R[i]['y']) for i in pts[f]]) if pts[f] else np.zeros((0, 2))
            spread = np.ptp(xy, axis=0).min() if len(xy) >= 2 else 0
            if len(xy) < 3 or spread < 600: W[f] = ROT0.get(f, rot_of(P[f]))
        return W
    for rnd in range(4):
        for gate in (25.0, 15.0, 10.0):
            obs = build_obs(gate); WEAK.clear(); WEAK.update(weak_frames(obs)); WEAK.update({f: np.radians(d) for f, d in ROT_FIX.items()}); res = solve(obs)
            print(f'round {rnd} gate {gate}: obs {len(obs)} ({dict(collections.Counter(o[6] for o in obs))}) median {np.median(res):.2f} p90 {np.percentile(res, 90):.2f} max {res.max():.1f}')
        # per-street bias of OSM controls (streets widened or moved since 1904)
        proj = collections.defaultdict(list)
        for o in obs:
            if o[6] != 'osm': continue
            r = R[o[1]]; e, nn = apply(P[r['fr']], r['x'], r['y']); v = np.array([e - o[3], nn - o[4]])
            for k in o[7]: proj[k].append(float(v @ normal(k, o[3], o[4])))
        new = {}
        for k, v in proj.items():
            m = np.median(v); q = np.percentile(np.abs(v), 75)
            if (len(v) >= 3 and (abs(m) > 2.0 or q > 5.0)) or (len(v) < 3 and abs(m) > 4.0): new[k] = (round(float(m), 1), len(v), round(float(q), 1))
        print('biased streets:', new)
        if not new: break
        bias_log.update(new); EXC |= set(new)
        for r in R: r['cand'] = cands(r)
    json.dump(bias_log, open(os.path.join(HERE, 'osm_biased.json'), 'w'), indent=0)
    # per-frame report
    rep = {}
    for f in frames:
        if f not in P: continue
        rr = [resid(o) for o in obs if R[o[1]]['fr'] == f or (o[2] is not None and R[o[2]]['fr'] == f)]
        nc = sum(1 for o in obs if o[0] == 'c' and R[o[1]]['fr'] == f and o[6] in ('osm', 't12'))
        p = P[f]
        if len(p) == 6: sc = (1 / np.hypot(p[0], p[2]), 1 / np.hypot(p[1], p[3])); rot = np.degrees(np.arctan2(p[2], p[0]))
        else: sc = (1 / np.hypot(p[0], p[1]),) * 2; rot = np.degrees(np.arctan2(p[1], p[0]))
        rep[f] = dict(n=len(rr), nc=nc, med=float(np.median(rr)) if rr else None, mx=float(max(rr)) if rr else None, pxm=[round(sc[0], 2), round(sc[1], 2)], rot=round(float(rot), 2), fixed=f in fixed)
    json.dump({f: list(map(float, p)) for f, p in P.items()}, open(os.path.join(HERE, 'tf.json'), 'w'), indent=0)
    json.dump(rep, open(os.path.join(HERE, 'report.json'), 'w'), indent=0)
    pickle.dump(dict(obs=obs, R=R), open(os.path.join(HERE, 'obs.pkl'), 'wb'))
    for f in frames:
        if f in rep: print(f, rep[f])
if __name__ == '__main__': main()
