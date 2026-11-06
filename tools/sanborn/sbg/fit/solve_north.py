"""Joint georeference of the 1904 Sanborn sheets north of the basin (Camp Washington, Northside, South Cumminsville).
Adapted from solve.py (deck method). Frames: vol 3 sheets 235-305 and vol 6 sheets 601-635 (LOC scans), one similarity
per frame; the inset panels of 627 and 628 are separate frames (627i, 628i; main panels 627m, 628m).
Fixed: every basin frame in tf.json and the deck sheets 233, 234, 245, 246, 253, 254 (deck/sheet_tf.json).
Observations: ties between the same named crossing on two frames (new-new and new-fixed); OSM corners of surviving
streets (basin/osm_basin.geojson, reaches about N 4,336,220); 1912 survey corners (picks12/*.json), the main control north
of the OSM limit and, south of it, used where OSM has no corner or the street is biased (widened or realigned since 1904).
Scale: the printed bars on both volumes read 50 ft to the inch (200 ft = 1193-1216 px, 19.6-19.95 px/m); free fits run
19.7-20.2 px/m, so the prior is 20.0 px/m for every frame (as the LOC pages of the basin fit).
RANSAC start, gates 25/15/10 m, Huber reweighting, per-street OSM bias rule (log 10n.5), weak-frame rotation pins (10o.4).
Writes tf_north.json (new frames only, same format as tf.json), report_north.json and obs_north.pkl.
"""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', '..'))); import _ws
import json, sys, os, pickle, collections, itertools, glob, numpy as np
HERE = _ws.data_dir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, _ws.code_dir(HERE)); sys.path.insert(0, _ws.code_dir(os.path.dirname(HERE)))
from load import load
from names import key, base, key2
SP = _ws.DATA
NEW = [233, 234, 235, 236, 245, 246, 247, 253, 254, 255, 272, 273, 274, 275, 279, 280, 281, 282, 287, 288, 289, 293, 294, 295,
       301, 302, 303, 304, 305] + list(range(601, 636))
DECK_NEW = ['233', '234', '245', '246', '253', '254']
PXM = 20.0                      # scale prior, px per metre, both volumes
# printed bars ('Scale of Feet', 50-0-50-100-150, i.e. 200 ft, 50 ft to the inch on every sheet read), full length in px
SCALE_BARS = {'235': 1193, '247': 1193, '273': 1202, '281': 1207, '601': 1216, '603': 1212, '604': 1218, '607': 1194, '608': 1219,
              '609': 1217, '612': 1209, '613': 1197, '614': 1199, '615': 1200, '616': 1200, '618': 1204, '619': 1205, '620': 1197,
              '621': 1204, '625': 1200, '627': 1206, '628': 1201, '629': 1199, '632': 1206}
S0 = 1 / PXM
BBOX = (710300, 4332300, 714800, 4339800)
# spellings that differ between the 1904 sheets, the 1912 survey and OSM (applied to every source)
ALIAS = {'coleraine': 'colerain', 'erhardt': 'ehrhardt', 'jo williams': 'joe williams', 'whitely': 'whiteley', 'doorman': 'dorman'}
# piece qualifiers made consistent across sheets (sheet, name as picked) -> name
RENAME = {
    (301, 'Township Street'): 'Township Street (west of Garrard)',          # 301/302 used the opposite convention to 272/273
    (302, 'Township Street'): 'Township Street (west of Garrard)',
    (302, 'Township Street (east of Garrard)'): 'Township Street',
    (303, 'Bates Avenue'): 'Bates Avenue (west of Colerain)',               # the 50 ft street through to Spring Grove (279)
    (287, 'Bates Avenue'): 'Bates Avenue (east of Colerain)',               # the street on the canal side of Colerain (279)
    (289, 'Bates Avenue'): 'Bates Avenue (east of Colerain)',
    (619, 'Chase Avenue (north leg)'): 'Chase Avenue (west of Virginia)',   # the 25 ft leg meeting Virginia (629)
    (601, 'Johnson Street'): 'Johnson Street (north of Alabama)',           # runs north from 305 onto 601
    (301, 'Johnson Street'): 'Johnson Street (south of Stock)',             # stub from 304 ending at Hopple
}
# 1904 name -> the name the 1912 survey prints for the same street (used only to look up 1912 corners; each pair checked
# against the fitted positions: the 1912 corner lies within 0.2-4 m of the 1904 one)
CTRL12 = {'turner al': 'turner', 'zwick': 'zinck', 'terrace pl': 'burlington pl', 'henry': 'lambston', 'ammond': 'ammon',
          'cypress': 'gorham al', 'hemlock': 'looker al', 'agate al': 'austin al', 'mcmakin': 'marble', 'toeser': 'tozzer',
          'dorman': 'powers', 'follett al': 'enos al', 'dirr al': 'gipsy al', 'earl': 'elmira', 'ennis': 'pitts',
          'kendall al': 'medill al', 'ingot al': 'lingo al', 'bond': 'boyd', 'ludlow pl': 'cornwall pl'}
# 1912 picks whose street name is wrong in picks12: the northside_e reader labelled the canal-side avenue between Brashears
# and Ehrhardt 'Spring Grove'; the survey prints COLERAINE on it (south of Brashears) and Spring Grove is the western avenue
FIX12 = {('northside_e', 'Spring Grove Avenue', b): 'Coleraine Avenue' for b in ('Whitely Street', 'Elmira Avenue', 'Ehrhardt Street', 'Brashears Street')}
# sheet 603 keeps no street that survived to 1912 (Ford, Groub and Geringer are gone) and only one corner (Colerain/Ehrhardt):
# the B&O S.W. crossings of Colerain and Spring Grove, read on the sheet (centreline of the right of way between the bridge
# parapets x the avenue centreline through the picks) and on the 1912 survey (between the bridge marks, on the street-railway
# centre), give it two more control points (about 2-3 m)
EXTRA_PICKS = [(603, 'Colerain Avenue', 'B&O SW Railroad', 2570.0, 1796.0), (603, 'Spring Grove Avenue', 'B&O SW Railroad', 4681.0, 3086.0)]
MANUAL12 = [('Coleraine Avenue', 'B&O SW Railroad', 712466.0, 4336555.0), ('Spring Grove Avenue', 'B&O SW Railroad', 712399.0, 4336455.0),
            # the 628 inset's only corner: Linden runs SSE from Knowlton to Spring Grove (1912: Linden centre x Spring Grove
            # street-railway centre, about 3 m); the inset is drawn in the main panel's orientation (Spring Grove's bearing
            # agrees to 0.1 deg), so it takes the main panel's rotation
            ('Spring Grove Avenue', 'Linden Street', 713521.0, 4337560.0)]
PARTS = (627, 628)              # sheets with an inset panel: frames <sheet>m (main) and <sheet>i (inset)
# frames the solve cannot pin (log 10o.4): rotation from their neighbours
# 236: its controls lie on Freeman (one N-S line) plus McMicken/Warner; the free start rotated it to -8.4 deg, which turned
#      Klotter and Conroy 20 deg off OSM and the 1912 survey; Freeman's direction on basin sheets 225/226 gives -2.6
#      (neighbours 225 -2.6, 226 -2.3, 235 -2.3)
# 295: only two ties, both on Bates Alley 100 m apart, gave -8.1; Bates Alley is straight through 287 and 294 (93.3-93.5 deg),
#      which gives -3.5 (neighbours 293 -4.0, 294 -4.1)
ROT_FIX = {'236': -2.6, '295': -3.5}
SIG = {'osm': 2.0, 't12': 3.0, 'tie': 1.5}
def K(n):
    k = key(n); return ALIAS.get(k, k)
def K2(n):
    k = key2(n)
    if k is None: return None
    b, _, q = k.partition(' | '); b = ALIAS.get(b, b)
    return b + (' | ' + q if q else '')
def sheet_of(fr): return int(''.join(c for c in fr if c.isdigit()))
def apply(p, x, y):
    a, c, tx, ty = p; return a * x + c * y + tx, c * x - a * y + ty
def coef(x, y): return {0: x, 1: y, 2: 1}, {0: -y, 1: x, 3: 1}
def sim_to_par(A, B): return np.array([A.real, A.imag, B.real, B.imag])
def rot_of(p): return np.arctan2(p[1], p[0])
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

def controls():
    """OSM corners (inside BBOX) and 1912 survey corners, keyed by sorted aliased key pairs"""
    from osmx import lines_osm, inters
    from shapely.geometry import box
    from shapely.geometry import LineString
    from osmx import ROADS
    B = box(*BBOX); G = collections.defaultdict(list)
    for k, v in lines_osm().items():
        w = [l for l in v if l.intersects(B)]
        if w: G[ALIAS.get(k, k)] += w
    # osm_basin.geojson stops at about N 4,334,300 for local streets; the deck's OSM extract runs on to N 4,335,500
    for f in json.load(open(SP + 'deck/osm_valley.geojson'))['features']:
        p = f['properties']; nm = p.get('name')
        if not nm or p.get('highway') not in ROADS or f['geometry']['type'] != 'LineString': continue
        l = LineString(f['geometry']['coordinates'])
        if l.intersects(B): G[K(nm)].append(l)
    osm = {k: v for k, v in inters(G).items()}
    t12 = collections.defaultdict(list)
    for f in sorted(glob.glob(os.path.join(os.path.dirname(HERE), 'picks12', '*.json'))):
        area = os.path.basename(f)[:-5]
        for p in json.load(open(f))['intersections']:
            a = FIX12.get((area, p['a'], p['b']), p['a']); b = FIX12.get((area, p['b'], p['a']), p['b'])
            t12[tuple(sorted((K(a), K(b))))].append((p['E'], p['N']))
    for a, b, e, n in MANUAL12: t12[tuple(sorted((K(a), K(b))))].append((e, n))
    return osm, dict(t12), G

def main():
    R, O = load()
    R = [r for r in R if r['fr']]
    for s, a, b, x, y in EXTRA_PICKS: R.append(dict(s=s, fr=str(s), a=a, b=b, x=x, y=y, kind='rail'))
    for s in PARTS:   # load.py splits only the basin's split sheets; give the inset picks their own frame
        part = {(p['x'], p['y'], p['a'], p['b']): p.get('part') for p in json.load(open(os.path.join(os.path.dirname(HERE), 'picks', f's{s}.json')))['intersections']}
        for r in R:
            if r['s'] == s: r['fr'] = f"{s}{part[(r['x'], r['y'], r['a'], r['b'])][0]}"
    for r in R:
        r['a'] = RENAME.get((r['s'], r['a']), r['a']); r['b'] = RENAME.get((r['s'], r['b']), r['b'])
        r['ka'], r['kb'] = K(r['a']), K(r['b']); r['k2a'], r['k2b'] = K2(r['a']), K2(r['b'])
    osm, t12, OG = controls()
    osmkeys = set(k for p in osm for k in p); t12keys = set(k for p in t12 for k in p)
    print('controls: osm pairs', len(osm), 'points', sum(map(len, osm.values())), '| 1912 pairs', len(t12), 'points', sum(map(len, t12.values())))
    def okey(k, keys):
        if k in keys: return [k]
        b = base(k); return [q for q in keys if base(q) == b]
    EXC = set()
    def cands(r):
        """candidate world points for a pick: list of (E, N, src, keys); OSM first, 1912 where OSM has none"""
        out = []
        if r['a'] and '(' in r['a'] or r['b'] and '(' in r['b']:
            if not (r['k2a'] and '|' not in r['k2a'] and r['k2b'] and '|' not in r['k2b']): return out
        if r['ka'] in ('', '?') or r['kb'] in ('', '?'): return out
        for src, D, keys in (('osm', osm, osmkeys), ('t12', t12, t12keys)):
            ka, kb = (CTRL12.get(r['ka'], r['ka']), CTRL12.get(r['kb'], r['kb'])) if src == 't12' else (r['ka'], r['kb'])
            for A in okey(ka, keys):
                for B in okey(kb, keys):
                    if A == B or (src == 'osm' and (A in EXC or B in EXC)): continue
                    for p in D.get(tuple(sorted((A, B))), []): out.append((p[0], p[1], src, (A, B)))
            if out and src == 'osm': break
        return out
    TFb = json.load(open(os.path.join(HERE, 'tf.json'))); TFd = json.load(open(SP + 'deck/sheet_tf.json'))
    fixed = {f: np.array(v) for f, v in TFb.items()}
    for f in DECK_NEW: fixed[f] = np.array(TFd[f])
    newfr = sorted({r['fr'] for r in R if r['s'] in NEW and r['fr'] not in fixed}, key=lambda f: (sheet_of(f), f))
    # keep the new frames' picks and the fixed frames' picks (ties); drop picks of unfitted basin frames
    R = [r for r in R if r['fr'] in fixed or r['fr'] in newfr]
    for r in R: r['cand'] = cands(r) if r['fr'] in newfr else []
    print('new frames', len(newfr), newfr)
    byfr = collections.defaultdict(list)
    for i, r in enumerate(R): byfr[r['fr']].append(i)
    bypair = collections.defaultdict(list)
    for i, r in enumerate(R):
        if r['k2a'] and r['k2b'] and r['k2a'] != r['k2b']: bypair[tuple(sorted((r['k2a'], r['k2b'])))].append(i)
    P = dict(fixed)
    def tie_pts(f, exclude=()):
        pts = []; refs = collections.Counter()
        for i in byfr[f]:
            r = R[i]
            if not (r['k2a'] and r['k2b']): continue
            for j in bypair.get(tuple(sorted((r['k2a'], r['k2b']))), []):
                q = R[j]
                if q['fr'] != f and q['fr'] in P and q['fr'] not in exclude:
                    pts.append(((r['x'], r['y']), apply(P[q['fr']], q['x'], q['y']))); refs[q['fr']] += 1
        return pts, refs
    def try_init(f, use_ties):
        src, dst = [], []
        for i in byfr[f]:
            r = R[i]
            for c in r['cand']: src.append((r['x'], r['y'])); dst.append(c[:2])
        if use_ties:
            for s, d in tie_pts(f)[0]: src.append(s); dst.append(d)
        if len(src) < 3: return None
        res = ransac_sim(np.array(src, float), np.array(dst, float), S0, thr=15.0, min_in=3)
        if res is None: return None
        A, B, inl, rr = res
        return sim_to_par(A, B), int(inl.sum()), len(src)
    log = []
    for f in newfr:
        t = try_init(f, False)
        if t and t[1] >= 4: P[f] = t[0]; log.append((f, 'ctrl', t[1], t[2]))
    for rnd in range(12):
        prog = False
        for f in newfr:
            if f in P: continue
            t = try_init(f, True)
            if t: P[f] = t[0]; log.append((f, f'tie{rnd}', t[1], t[2])); prog = True
        if not prog: break
    # fallback: two or more tie/control points -> rotation from them at the prior scale; one point on an inset -> main panel rotation
    ROT0 = {}
    for rnd in range(3):
        for f in newfr:
            if f in P: continue
            pts, refs = tie_pts(f)
            for i in byfr[f]:
                r = R[i]
                for c in r['cand']: pts.append(((r['x'], r['y']), c[:2]))
            if not pts: continue
            src = np.array([p[0] for p in pts], float); dst = np.array([p[1] for p in pts], float)
            if len(pts) >= 2 and np.ptp(src, axis=0).max() >= 300:
                A, B = fit_sim(src, dst); A = S0 * A / abs(A)
            elif f.endswith('i') and f[:-1] + 'm' in P:
                A = S0 * np.exp(1j * rot_of(P[f[:-1] + 'm']))
            else: continue
            z = src[:, 0] - 1j * src[:, 1]; B = np.mean(dst[:, 0] + 1j * dst[:, 1] - A * z)
            P[f] = sim_to_par(A, B); ROT0[f] = float(np.angle(A)); log.append((f, 'fallback', len(pts)))
    for f, deg in ROT_FIX.items():
        pts, _ = tie_pts(f, exclude=ROT_FIX)
        for i in byfr[f]:
            r = R[i]
            for c in r['cand']: pts.append(((r['x'], r['y']), c[:2]))
        A = S0 * np.exp(1j * np.radians(deg))
        B = np.mean([complex(*w) - A * (x - 1j * y) for (x, y), w in pts])
        P[f] = sim_to_par(A, B); ROT0[f] = np.radians(deg); log.append((f, 'rotfix', len(pts)))
    for l in log: print('init', l)
    miss = [f for f in newfr if f not in P]
    print('init', len([f for f in newfr if f in P]), 'missing', miss, 'fallback', list(ROT0))
    free = [f for f in newfr if f in P]
    off = {f: 4 * k for k, f in enumerate(free)}; n = 4 * len(free)
    WEAK = {}
    EXF = set()     # fixed frames whose ties disagree with the controls (left out, reported)
    def build_obs(gate):
        obs = []   # (type, i, j or None, E, N, sigma, src, keys)
        claim = {}  # one control point per pick within a frame: a jogged street read as two T's keeps the nearer one
        for i, r in enumerate(R):
            f = r['fr']
            if f not in off or not r['cand']: continue
            e, nn = apply(P[f], r['x'], r['y'])
            best = min(r['cand'], key=lambda c: np.hypot(c[0] - e, c[1] - nn))
            d = np.hypot(best[0] - e, best[1] - nn)
            if d < gate:
                ck = (f, round(best[0], 1), round(best[1], 1))
                if ck not in claim or claim[ck][0] > d: claim[ck] = (d, ('c', i, None, best[0], best[1], SIG[best[2]], best[2], best[3]))
        obs += [v[1] for v in claim.values()]
        for pk, idx in bypair.items():
            for i, j in itertools.combinations(idx, 2):
                fi, fj = R[i]['fr'], R[j]['fr']
                if fi == fj or fi not in P or fj not in P or (fi not in off and fj not in off) or fi in EXF or fj in EXF: continue
                ei, ni = apply(P[fi], R[i]['x'], R[i]['y']); ej, nj = apply(P[fj], R[j]['x'], R[j]['y'])
                if np.hypot(ei - ej, ni - nj) > gate: continue
                oi = [k for k in idx if R[k]['fr'] == fj]; oj = [k for k in idx if R[k]['fr'] == fi]
                def dd(a, b):
                    ea, na = apply(P[R[a]['fr']], R[a]['x'], R[a]['y']); eb, nb = apply(P[R[b]['fr']], R[b]['x'], R[b]['y']); return np.hypot(ea - eb, na - nb)
                if min(oi, key=lambda k: dd(i, k)) != j or min(oj, key=lambda k: dd(j, k)) != i: continue
                if fi not in off: obs.append(('c', j, i, ei, ni, SIG['tie'], 'tie-fixed', None))
                elif fj not in off: obs.append(('c', i, j, ej, nj, SIG['tie'], 'tie-fixed', None))
                else: obs.append(('t', i, j, 0, 0, SIG['tie'], 'tie', None))
        return obs
    def resid(o):
        r = R[o[1]]; e, nn = apply(P[r['fr']], r['x'], r['y'])
        if o[0] == 'c': return np.hypot(e - o[3], nn - o[4])
        q = R[o[2]]; e2, n2 = apply(P[q['fr']], q['x'], q['y']); return np.hypot(e - e2, nn - n2)
    from scipy.sparse import csr_matrix, diags
    from scipy.sparse.linalg import lsqr
    def solve(obs, iters=8, delta=2.5):
        gw = np.ones(len(obs))
        for it in range(iters):
            rows, cols, vals, rhs, wts = [], [], [], [], []
            rid = 0
            def add(cdict, b, w):
                nonlocal rid
                for (f, k), v in cdict.items(): rows.append(rid); cols.append(off[f] + k); vals.append(v)
                rhs.append(b); wts.append(w); rid += 1
            for oi, o in enumerate(obs):
                w = gw[oi] / o[5] ** 2
                r = R[o[1]]; f = r['fr']; cE, cN = coef(r['x'], r['y'])
                if o[0] == 'c':
                    add({(f, k): v for k, v in cE.items()}, o[3], w); add({(f, k): v for k, v in cN.items()}, o[4], w)
                else:
                    q = R[o[2]]; g = q['fr']; dE, dN = coef(q['x'], q['y'])
                    for c1, c2 in ((cE, dE), (cN, dN)):
                        d = {(f, k): v for k, v in c1.items()}
                        for k, v in c2.items(): d[(g, k)] = d.get((g, k), 0) - v
                        add(d, 0, w)
            L = 4000.0
            for f in free:
                p = P[f]
                if f in WEAK:
                    th = WEAK[f]; add({(f, 1): L * np.cos(th), (f, 0): -L * np.sin(th)}, 0, 1 / 0.5 ** 2)
                nx = np.hypot(p[0], p[1]); add({(f, 0): L * p[0] / nx, (f, 1): L * p[1] / nx}, L * S0, 1 / 4.0 ** 2)
            A = csr_matrix((vals, (rows, cols)), shape=(rid, n)); b = np.array(rhs); W = np.sqrt(np.array(wts))
            Aw = diags(W) @ A; x0 = np.concatenate([P[f] for f in free])
            sol = lsqr(Aw, b * W - Aw @ x0, atol=1e-14, btol=1e-14, iter_lim=20000)[0] + x0
            for f in free: P[f] = sol[off[f]:off[f] + 4]
            res = np.array([resid(o) for o in obs])
            gw = np.where(res < delta, 1.0, delta / np.maximum(res, 1e-9))
        return res
    from shapely.geometry import Point
    from shapely.ops import unary_union
    OL = {k: unary_union(v) for k, v in OG.items()}
    def normal(k, e, n):
        g = OL[k]; d = g.project(Point(e, n)); a = g.interpolate(max(0, d - 15)); b = g.interpolate(d + 15)
        t = np.array([b.x - a.x, b.y - a.y]); t /= (np.hypot(*t) + 1e-9); return np.array([-t[1], t[0]])
    def weak_frames(obs):
        pts = collections.defaultdict(set)
        for o in obs:
            if R[o[1]]['fr'] in off: pts[R[o[1]]['fr']].add(o[1])
            if o[2] is not None and R[o[2]]['fr'] in off: pts[R[o[2]]['fr']].add(o[2])
        W = {}
        for f in free:
            xy = np.array([(R[i]['x'], R[i]['y']) for i in pts[f]]) if pts[f] else np.zeros((0, 2))
            spread = np.ptp(xy, axis=0).min() if len(xy) >= 2 else 0
            if len(xy) < 3 or spread < 600: W[f] = ROT0.get(f, rot_of(P[f]))
        return W
    bias_log = {}; fixed_log = {}
    for rnd in range(8):
        for gate in (25.0, 15.0, 10.0):
            obs = build_obs(gate); WEAK.clear(); WEAK.update(weak_frames(obs)); WEAK.update({f: np.radians(d) for f, d in ROT_FIX.items()}); res = solve(obs)
            print(f'round {rnd} gate {gate}: obs {len(obs)} ({dict(collections.Counter(o[6] for o in obs))}) median {np.median(res):.2f} p90 {np.percentile(res, 90):.2f} max {res.max():.1f}')
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
        # fixed frames whose ties sit consistently off the controls (two or more ties, median offset over 4 m): drop the worst
        fv = collections.defaultdict(list)
        for o in obs:
            if o[6] != 'tie-fixed': continue
            r = R[o[1]]; e, nn = apply(P[r['fr']], r['x'], r['y']); fv[R[o[2]]['fr']].append((e - o[3], nn - o[4]))
        bad = {g: float(np.hypot(*np.median(v, axis=0))) for g, v in fv.items() if len(v) >= 2}
        bad = {g: m for g, m in bad.items() if m > 4.0}
        if bad:
            g = max(bad, key=bad.get); EXF.add(g); fixed_log[g] = (round(bad[g], 1), len(fv[g])); print('fixed frame left out:', g, fixed_log[g])
        if not new and not bad: break
        bias_log.update(new); EXC.update(new)
        for r in R:
            if r['fr'] in off: r['cand'] = cands(r)
    print('weak frames (rotation pinned):', {f: round(float(np.degrees(t)), 2) for f, t in WEAK.items()})
    # dropped observations: control candidates and same-name ties left out at the final gate
    final = obs; used_c = {o[1] for o in final if o[6] in ('osm', 't12')}
    used_t = {tuple(sorted((o[1], o[2]))) for o in final if o[2] is not None}
    dropped = []
    for i, r in enumerate(R):
        if r['fr'] in off and r['cand'] and i not in used_c:
            e, nn = apply(P[r['fr']], r['x'], r['y'])
            best = min(r['cand'], key=lambda c: np.hypot(c[0] - e, c[1] - nn))
            d = float(np.hypot(best[0] - e, best[1] - nn))
            dropped.append(dict(type=best[2], frame=r['fr'], a=r['a'], b=r['b'], x=r['x'], y=r['y'], dist=round(d, 1),
                                reason='gate 10 m' if d >= 10 else 'second pick of a jogged crossing (one control point, nearer pick kept)'))
    for pk, idx in bypair.items():
        for i, j in itertools.combinations(idx, 2):
            fi, fj = R[i]['fr'], R[j]['fr']
            if fi == fj or fi not in P or fj not in P or (fi not in off and fj not in off) or fi in EXF or fj in EXF or tuple(sorted((i, j))) in used_t: continue
            ei, ni = apply(P[fi], R[i]['x'], R[i]['y']); ej, nj = apply(P[fj], R[j]['x'], R[j]['y']); d = float(np.hypot(ei - ej, ni - nj))
            # only report pairs that are not explained by a closer same-name partner (jogged streets carry two picks per sheet)
            oi = [k for k in idx if R[k]['fr'] == fj]; oj = [k for k in idx if R[k]['fr'] == fi]
            def dd(a, b):
                ea, na = apply(P[R[a]['fr']], R[a]['x'], R[a]['y']); eb, nb = apply(P[R[b]['fr']], R[b]['x'], R[b]['y']); return np.hypot(ea - eb, na - nb)
            if min(oi, key=lambda k: dd(i, k)) != j or min(oj, key=lambda k: dd(j, k)) != i: continue
            dropped.append(dict(type='tie', frame=fi, frame2=fj, a=R[i]['a'], b=R[i]['b'], dist=round(d, 1)))
    for k, v in bias_log.items(): dropped.append(dict(type='osm-street', street=k, median_offset=v[0], corners=v[1], p75=v[2]))
    for g, v in fixed_log.items(): dropped.append(dict(type='fixed-frame-ties', frame=g, median_offset=v[0], ties=v[1]))
    rep = {}
    for f in newfr:
        if f not in P: rep[f] = dict(fitted=False); continue
        rr = []; cnt = collections.Counter()
        for o in final:
            mine = R[o[1]]['fr'] == f or (o[0] == 't' and R[o[2]]['fr'] == f)
            if mine: rr.append(resid(o)); cnt[o[6]] += 1
        p = P[f]
        rep[f] = dict(fitted=True, pxm=round(float(1 / np.hypot(p[0], p[1])), 3), rot=round(float(np.degrees(rot_of(p))), 2),
                      n=dict(cnt), med=round(float(np.median(rr)), 2) if rr else None, mx=round(float(max(rr)), 2) if rr else None,
                      weak=f in WEAK, init=next((l[1] for l in log if l[0] == f), None))
    restype = collections.defaultdict(list)
    for o in final: restype[o[6]].append(resid(o))
    summary = {t: dict(n=len(v), median=round(float(np.median(v)), 2), p90=round(float(np.percentile(v, 90)), 2), max=round(float(max(v)), 2)) for t, v in restype.items()}
    json.dump({f: list(map(float, P[f])) for f in newfr if f in P}, open(os.path.join(HERE, 'tf_north.json'), 'w'), indent=0)
    json.dump(dict(frames=rep, residuals=summary, not_fitted=miss + ['605 (no intersections picked)'], dropped=dropped,
                   scale_prior_pxm=PXM, rot_fix=ROT_FIX,
                   scale_bars_pxm={k: round(v / 60.96, 2) for k, v in SCALE_BARS.items()},
                   fitted_pxm_median={'vol3': round(float(np.median([rep[f]['pxm'] for f in rep if rep[f].get('fitted') and sheet_of(f) < 600 and not rep[f]['weak']])), 2),
                                      'vol6': round(float(np.median([rep[f]['pxm'] for f in rep if rep[f].get('fitted') and sheet_of(f) >= 600 and not rep[f]['weak']])), 2)}), open(os.path.join(HERE, 'report_north.json'), 'w'), indent=1)
    pickle.dump(dict(obs=final, R=R, P={f: P[f] for f in newfr if f in P}), open(os.path.join(HERE, 'obs_north.pkl'), 'wb'))
    print('residuals by type', summary)
    for f in newfr: print(f, rep[f])
    print('dropped', len(dropped))
if __name__ == '__main__': main()
