"""Georeference the extension sheets (Ben, 2026-10-18: 1904 Sanborn between the Times and Elsinore stations, vol. 2 sheets
143, 144, 149, 150, 157-160; and Winton Place / Mitchell Ave to Ivorydale, vol. 6 sheets 647-656, 663-665) with every frame
already fitted held fixed (sbg/fit/tf.json basin, lph/tf_all.json deck + north). Same method as lph/solve_all.py:
vol. 2 (CHPL scans): affine with soft similarity priors; vol. 6 (LOC): similarity. Observations: ties to the same named
crossing on a fixed frame (world point), ties between two new frames, OSM corners of surviving streets (lph/osm_north.geojson,
basin/osm_basin.geojson). Start from a RANSAC similarity per frame, then a joint Huber-weighted least squares.
Writes lph/tf_ext.json and lph/report_ext.json."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, os, collections, itertools, numpy as np
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'sbg/fit'); sys.path.insert(0, _ws.CODE + 'sbg'); sys.path.insert(0, _ws.CODE + 'lph')
from names import key, base
from shapely.geometry import LineString, Point
from shapely.ops import unary_union, linemerge
import osmx
from solve_all import ALIAS, ransac_sim, page_w
NEW = [int(v) for v in os.environ["NEW"].split(",")] if os.environ.get("NEW") else [143, 144, 149, 150, 157, 158, 159, 160] + list(range(647, 657)) + [663, 664, 665]
CHPL2 = {s for s in NEW if s <= 200}      # vol. 2 runs to sheet 200
OUTSFX = os.environ.get("OUTSFX", "")
SIG = {'fix': 1.5, 'osm': 2.0, 'tie': 1.5}
def K(n): k = key(n); return ALIAS.get(k, k)
def sheet_of(fr): return int(''.join(c for c in str(fr) if c.isdigit()))
def npar(fr): return 6 if sheet_of(fr) in CHPL2 else 4
def s0_of(fr): return (4125 / page_w(sheet_of(fr))) / 11.40 if sheet_of(fr) in CHPL2 else 1 / 20.0
def sim_to_par(fr, A, B):
    a, c = A.real, A.imag
    return np.array([a, c, c, -a, B.real, B.imag]) if npar(fr) == 6 else np.array([a, c, B.real, B.imag])
def apply(p, x, y):
    if len(p) == 6: return p[0] * x + p[1] * y + p[4], p[2] * x + p[3] * y + p[5]
    a, c, tx, ty = p; return a * x + c * y + tx, c * x - a * y + ty
def coef(fr, x, y):
    if npar(fr) == 6: return {0: x, 1: y, 4: 1}, {2: x, 3: y, 5: 1}
    return {0: x, 1: y, 2: 1}, {0: -y, 1: x, 3: 1}
LEG = {(649, 5864, 5488): 'north', (650, 440, 7555): 'north', (649, 5630, 5614): 'south', (656, 397, 6777): 'south'}
def pab(part): return ''.join(w[0] for w in part.replace('_', '-').split('-') if w)
# hand-read extras (lph/ext_extra.json): crossings just off the paper, and points on a street centreline (matched to the OSM line)
EXTRA = json.load(open(SP + 'lph/ext_extra.json')) if os.path.exists(SP + 'lph/ext_extra.json') else {}
def picks():
    R = []
    for s in NEW + []:
        f = SP + f'sbg/picks/s{s}.json'
        if not os.path.exists(f): continue
        d = json.load(open(f))
        for p in d.get('intersections', []):
            fr = f"{s}{pab(p['part'])}" if p.get('part') else str(s)
            R.append(dict(s=s, fr=fr, a=p['a'], b=p['b'], x=float(p['x']), y=float(p['y'])))
        for p in d.get('bends', []):
            if not p.get('street'): continue
            fr = f"{s}{pab(p['part'])}" if p.get('part') else str(s)
            R.append(dict(s=s, fr=fr, a=p['street'], b='', x=float(p['x']), y=float(p['y']), bend=True))
    for p in EXTRA.get('intersections', []):
        if p['s'] not in NEW: continue
        R.append(dict(s=p['s'], fr=p['fr'], a=p['a'], b=p['b'], x=float(p['x']), y=float(p['y'])))
    return R
def fixed_world():
    """world points of named crossings on the fixed frames"""
    TF = {k: np.array(v) for k, v in json.load(open(SP + 'sbg/fit/tf.json')).items()}
    TF.update({k: np.array(v) for k, v in json.load(open(SP + 'lph/tf_all.json')).items()})
    for fx in [x for x in os.environ.get('FIXED_EXTRA', '').split(',') if x]:      # earlier extension frames held fixed too (e.g. lph/tf_ext.json)
        TF.update({k: np.array(v) for k, v in json.load(open(SP + fx)).items() if sheet_of(k) not in NEW})
    W = collections.defaultdict(list)
    import glob
    for f in glob.glob(SP + 'sbg/picks/s*.json'):
        d = json.load(open(f)); s = int(d.get('sheet') or f.split('/s')[-1].split('.')[0])
        if s in NEW: continue
        for p in d.get('intersections', []):
            fr = f"{s}{pab(p['part'])}" if p.get('part') else str(s)
            if fr not in TF:
                # split basin sheets (13u/13l etc.) and 17u: try the frames that exist
                c = [k for k in TF if sheet_of(k) == s]
                if len(c) != 1: continue
                fr = c[0]
            E, N = apply(TF[fr], p['x'], p['y'])
            ka, kb = K(p['a']), K(p['b'])
            if ka in ('', '?') or kb in ('', '?') or ka == kb: continue
            W[tuple(sorted((ka, kb)))].append((E, N, fr))
    return W
def osm_corners():
    G = collections.defaultdict(list); seen = set()
    for fn in ('lph/osm_north.geojson', 'basin/osm_basin.geojson') + (('lph/osm_east.geojson',) if os.path.exists(SP + 'lph/osm_east.geojson') else ()):
        for f in json.load(open(SP + fn))['features']:
            p = f['properties']; nm = p.get('name')
            if not nm or p.get('highway') not in osmx.ROADS or f['geometry']['type'] != 'LineString': continue
            c = tuple(map(tuple, f['geometry']['coordinates']))
            if c in seen: continue
            seen.add(c); l = LineString(c)
            if 713000 <= l.centroid.x <= 720000 and 4330500 <= l.centroid.y <= 4341500: G[K(nm)].append(l)
    return {k: v for k, v in osmx.inters(G).items()}
def okeys(k, keys):
    if k in keys: return [k]
    b = base(k); return [q for q in keys if base(q) == b]
def main():
    R = [r for r in picks() if K(r['a']) not in ('', '?') and (r.get('bend') or K(r['b']) not in ('', '?'))]
    W = fixed_world(); O = osm_corners()
    WK, OK_ = set(k for p in W for k in p), set(k for p in O for k in p)
    for r in R:
        ka, kb = K(r['a']), K(r['b']); r['pair'] = tuple(sorted((ka, kb))) if not r.get('bend') else ('bend', id(r)); r['cand'] = []
        if r.get('bend'): continue
        leg = LEG.get((r['s'], int(r['x']), int(r['y'])))
        if leg: r['pair'] = r['pair'] + (leg,); r['sig'] = 6.0     # Mitchell jogs 43 ft at Spring Grove: legs tie only to the same leg
        for A in okeys(ka, WK):
            for B in okeys(kb, WK):
                if A != B: r['cand'] += [(e, n, 'fix') for e, n, _ in W.get(tuple(sorted((A, B))), [])]
        SKIPO = set(k for k in os.environ.get('OSM_SKIP', '').split(',') if k)     # streets realigned since 1904 (I-71, Dorchester, Florence, Gilbert): no OSM corner control
        for A in okeys(ka, OK_):
            for B in okeys(kb, OK_):
                if A != B and not ({A, B} & SKIPO) and f'{min(A, B)}+{max(A, B)}' not in SKIPO: r['cand'] += [(e, n, 'osm') for e, n in O.get(tuple(sorted((A, B))), [])]
    # OSM centrelines for the line observations
    OL = collections.defaultdict(list)
    for fn in ('lph/osm_north.geojson',) + (('lph/osm_east.geojson',) if os.path.exists(SP + 'lph/osm_east.geojson') else ()):
        for f in json.load(open(SP + fn))['features']:
            nm = f['properties'].get('name')
            if nm and f['geometry']['type'] == 'LineString': OL[K(nm)].append(LineString(f['geometry']['coordinates']))
    OLM = {}
    for k, v in OL.items():
        u = unary_union(v); OLM[k] = linemerge(u) if u.geom_type == 'MultiLineString' else u
    LINES = []
    for L in EXTRA.get('lines', []):
        u = unary_union(OL.get(K(L['street']), [])); g = linemerge(u) if u.geom_type == 'MultiLineString' else u
        if g.is_empty: print('no OSM line for', L['street']); continue
        if g.geom_type == 'MultiLineString':     # the piece nearest the hand-given approximate position
            g = min(g.geoms, key=lambda q: q.distance(Point(*L['near'])))
        LINES.append(dict(L, geom=g))
    frames = sorted({r['fr'] for r in R}, key=lambda f: (sheet_of(f), f))
    # starting frames: RANSAC similarity on every candidate
    P0 = {}
    for fr in frames:
        rr = [r for r in R if r['fr'] == fr]
        src, dst = [], []
        for r in rr:
            for e, n, _ in r['cand']: src.append((r['x'], r['y'])); dst.append((e, n))
        if len(src) < 2: print('frame', fr, 'no control', len(rr)); continue
        res = ransac_sim(np.array(src), np.array(dst), s0_of(fr), thr=20.0, min_in=2 if len(src) <= 4 else 3)
        if res is None: print('frame', fr, 'ransac failed', len(rr), len(src)); continue
        A, B, inl, _ = res; P0[fr] = sim_to_par(fr, A, B); print('frame', fr, 'start', int(inl.sum()), 'of', len(src), 'scale', round(abs(A) / s0_of(fr), 3))
    # frames with no control of their own: start from a tied neighbour (two or more crossings shared with a started frame)
    for _ in range(8):
        for fr in frames:
            if fr in P0: continue
            src, dst = [], []
            for r in R:
                if r['fr'] != fr: continue
                for q in R:
                    if q['fr'] in P0 and q['fr'] != fr and q['pair'] == r['pair']:
                        src.append((r['x'], r['y'])); dst.append(apply(P0[q['fr']], q['x'], q['y']))
            if len(src) >= 2:
                res = ransac_sim(np.array(src), np.array(dst), s0_of(fr), thr=25.0, min_in=2)
                if res: A, B, inl, _ = res; P0[fr] = sim_to_par(fr, A, B); print('frame', fr, 'start from ties', int(inl.sum()))
    for fr, phi in sorted(EXTRA.get('init_north_deg', {}).items(), key=lambda kv: kv[0] in ('650m',)):      # one crossing plus the north arrow
        if fr in P0 or fr not in frames: continue
        A = s0_of(fr) * np.exp(1j * np.radians(phi)); w = None
        for r in R:
            if r['fr'] != fr or r.get('bend'): continue
            if r['cand']: w = r['cand'][0][0] + 1j * r['cand'][0][1]; break
            q = [q for q in R if q['fr'] in P0 and q['fr'] != fr and q['pair'] == r['pair']]
            if q: e, n = apply(P0[q[0]['fr']], q[0]['x'], q[0]['y']); w = e + 1j * n; break
        if w is None: print('frame', fr, 'no point for the arrow start'); continue
        z = r['x'] - 1j * r['y']
        P0[fr] = sim_to_par(fr, A, w - A * z); print('frame', fr, 'start from the north arrow and', r['a'], '/', r['b'])
    frames = [f for f in frames if f in P0]
    idx, off = {}, 0
    for f in frames: idx[f] = off; off += npar(f)
    P = np.concatenate([P0[f] for f in frames])
    def par(f): return P[idx[f]:idx[f] + npar(f)]
    ties = [(r, q) for r, q in itertools.combinations([r for r in R if r['fr'] in idx], 2) if r['fr'] != q['fr'] and r['pair'] == q['pair']]
    for it in range(12):
        rows, rhs, wts, tags = [], [], [], []
        def add(c1, f1, c2, f2, val, sig, tag):
            row = np.zeros(off)
            for k, v in c1.items(): row[idx[f1] + k] += v
            if f2:
                for k, v in c2.items(): row[idx[f2] + k] -= v
            rows.append(row); rhs.append(val); wts.append(1 / sig); tags.append(tag)
        for r in R:
            f = r['fr']
            if f not in idx or not r['cand']: continue
            e, n = apply(par(f), r['x'], r['y'])
            c = min(r['cand'], key=lambda q: (q[0] - e) ** 2 + (q[1] - n) ** 2)
            if np.hypot(c[0] - e, c[1] - n) > (60 if it < 3 else (25 if it < 6 else 12)): continue
            cx, cy = coef(f, r['x'], r['y'])
            sg = r.get('sig', SIG[c[2]]); add(cx, f, None, None, c[0], sg, ('ctl', id(r), c[2])); add(cy, f, None, None, c[1], sg, ('ctl', id(r), c[2]))
        for r in R:
            f = r['fr']
            if f not in idx: continue
            e, n = apply(par(f), r['x'], r['y']); pt = Point(e, n)
            for nm in (r['a'], r['b']):
                g = OLM.get(K(nm)) if nm and K(nm) not in set(os.environ.get('OSM_SKIP', '').split(',')) else None
                if g is None: continue
                q = g.interpolate(g.project(pt)); d = pt.distance(q)
                if d > (40 if it < 3 else 15): continue
                t0 = g.interpolate(max(0, g.project(pt) - 5)); t1 = g.interpolate(min(g.length, g.project(pt) + 5))
                tv = np.array([t1.x - t0.x, t1.y - t0.y]); nrm = np.linalg.norm(tv)
                if nrm == 0: continue
                tv /= nrm; nv = np.array([-tv[1], tv[0]])
                cx, cy = coef(f, r['x'], r['y']); c = {k: nv[0] * v for k, v in cx.items()}
                for k, v in cy.items(): c[k] = c.get(k, 0) + nv[1] * v
                add(c, f, None, None, nv[0] * q.x + nv[1] * q.y, 4.0 if r.get('bend') else 3.0, ('sline',))
        for f in frames:                      # LOC page scale (the fitted LOC frames all sit within 1% of 20 px/m): hold it to 0.5%
            if npar(f) == 4:
                p = par(f); m = np.hypot(p[0], p[1]); add({0: p[0] / m, 1: p[1] / m}, f, None, None, s0_of(f), 0.005 * s0_of(f), ('scale',))
            else:                             # CHPL pages: hold each axis scale to 2% of the page scale
                p = par(f); m = np.hypot(p[0], p[2]); add({0: p[0] / m, 2: p[2] / m}, f, None, None, s0_of(f), 0.02 * s0_of(f), ('scale',))
                m = np.hypot(p[1], p[3]); add({1: p[1] / m, 3: p[3] / m}, f, None, None, s0_of(f), 0.02 * s0_of(f), ('scale',))
        for L in LINES:
            f = L['fr']
            if f not in idx: continue
            for x, y in L['pts']:
                e, n = apply(par(f), x, y); pt = Point(e, n); g = L['geom']
                q = g.interpolate(g.project(pt)); d = pt.distance(q)
                if d > (80 if it < 3 else 30): continue
                t0 = g.interpolate(max(0, g.project(pt) - 5)); t1 = g.interpolate(min(g.length, g.project(pt) + 5))
                tv = np.array([t1.x - t0.x, t1.y - t0.y]); tv /= np.linalg.norm(tv); nv = np.array([-tv[1], tv[0]])
                cx, cy = coef(f, x, y); c = {k: nv[0] * v for k, v in cx.items()}
                for k, v in cy.items(): c[k] = c.get(k, 0) + nv[1] * v
                add(c, f, None, None, nv[0] * q.x + nv[1] * q.y, 3.0, ('line',))
        for r, q in ties:
            e1, n1 = apply(par(r['fr']), r['x'], r['y']); e2, n2 = apply(par(q['fr']), q['x'], q['y'])
            if np.hypot(e1 - e2, n1 - n2) > (60 if it < 3 else (25 if it < 6 else 12)): continue
            a1, b1 = coef(r['fr'], r['x'], r['y']); a2, b2 = coef(q['fr'], q['x'], q['y'])
            add(a1, r['fr'], a2, q['fr'], 0.0, SIG['tie'], ('tie',)); add(b1, r['fr'], b2, q['fr'], 0.0, SIG['tie'], ('tie',))
        for f in frames:                     # priors: similarity shape for affine frames, scale toward the page scale
            p = par(f); s0 = s0_of(f)
            if npar(f) == 6:
                add({1: 1, 2: -1}, f, None, None, 0.0, 0.002 * s0 * 10, ('pri',)); add({0: 1, 3: 1}, f, None, None, 0.0, 0.002 * s0 * 10, ('pri',))
        A_ = np.array(rows); b_ = np.array(rhs); w = np.array(wts)
        r_ = (A_ @ P - b_) * w
        hub = np.where(np.abs(r_) <= 1.5, 1.0, 1.5 / np.maximum(np.abs(r_), 1e-9))
        ww = w * np.sqrt(hub)
        P, *_ = np.linalg.lstsq(A_ * ww[:, None], b_ * ww, rcond=None)
    # report
    rep = {}
    for f in frames:
        res = []
        for r in R:
            if r['fr'] != f or not r['cand']: continue
            e, n = apply(par(f), r['x'], r['y']); c = min(r['cand'], key=lambda q: (q[0] - e) ** 2 + (q[1] - n) ** 2)
            d = float(np.hypot(c[0] - e, c[1] - n))
            if d < 12: res.append((d, c[2]))
        tr = []
        for r, q in ties:
            if f in (r['fr'], q['fr']):
                e1, n1 = apply(par(r['fr']), r['x'], r['y']); e2, n2 = apply(par(q['fr']), q['x'], q['y']); d = float(np.hypot(e1 - e2, n1 - n2))
                if d < 12: tr.append(d)
        p = par(f); sc = float(np.hypot(p[0], p[2]) if len(p) == 6 else np.hypot(p[0], p[1]))
        rep[f] = dict(n_ctl=len(res), n_fix=sum(1 for d, s in res if s == 'fix'), rms_ctl=round(float(np.sqrt(np.mean([d * d for d, _ in res]))), 2) if res else None,
                      max_ctl=round(max([d for d, _ in res]), 2) if res else None, n_tie=len(tr), rms_tie=round(float(np.sqrt(np.mean(np.square(tr)))), 2) if tr else None,
                      scale_rel=round(sc / s0_of(f), 4), n_picks=sum(1 for r in R if r['fr'] == f))
        print(f, rep[f])
    json.dump({f: [float(v) for v in par(f)] for f in frames}, open(SP + f'lph/tf_ext{OUTSFX}.json', 'w'), indent=1)
    json.dump(rep, open(SP + f'lph/report_ext{OUTSFX}.json', 'w'), indent=1)
    print('missing frames:', sorted(set(str(s) for s in NEW) - set(sheet_of(f) and str(sheet_of(f)) for f in frames)))
if __name__ == '__main__': main()
