"""Joint georeference of the deck sheets and the north sheets (Camp Washington, Northside, South Cumminsville), basin method.
Adapted from sbg/fit/solve_north.py. Basin frames (sbg/fit/tf.json) fixed; everything else free:
  deck vol 1 (CHPL scans, resized pages): affine with soft similarity priors, scale prior 11.40 px/m (4125 px pages)
  deck vol 3 / vol 5 and north vol 3 / vol 6 (LOC scans): similarity, scale prior 20.0 px/m
Observations: ties between the same named crossing on two frames; OSM corners of surviving streets; 1912 survey corners
(picks12, plus the traced 1912 basin streets at low weight); inside the Lower Price Hill block (State Ave - Western Ave,
Gest St - river; Ben 2026-10-12) the 1922 plates 3, 6, 26, 29 (lph/tf22_aff.json) are the control; old deck observations
(deck/obs.json): ties between block corners, points on OSM lines (L:) and 1912 lines (G:), hand-read world points, except
inside the block (only L: lines kept) and the 6th1912 line (about 20 m off, log 10s / 12).
Writes lph/tf_all.json, lph/report_all.json, lph/obs_all.pkl.
"""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, os, pickle, collections, itertools, glob, numpy as np
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'sbg/fit'); sys.path.insert(0, _ws.CODE + 'sbg'); sys.path.insert(0, _ws.CODE + 'lph')
from load import load
from names import key, base, key2
OUT = SP + 'lph/'
NORTH = [235, 236, 247, 255, 272, 273, 274, 275, 279, 280, 281, 282, 287, 288, 289, 293, 294, 295, 301, 302, 303, 304, 305] + list(range(601, 636))
DECK = [33, 34, 35, 47, 57, 58, 67, 68, 69, 77, 201, 202, 211, 212, 221, 222, 233, 234, 245, 246, 253, 254,
        460, 461, 462, 463, 464, 466, 467, 468, 491, 492, 493, 494, 495, 496, 504, 505, 511, 512, 513, 514, 519, 520, 522]
# basin sheets 223 and 224 (Brighton, Harrison Ave): their ties sat 5-17 m off the 1912 survey, OSM and deck sheet 234, so
# they are refitted here with the rest (2026-10-13)
BASIN_REFIT = [223, 224]
FREE = set(NORTH) | set(DECK) | set(BASIN_REFIT)
BOXSHEETS = {33, 34, 35, 47, 460, 461, 462, 463, 464, 466, 467, 468}
def in_box(e, n): return 711400 <= e <= 712870 and 4330250 <= n <= 4331640
PXM = {'loc': 20.0, 'chpl': 11.40}
BBOX = (710300, 4330200, 714800, 4339800)
ALIAS = {'coleraine': 'colerain', 'erhardt': 'ehrhardt', 'jo williams': 'joe williams', 'whitely': 'whiteley', 'doorman': 'dorman',
         'saint michael': 'st michael', 'strebler': 'staebler', 'vanhorne': 'vanhorn', 'dutten': 'dutton', 'iroquis': 'iroquois'}
RENAME = {
    (301, 'Township Street'): 'Township Street (west of Garrard)', (302, 'Township Street'): 'Township Street (west of Garrard)',
    (302, 'Township Street (east of Garrard)'): 'Township Street',
    (303, 'Bates Avenue'): 'Bates Avenue (west of Colerain)', (287, 'Bates Avenue'): 'Bates Avenue (east of Colerain)',
    (289, 'Bates Avenue'): 'Bates Avenue (east of Colerain)',
    (619, 'Chase Avenue (north leg)'): 'Chase Avenue (west of Virginia)',
    (601, 'Johnson Street'): 'Johnson Street (north of Alabama)', (301, 'Johnson Street'): 'Johnson Street (south of Stock)',
}
# same crossing printed under different names on two sheets: (sheet, a, b) -> (a, b)
RENAME_PAIR = {(514, 'Western Avenue', 'Fairmount Avenue'): ('Beekman Street', 'Fairmount Avenue')}
# 1904 name -> the name used by the controls (1912 survey, 1922 plates, OSM) for the same street
CTRL = {'turner al': 'turner', 'zwick': 'zinck', 'terrace pl': 'burlington pl', 'henry': 'lambston', 'ammond': 'ammon',
        'cypress': 'gorham al', 'hemlock': 'looker al', 'agate al': 'austin al', 'mcmakin': 'marble', 'toeser': 'tozzer',
        'dorman': 'powers', 'follett al': 'enos al', 'dirr al': 'gipsy al', 'earl': 'elmira', 'ennis': 'pitts',
        'kendall al': 'medill al', 'ingot al': 'lingo al', 'bond': 'boyd', 'ludlow pl': 'cornwall pl', 'german': 'english'}
FIX12 = {('northside_e', 'Spring Grove Avenue', b): 'Coleraine Avenue' for b in ('Whitely Street', 'Elmira Avenue', 'Ehrhardt Street', 'Brashears Street')}
EXTRA_PICKS = [(603, 'Colerain Avenue', 'B&O SW Railroad', 2570.0, 1796.0), (603, 'Spring Grove Avenue', 'B&O SW Railroad', 4681.0, 3086.0)]
MANUAL12 = [('Coleraine Avenue', 'B&O SW Railroad', 712466.0, 4336555.0), ('Spring Grove Avenue', 'B&O SW Railroad', 712399.0, 4336455.0),
            ('Spring Grove Avenue', 'Linden Street', 713521.0, 4337560.0)]
# 492: two crossings only, both near Lehman; State Avenue is drawn vertical on the page and its OSM centreline bears 33.7 deg
#      there (page up -> bearing b gives rotation -b)
ROT_FIX = {'236': -2.6, '295': -3.5, '492': -33.7}
SIG = {'osm': 2.0, 'p22': 2.0, 't12': 3.0, 'b12': 6.0, 'tie': 1.5, 'oldw': 3.0, 'oldt': 2.5, 'line': 3.0}
CHPL = {33, 34, 35, 47, 57, 58, 67, 68, 69, 77}
SIZES = {}
def page_w(s):
    if s not in SIZES:
        from PIL import Image; Image.MAX_IMAGE_PIXELS = None
        from sb import find
        SIZES[s] = Image.open(find(s)).size[0]
    return SIZES[s]
def K(n):
    k = key(n); return ALIAS.get(k, k)
def K2(n):
    k = key2(n)
    if k is None: return None
    b, _, q = k.partition(' | '); b = ALIAS.get(b, b)
    return b + (' | ' + q if q else '')
def sheet_of(fr): return int(''.join(c for c in str(fr) if c.isdigit()))
def kind(fr): return 'chpl' if sheet_of(fr) in CHPL else 'loc'
def npar(fr): return 6 if kind(fr) == 'chpl' else 4
def s0_of(fr):
    s = sheet_of(fr)
    return (4125 / page_w(s)) / PXM['chpl'] if kind(fr) == 'chpl' else 1 / PXM['loc']
def apply(p, x, y):
    if len(p) == 6: return p[0] * x + p[1] * y + p[4], p[2] * x + p[3] * y + p[5]
    a, c, tx, ty = p; return a * x + c * y + tx, c * x - a * y + ty
def coef(fr, x, y):
    if npar(fr) == 6: return {0: x, 1: y, 4: 1}, {2: x, 3: y, 5: 1}
    return {0: x, 1: y, 2: 1}, {0: -y, 1: x, 3: 1}
def sim_to_par(fr, A, B):
    a, c = A.real, A.imag
    return np.array([a, c, c, -a, B.real, B.imag]) if npar(fr) == 6 else np.array([a, c, B.real, B.imag])
def rot_of(p): return np.arctan2(p[2], p[0]) if len(p) == 6 else np.arctan2(p[1], p[0])
def scale_of(p): return np.hypot(p[0], p[2]) if len(p) == 6 else np.hypot(p[0], p[1])
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
        inl = r < thr; sc = inl.sum() - 1e-3 * r[inl].sum()
        if best is None or sc > best[0]: best = (sc, inl)
    if best is None or best[1].sum() < min_in: return None
    inl = best[1]
    for _ in range(3):
        A, B = fit_sim(src[inl], dst[inl])
        z = src[:, 0] - 1j * src[:, 1]; r = np.abs(A * z + B - (dst[:, 0] + 1j * dst[:, 1])); inl = r < thr
        if inl.sum() < min_in: return None
    return A, B, inl, r

def controls():
    from osmx import lines_osm, inters, ROADS
    from shapely.geometry import box, LineString
    B = box(*BBOX); G = collections.defaultdict(list); seen = set()
    for k, v in lines_osm().items():
        for l in v:
            if l.intersects(B): G[ALIAS.get(k, k)].append(l); seen.add(tuple(l.coords))
    for f in json.load(open(SP + 'deck/osm_valley.geojson'))['features']:
        p = f['properties']; nm = p.get('name')
        if not nm or p.get('highway') not in ROADS or f['geometry']['type'] != 'LineString': continue
        c = tuple(map(tuple, f['geometry']['coordinates']))
        if c in seen: continue
        l = LineString(c)
        if l.intersects(B): G[K(nm)].append(l); seen.add(c)
    osm = {k: v for k, v in inters(G).items()}
    t12 = collections.defaultdict(list)
    for f in sorted(glob.glob(SP + 'sbg/picks12/*.json')):
        area = os.path.basename(f)[:-5]
        for p in json.load(open(f))['intersections']:
            a = FIX12.get((area, p['a'], p['b']), p['a']); b = FIX12.get((area, p['b'], p['a']), p['b'])
            t12[tuple(sorted((K(a), K(b))))].append((p['E'], p['N']))
    for a, b, e, n in MANUAL12: t12[tuple(sorted((K(a), K(b))))].append((e, n))
    b12 = collections.defaultdict(list)
    for k, v in pickle.load(open(SP + 'sbg/fit/osmx.pkl', 'rb'))['t12'].items():
        b12[tuple(sorted((ALIAS.get(k[0], k[0]), ALIAS.get(k[1], k[1]))))] += [tuple(map(float, q)) for q in v]
    from ref22 import ref
    p22 = collections.defaultdict(list)
    for k, v in ref().items():
        kk = tuple(sorted((ALIAS.get(k[0], k[0]), ALIAS.get(k[1], k[1]))))
        for q in v:
            if in_box(*q): p22[kk].append((float(q[0]), float(q[1])))
    return osm, dict(t12), dict(b12), dict(p22), G

def line_geom(name):
    from shapely.geometry import LineString
    if name.startswith('G:'): return LineString(json.load(open(SP + 'deck/lines1912.json'))[name[2:]])
    sys.path.insert(0, _ws.CODE + 'deck'); from xs import geom; return geom(name[2:])

def main():
    R, _ = load()
    R = [r for r in R if r['fr'] and r['s'] not in FREE or r['s'] in FREE]
    for s, a, b, x, y in EXTRA_PICKS: R.append(dict(s=s, fr=str(s), a=a, b=b, x=x, y=y, kind='rail'))
    # panels: any free sheet whose picks carry a 'part' gets one frame per panel
    for s in sorted(FREE):
        f = SP + f'sbg/picks/s{s}.json'
        if not os.path.exists(f): continue
        part = {(p['x'], p['y'], p['a'], p['b']): p.get('part') for p in json.load(open(f))['intersections']}
        if not any(part.values()): continue
        for r in R:
            if r['s'] == s:
                pt = part.get((r['x'], r['y'], r['a'], r['b']))
                if pt: r['fr'] = f"{s}{pt[0]}"
    for r in R:
        r['a'] = RENAME.get((r['s'], r['a']), r['a']); r['b'] = RENAME.get((r['s'], r['b']), r['b'])
        if (r['s'], r['a'], r['b']) in RENAME_PAIR: r['a'], r['b'] = RENAME_PAIR[(r['s'], r['a'], r['b'])]
        elif (r['s'], r['b'], r['a']) in RENAME_PAIR: r['b'], r['a'] = RENAME_PAIR[(r['s'], r['b'], r['a'])]
        r['ka'], r['kb'] = K(r['a']), K(r['b']); r['k2a'], r['k2b'] = K2(r['a']), K2(r['b'])
    R = [r for r in R if r['fr']]
    osm, t12, b12, p22, OG = controls()
    SRC = {'osm': osm, 't12': t12, 'b12': b12, 'p22': p22}
    KEYS = {s: set(k for p in D for k in p) for s, D in SRC.items()}
    print('controls:', {s: (len(D), sum(map(len, D.values()))) for s, D in SRC.items()})
    def okey(k, keys):
        if k in keys: return [k]
        b = base(k); return [q for q in keys if base(q) == b]
    EXC = set()
    def cands(r, order):
        out = []
        if r['a'] and '(' in r['a'] or r['b'] and '(' in r['b']:
            if not (r['k2a'] and '|' not in r['k2a'] and r['k2b'] and '|' not in r['k2b']): return out
        if r['ka'] in ('', '?') or r['kb'] in ('', '?'): return out
        for src in order:
            ka, kb = CTRL.get(r['ka'], r['ka']), CTRL.get(r['kb'], r['kb'])
            for A in okey(ka, KEYS[src]):
                for B in okey(kb, KEYS[src]):
                    if A == B or (src == 'osm' and (A in EXC or B in EXC)): continue
                    for p in SRC[src].get(tuple(sorted((A, B))), []):
                        if src == 'p22' or not in_box(*p) or sheet_of(r['fr']) not in BOXSHEETS: out.append((p[0], p[1], src, (A, B)))
            if out: break
        return out
    ORDER_BOX = ('p22', 'osm', 't12'); ORDER = ('osm', 't12', 'b12')
    TFb = json.load(open(SP + 'sbg/fit/tf.json'))
    fixed = {f: np.array(v) for f, v in TFb.items() if sheet_of(f) not in FREE}
    newfr = sorted({r['fr'] for r in R if r['s'] in FREE}, key=lambda f: (sheet_of(f), f))
    R = [r for r in R if r['fr'] in fixed or r['fr'] in newfr]
    def set_cands():
        for r in R:
            if r['fr'] in newfr: r['cand'] = cands(r, ORDER_BOX if sheet_of(r['fr']) in BOXSHEETS else ORDER)
            else: r['cand'] = []
    set_cands()
    # old deck observations
    OLD = json.load(open(SP + 'deck/obs.json')); oldw, oldt, oldl = [], [], []
    def frame_for(s):
        s = str(s); return s if s in newfr else (s + 'u' if s + 'u' in newfr else None)
    for o in OLD:
        f = frame_for(o['s'])
        if f is None: continue
        inbox = int(o['s']) in BOXSHEETS
        if o['t'] == 'w' and not inbox: oldw.append((f, o['x'], o['y'], o['E'], o['N'], o['lab']))
        elif o['t'] == 'l' and o['line'] != 'G:6th1912' and (not inbox or o['line'].startswith('L:')):
            g = line_geom(o['line'])
            if g is not None: oldl.append((f, o['x'], o['y'], g, o['line']))
        elif o['t'] == 't':
            f2 = frame_for(o['s2'])
            if f2 and not inbox and int(o['s2']) not in BOXSHEETS: oldt.append((f, o['x'], o['y'], f2, o['x2'], o['y2'], o['lab']))
    print('old obs: w', len(oldw), 't', len(oldt), 'l', len(oldl), '| frames', len(newfr))
    byfr = collections.defaultdict(list)
    for i, r in enumerate(R): byfr[r['fr']].append(i)
    bypair = collections.defaultdict(list)
    for i, r in enumerate(R):
        if r['k2a'] and r['k2b'] and r['k2a'] != r['k2b']: bypair[tuple(sorted((r['k2a'], r['k2b'])))].append(i)
    P = dict(fixed)
    def tie_pts(f, exclude=()):
        pts = []
        for i in byfr[f]:
            r = R[i]
            if not (r['k2a'] and r['k2b']): continue
            for j in bypair.get(tuple(sorted((r['k2a'], r['k2b']))), []):
                q = R[j]
                if q['fr'] != f and q['fr'] in P and q['fr'] not in exclude: pts.append(((r['x'], r['y']), apply(P[q['fr']], q['x'], q['y'])))
        for (f1, x1, y1, f2, x2, y2, lab) in oldt:
            if f1 == f and f2 in P and f2 not in exclude: pts.append(((x1, y1), apply(P[f2], x2, y2)))
            if f2 == f and f1 in P and f1 not in exclude: pts.append(((x2, y2), apply(P[f1], x1, y1)))
        return pts
    def ctrl_pts(f):
        pts = [((R[i]['x'], R[i]['y']), c[:2]) for i in byfr[f] for c in R[i]['cand']]
        pts += [((x, y), (e, n)) for (g, x, y, e, n, lab) in oldw if g == f]
        return pts
    def try_init(f, use_ties):
        pts = ctrl_pts(f) + (tie_pts(f) if use_ties else [])
        if len(pts) < 3: return None
        res = ransac_sim(np.array([p[0] for p in pts], float), np.array([p[1] for p in pts], float), s0_of(f), thr=15.0, min_in=3)
        if res is None: return None
        A, B, inl, rr = res
        return sim_to_par(f, A, B), int(inl.sum()), len(pts)
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
    ROT0 = {}
    for rnd in range(3):
        for f in newfr:
            if f in P: continue
            pts = tie_pts(f) + ctrl_pts(f)
            if not pts: continue
            src = np.array([p[0] for p in pts], float); dst = np.array([p[1] for p in pts], float)
            if len(pts) >= 2 and np.ptp(src, axis=0).max() >= 300:
                A, B = fit_sim(src, dst); A = s0_of(f) * A / abs(A)
            elif f[-1].isalpha() and any(g in P for g in newfr if sheet_of(g) == sheet_of(f) and g != f):
                g = next(g for g in newfr if sheet_of(g) == sheet_of(f) and g != f and g in P); A = s0_of(f) * np.exp(1j * rot_of(P[g]))
            else:
                # one point: rotation of the fitted neighbours (frames it shares a crossing with, else the adjacent sheet numbers)
                nb = set()
                for i in byfr[f]:
                    r = R[i]
                    for j in bypair.get(tuple(sorted((r['k2a'] or '', r['k2b'] or ''))), []):
                        if R[j]['fr'] != f and R[j]['fr'] in P: nb.add(R[j]['fr'])
                if not nb: nb = {g for g in P if g in newfr and abs(sheet_of(g) - sheet_of(f)) == 1}
                if not nb: continue
                th = np.angle(np.mean([np.exp(1j * rot_of(P[g])) for g in nb])); A = s0_of(f) * np.exp(1j * th)
            z = src[:, 0] - 1j * src[:, 1]; B = np.mean(dst[:, 0] + 1j * dst[:, 1] - A * z)
            P[f] = sim_to_par(f, A, B); ROT0[f] = float(np.angle(A)); log.append((f, 'fallback', len(pts)))
    for f, deg in ROT_FIX.items():
        pts = tie_pts(f, exclude=ROT_FIX) + ctrl_pts(f)
        A = s0_of(f) * np.exp(1j * np.radians(deg)); B = np.mean([complex(*w) - A * (x - 1j * y) for (x, y), w in pts])
        P[f] = sim_to_par(f, A, B); ROT0[f] = np.radians(deg); log.append((f, 'rotfix', len(pts)))
    for l in log: print('init', l)
    miss = [f for f in newfr if f not in P]
    print('init', len([f for f in newfr if f in P]), 'missing', miss)
    free = [f for f in newfr if f in P]
    off = {}; n = 0
    for f in free: off[f] = n; n += npar(f)
    WEAK = {}; EXF = set()
    def build_obs(gate):
        obs = []   # (type, i, j, E, N, sigma, src, keys)  types: c (control), t (tie), l (line), oc / ot (old)
        claim = {}
        for i, r in enumerate(R):
            f = r['fr']
            if f not in off or not r['cand']: continue
            e, nn = apply(P[f], r['x'], r['y'])
            best = min(r['cand'], key=lambda c: np.hypot(c[0] - e, c[1] - nn)); d = np.hypot(best[0] - e, best[1] - nn)
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
        for k, (f, x, y, e, nn_, lab) in enumerate(oldw):
            if f in off:
                e0, n0 = apply(P[f], x, y)
                if np.hypot(e0 - e, n0 - nn_) < gate: obs.append(('oc', k, None, e, nn_, SIG['oldw'], 'oldw', lab))
        for k, (f, x, y, f2, x2, y2, lab) in enumerate(oldt):
            if f in P and f2 in P and (f in off or f2 in off):
                e1, n1 = apply(P[f], x, y); e2, n2 = apply(P[f2], x2, y2)
                if np.hypot(e1 - e2, n1 - n2) < gate: obs.append(('ot', k, None, 0, 0, SIG['oldt'], 'oldt', lab))
        from shapely.geometry import Point
        for k, (f, x, y, g, lab) in enumerate(oldl):
            if f not in off: continue
            e0, n0 = apply(P[f], x, y); pt = Point(e0, n0); d = g.distance(pt)
            if d < gate:
                s = g.project(pt); a = g.interpolate(max(0, s - 10)); b = g.interpolate(s + 10); ft = g.interpolate(s)
                t = np.array([b.x - a.x, b.y - a.y]); t /= (np.hypot(*t) + 1e-9); nv = np.array([-t[1], t[0]])
                obs.append(('l', k, None, ft.x, ft.y, SIG['line'], 'line', (nv[0], nv[1])))
        return obs
    def resid(o):
        if o[0] == 'oc':
            f, x, y, e, nn_, lab = oldw[o[1]]; e0, n0 = apply(P[f], x, y); return np.hypot(e0 - e, n0 - nn_)
        if o[0] == 'ot':
            f, x, y, f2, x2, y2, lab = oldt[o[1]]; e1, n1 = apply(P[f], x, y); e2, n2 = apply(P[f2], x2, y2); return np.hypot(e1 - e2, n1 - n2)
        if o[0] == 'l':
            f, x, y, g, lab = oldl[o[1]]; e0, n0 = apply(P[f], x, y); return abs((e0 - o[3]) * o[7][0] + (n0 - o[4]) * o[7][1])
        r = R[o[1]]; e, nn = apply(P[r['fr']], r['x'], r['y'])
        if o[0] == 'c': return np.hypot(e - o[3], nn - o[4])
        q = R[o[2]]; e2, n2 = apply(P[q['fr']], q['x'], q['y']); return np.hypot(e - e2, nn - n2)
    from scipy.sparse import csr_matrix, diags
    from scipy.sparse.linalg import lsqr
    def solve(obs, iters=8, delta=2.5):
        gw = np.ones(len(obs))
        for it in range(iters):
            rows, cols, vals, rhs, wts = [], [], [], [], []; rid = 0
            def add(cdict, b, w):
                nonlocal rid
                for (f, k), v in cdict.items(): rows.append(rid); cols.append(off[f] + k); vals.append(v)
                rhs.append(b); wts.append(w); rid += 1
            def tie_rows(f, x, y, g, x2, y2, w):
                cE, cN = coef(f, x, y); dE, dN = coef(g, x2, y2)
                for c1, c2, comp in ((cE, dE, 0), (cN, dN, 1)):
                    d = {}; b = 0.0
                    if f in off: d.update({(f, k): v for k, v in c1.items()})
                    else: b -= apply(P[f], x, y)[comp]
                    if g in off:
                        for k, v in c2.items(): d[(g, k)] = d.get((g, k), 0) - v
                    else: b += apply(P[g], x2, y2)[comp]
                    add(d, b, w)
            for oi, o in enumerate(obs):
                w = gw[oi] / o[5] ** 2
                if o[0] in ('c', 'oc'):
                    if o[0] == 'c': r = R[o[1]]; f, x, y = r['fr'], r['x'], r['y']
                    else: f, x, y = oldw[o[1]][:3]
                    cE, cN = coef(f, x, y)
                    add({(f, k): v for k, v in cE.items()}, o[3], w); add({(f, k): v for k, v in cN.items()}, o[4], w)
                elif o[0] == 't':
                    r, q = R[o[1]], R[o[2]]; tie_rows(r['fr'], r['x'], r['y'], q['fr'], q['x'], q['y'], w)
                elif o[0] == 'ot':
                    f, x, y, f2, x2, y2, lab = oldt[o[1]]; tie_rows(f, x, y, f2, x2, y2, w)
                elif o[0] == 'l':
                    f, x, y, g, lab = oldl[o[1]]; cE, cN = coef(f, x, y); nx, ny = o[7]
                    d = {(f, k): nx * v for k, v in cE.items()}
                    for k, v in cN.items(): d[(f, k)] = d.get((f, k), 0) + ny * v
                    add(d, nx * o[3] + ny * o[4], w)
            L = 4000.0
            for f in free:
                p = P[f]; s0 = s0_of(f)
                if f in WEAK:
                    th = WEAK[f]; i0, i2 = (0, 2) if npar(f) == 6 else (0, 1)
                    add({(f, i2): L * np.cos(th), (f, i0): -L * np.sin(th)}, 0, 1 / 0.5 ** 2)
                if npar(f) == 6:
                    add({(f, 1): L, (f, 2): -L}, 0, 1 / 2.0 ** 2); add({(f, 3): L, (f, 0): L}, 0, 1 / 2.0 ** 2)
                    nx = np.hypot(p[0], p[2]); add({(f, 0): L * p[0] / nx, (f, 2): L * p[2] / nx}, L * s0, 1 / 4.0 ** 2)
                else:
                    nx = np.hypot(p[0], p[1]); add({(f, 0): L * p[0] / nx, (f, 1): L * p[1] / nx}, L * s0, 1 / 4.0 ** 2)
            A = csr_matrix((vals, (rows, cols)), shape=(rid, n)); b = np.array(rhs); W = np.sqrt(np.array(wts))
            Aw = diags(W) @ A; x0 = np.concatenate([P[f] for f in free])
            sol = lsqr(Aw, b * W - Aw @ x0, atol=1e-14, btol=1e-14, iter_lim=40000)[0] + x0
            for f in free: P[f] = sol[off[f]:off[f] + npar(f)]
            res = np.array([resid(o) for o in obs])
            gw = np.where(res < delta, 1.0, delta / np.maximum(res, 1e-9))
        return res
    from shapely.geometry import Point
    from shapely.ops import unary_union
    OL = {k: unary_union(v) for k, v in OG.items()}
    def normal(k, e, n):
        g = OL[k]; d = g.project(Point(e, n)); a = g.interpolate(max(0, d - 15)); b = g.interpolate(d + 15)
        t = np.array([b.x - a.x, b.y - a.y]); t /= (np.hypot(*t) + 1e-9); return np.array([-t[1], t[0]])
    def obs_frames(o):
        if o[0] in ('c', 't'): return [R[o[1]]['fr']] + ([R[o[2]]['fr']] if o[2] is not None else [])
        if o[0] == 'oc': return [oldw[o[1]][0]]
        if o[0] == 'ot': return [oldt[o[1]][0], oldt[o[1]][3]]
        return [oldl[o[1]][0]]
    def obs_xy(o, f):
        if o[0] in ('c', 't'):
            for i in (o[1], o[2]):
                if i is not None and R[i]['fr'] == f: return (R[i]['x'], R[i]['y'])
        if o[0] == 'oc': return oldw[o[1]][1:3]
        if o[0] == 'ot': return oldt[o[1]][1:3] if oldt[o[1]][0] == f else oldt[o[1]][4:6]
        return oldl[o[1]][1:3]
    def weak_frames(obs):
        pts = collections.defaultdict(set)
        for o in obs:
            if o[0] == 'l': continue
            for f in obs_frames(o):
                if f in off: pts[f].add(obs_xy(o, f))
        lp = collections.defaultdict(list)
        for o in obs:
            if o[0] == 'l' and oldl[o[1]][0] in off: lp[oldl[o[1]][0]].append(oldl[o[1]][1:3])
        W = {}
        for f in free:
            xy = np.array(sorted(pts[f])) if pts[f] else np.zeros((0, 2))
            spread = np.ptp(xy, axis=0).min() if len(xy) >= 2 else 0
            # one point plus points on one line spread along the page fix the rotation too
            lspread = np.ptp(np.array(lp[f]), axis=0).max() if len(lp[f]) >= 2 else 0
            if (len(xy) < 3 or spread < 600) and not (len(xy) >= 1 and lspread >= 2000): W[f] = ROT0.get(f, rot_of(P[f]))
        return W
    bias_log = {}; fixed_log = {}
    for rnd in range(8):
        for gate in (25.0, 15.0, 10.0):
            obs = build_obs(gate); WEAK.clear(); WEAK.update(weak_frames(obs)); WEAK.update({f: np.radians(d) for f, d in ROT_FIX.items()}); res = solve(obs)
            print(f'round {rnd} gate {gate}: obs {len(obs)} ({dict(collections.Counter(o[6] for o in obs))}) median {np.median(res):.2f} p90 {np.percentile(res, 90):.2f} max {res.max():.1f}', flush=True)
        proj = collections.defaultdict(list)
        for o in obs:
            if o[6] != 'osm': continue
            r = R[o[1]]; e, nn = apply(P[r['fr']], r['x'], r['y']); v = np.array([e - o[3], nn - o[4]])
            for k in o[7]:
                if k in OL: proj[k].append(float(v @ normal(k, o[3], o[4])))
        new = {}
        for k, v in proj.items():
            m = np.median(v); q = np.percentile(np.abs(v), 75)
            if (len(v) >= 3 and (abs(m) > 2.0 or q > 5.0)) or (len(v) < 3 and abs(m) > 4.0): new[k] = (round(float(m), 1), len(v), round(float(q), 1))
        new = {k: v for k, v in new.items() if k not in EXC}
        print('biased streets:', new)
        fv = collections.defaultdict(list)
        for o in obs:
            if o[6] != 'tie-fixed': continue
            r = R[o[1]]; e, nn = apply(P[r['fr']], r['x'], r['y']); fv[R[o[2]]['fr']].append((e - o[3], nn - o[4]))
        bad = {g: float(np.hypot(*np.median(v, axis=0))) for g, v in fv.items() if len(v) >= 2}
        bad = {g: m for g, m in bad.items() if m > 4.0 and g not in EXF}
        if bad:
            g = max(bad, key=bad.get); EXF.add(g); fixed_log[g] = (round(bad[g], 1), len(fv[g])); print('fixed frame left out:', g, fixed_log[g])
        if not new and not bad: break
        bias_log.update(new); EXC.update(new); set_cands()
    print('weak frames (rotation pinned):', {f: round(float(np.degrees(t)), 2) for f, t in WEAK.items()})
    final = obs
    rep = {}
    for f in newfr:
        if f not in P: rep[f] = dict(fitted=False); continue
        rr = []; cnt = collections.Counter()
        for o in final:
            if f in obs_frames(o): rr.append(resid(o)); cnt[o[6]] += 1
        p = P[f]
        rep[f] = dict(fitted=True, pxm=round(float(1 / scale_of(p)), 3), rot=round(float(np.degrees(rot_of(p))), 2), n=dict(cnt),
                      med=round(float(np.median(rr)), 2) if rr else None, mx=round(float(max(rr)), 2) if rr else None,
                      weak=f in WEAK, init=next((l[1] for l in log if l[0] == f), None))
    restype = collections.defaultdict(list)
    for o in final: restype[o[6]].append(resid(o))
    summary = {t: dict(n=len(v), median=round(float(np.median(v)), 2), p90=round(float(np.percentile(v, 90)), 2), max=round(float(max(v)), 2)) for t, v in restype.items()}
    json.dump({f: list(map(float, P[f])) for f in newfr if f in P}, open(OUT + 'tf_all.json', 'w'), indent=0)
    json.dump(dict(frames=rep, residuals=summary, not_fitted=miss, biased=bias_log, fixed_left_out=fixed_log), open(OUT + 'report_all.json', 'w'), indent=1)
    pickle.dump(dict(obs=final, R=R, P={f: P[f] for f in newfr if f in P}, oldw=oldw, oldt=oldt, oldl=[(a, b, c, None, e) for a, b, c, d, e in oldl]), open(OUT + 'obs_all.pkl', 'wb'))
    print('residuals by type', summary)
    for f in newfr: print(f, rep[f])
if __name__ == '__main__': main()
