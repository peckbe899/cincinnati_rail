"""Analysis only: Garrard seam combined with options A (LPH N-S parallel to the boulevard), the W 8th / Gest / W 9th /
Richmond exceptions, and D-lite (1904 south of W 8th squared). Prints moves and corner statistics; writes nothing."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, math, sys, numpy as np
from shapely.geometry import LineString, Point
SP = _ws.DATA
D = json.load(open(SP + 'deckpage/deck.json'))['features']
L = json.load(open(SP + 'lph/lph_streets.json'))['features']

def brg(a, b): return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) % 360
def unit(deg): r = math.radians(deg); return np.array([math.sin(r), math.cos(r)])

bl = [f for f in D if f['properties']['layer'] == 'boulevard'][0]['geometry']['coordinates'][0]
TH_AX = brg(bl[0], bl[3])                       # boulevard axis bearing
TH_W = TH_AX + 90                               # square to it
ua = unit(TH_AX)
def infline(p, deg, half=6000):
    p = np.array(p); u = unit(deg); return LineString([tuple(p - u * half), tuple(p + u * half)])
EDGE_W, EDGE_E = infline(bl[0], TH_AX), infline(bl[1], TH_AX)
st = {}
for f in D:
    p = f['properties']
    if p['layer'] != 'street': continue
    st.setdefault(p['name'], []).append(dict(line=LineString(f['geometry']['coordinates']), kind=p.get('kind'), side=p.get('side', '')))
GARR = LineString([(712467.6, 4330932.2), (712681.4, 4334574.6)])
TH_G = brg(*GARR.coords)
G_INF = infline(GARR.coords[0], TH_G)
HORNE = st['Horne line']
lph = {f['properties']['name']: LineString(f['geometry']['coordinates']) for f in L if f['properties']['layer'] == 'street'}
print(f'boulevard axis {TH_AX:.3f}, square {TH_W:.3f}, Garrard {TH_G:.3f}')

def fit_parallel(pts, deg):
    """line at bearing deg through the mean cross-offset of pts; returns (line, max move, rms)"""
    P = np.array(pts, float); u = unit(deg); n = np.array([u[1], -u[0]])
    off = P @ n; m = off.mean(); dev = off - m
    c = P.mean(0) + n * (m - P.mean(0) @ n)
    return infline(c, deg), float(np.abs(dev).max()), dev

def corners(ew, ns, region=None):
    """all crossings of E-W lines with N-S lines; per crossing the worst of its four corners (deg off square)"""
    out = []
    for en, el in ew:
        for nn, nl in ns:
            x = el.intersection(nl)
            if x.is_empty: continue
            for q in getattr(x, 'geoms', [x]):
                if q.geom_type != 'Point': continue
                if region is not None and not region(q): continue
                def dirs(line, q):
                    c = list(line.coords); s = line.project(q); res = []
                    acc = 0
                    for i in range(len(c) - 1):
                        seg = LineString(c[i:i + 2]); a0, a1 = acc, acc + seg.length
                        if a0 - 0.5 <= s <= a1 + 0.5: res.append(brg(c[i], c[i + 1]))
                        acc = a1
                    return res
                de, dn = dirs(el, q), dirs(nl, q)
                if not de or not dn: continue
                w = max(abs(((a - b) % 180) - 90) for a in de for b in dn)
                out.append((round(w, 2), en, nn, round(q.x), round(q.y)))
    return out
def stats(c, label):
    v = np.array([x[0] for x in c]) if c else np.array([0.0])
    worst = sorted(c, reverse=True)[:5]
    print(f'{label}: n={len(c)} median {np.median(v):.2f} max {v.max():.2f}; >0.5: {int((v > 0.5).sum())}; worst {worst}')

west_of_G = lambda q: q.x < G_INF.interpolate(G_INF.project(q)).x + 0.6
north_of_8 = lambda q: q.y > 4331250

# ---------------------------------------------------------------- current
DEPOT = LineString([(711689.0, 4331251.0), (711690.0, 4331305.0), (711699.0, 4331460.0), (711708.0, 4331601.0), (711719.0, 4331777.0)])
EW_now = [(n, d['line']) for n in st for d in st[n] if d['kind'] in ('T', 'through') and d['side'] in ('E', 'LPH', '') and n not in ('W 6th',)]
NS_now = [('blvd W', EDGE_W), ('blvd E', EDGE_E), ('Garrard', GARR), ('Depot', DEPOT)] + [(n, st[n][0]['line']) for n in ('Summer', 'Berlin', 'Evans')]
c_now = corners(EW_now, NS_now, lambda q: west_of_G(q) and north_of_8(q))
stats(c_now, 'NOW, west of Garrard, north of W 8th (deck + razed LPH)')

# ---------------------------------------------------------------- option A: N-S lines parallel to the boulevard
NS_A = {}
for nm, pts in (('Depot', list(DEPOT.coords)[1:]), ('Summer', [(711858, 4331593), (711873, 4331827), (711879, 4331898)]),
                ('Berlin', [(711934, 4331589), (711947, 4331822), (711952, 4331909)]),
                ('Evans', [(711988, 4331282), (711985, 4331332), (711990, 4331400), (711992, 4331443), (712005, 4331585), (712022, 4331818)])):
    ln, mx, dev = fit_parallel(pts, TH_AX)
    NS_A[nm] = ln
    print(f'A  {nm:7s} straight at {TH_AX:.2f}: max move {mx:.1f} m  (per vertex {np.round(dev, 1).tolist()})')
# Evans: also with the W 8th corner held (south vertex fixed)
p0 = np.array([711988.0, 4331282.0]); n = np.array([ua[1], -ua[0]])
dv = [float((np.array(q) - p0) @ n) for q in [(711985, 4331332), (711990, 4331400), (711992, 4331443), (712005, 4331585), (712022, 4331818)]]
print('A  Evans held at W 8th corner: moves', np.round(dv, 1).tolist())

# ---------------------------------------------------------------- seam at Garrard
def seam(line, west_target, deg=TH_W):
    c = list(line.coords); east = c[0] if c[0][0] > c[-1][0] else c[-1]
    q = line.intersection(G_INF)
    if q.is_empty: return None, None
    ray = LineString([(q.x, q.y), tuple(np.array([q.x, q.y]) - unit(deg) * 1500)])
    h = ray.intersection(west_target)
    if h.is_empty: return None, None
    h = min(getattr(h, 'geoms', [h]), key=lambda g: Point(q).distance(g))
    return LineString([east, (q.x, q.y), (h.x, h.y)]), (q.x, q.y)
EW_S, moves = [], {}
for nm in st:
    for d in st[nm]:
        if d['kind'] == 'T' and d['side'] == 'E':
            new, q = seam(d['line'], EDGE_E)
            if new is None: EW_S.append((nm, d['line'])); continue
            old_end = Point(min(d['line'].coords, key=lambda c: c[0]))
            moves.setdefault('T', []).append((round(old_end.distance(Point(new.coords[-1])), 1), nm))
            EW_S.append((nm, new))
        elif d['side'] == 'LPH' and d['kind'] == 'through':
            tgt = NS_A['Summer'] if nm == 'Hopkins' else NS_A['Depot']
            new, q = seam(d['line'], tgt)
            old_end = Point(min(d['line'].coords, key=lambda c: c[0]))
            dn = new.coords[-1][1] - old_end.y
            moves.setdefault('LPH', []).append((round(dn, 1), nm))
            EW_S.append((nm, new))
for t in ('T', 'LPH'): print('seam', t, 'west-end moves (m):', sorted(moves[t], reverse=True)[:8] if t == 'T' else moves[t])
# Liberty, W 8th, Gest bent at the seam (for the alternative)
for nm, west_x in (('W Liberty', 711876), ('W 8th (viaduct line)', 711570), ('Gest', 711632.5)):
    ln = st[nm][0]['line']; q = ln.intersection(G_INF)
    y_new = q.y + (q.x - west_x) * math.tan(math.radians(TH_W - 90))
    y_old = [c[1] for c in ln.coords if abs(c[0] - west_x) < 1][0]
    print(f'seam alt: {nm} bent at Garrard -> west end moves {y_new - y_old:+.1f} m (own bearing west of Garrard {brg(*[c for c in ln.coords][-2:]):.2f})')
W8, GEST, LIB = st['W 8th (viaduct line)'][0]['line'], st['Gest'][0]['line'], st['W Liberty'][0]['line']
NS_S = [('blvd W', EDGE_W), ('blvd E', EDGE_E), ('Garrard', GARR)] + [(k, v) for k, v in NS_A.items()]
c1 = corners(EW_S + [('W 8th', W8), ('Gest', GEST)], NS_S, lambda q: west_of_G(q) and north_of_8(q))
stats(c1, 'SEAM + A, W 8th and Gest own lines')
c1b = corners(EW_S, NS_S, lambda q: west_of_G(q) and north_of_8(q))
stats(c1b, '   same, excluding W 8th and Gest corners')
# W 9th / Richmond meet Dutton / South: jog sizes at Depot'
for nm, tgt in (('W 9th', (711695, 4331382)), ('Richmond', (711699, 4331460))):
    l = [x for n_, x in EW_S if n_ == nm][0]; e = Point(l.coords[-1])
    print(f'jog {nm}: {e.distance(Point(tgt)):.1f} m ({tgt[1] - e.y:+.1f} N)')
# alternative: W 9th / Richmond bent at the boulevard west edge to reach Dutton / South
for nm, tgt in (('W 9th', (711695, 4331382)), ('Richmond', (711699, 4331460))):
    l = [x for n_, x in EW_S if n_ == nm][0]; w = l.intersection(EDGE_W)
    print(f'bend alt {nm}: from blvd W edge to {tgt}: bearing {brg(tgt, (w.x, w.y)):.2f} -> {abs(brg(tgt, (w.x, w.y)) - TH_W):.2f} deg off at Summer/Berlin/Evans/Depot')

# ---------------------------------------------------------------- D-lite: 1904 south of W 8th
EW04 = ['Hatmaker Street', 'Staebler Street', 'Storrs Street', 'St. Michael Street', 'Price', 'Dutton', 'South', 'West 6th Street']
NS04 = ['State Avenue', 'Depot Street', 'Burns Street', 'Neave Street', 'Evans Street']
c04 = corners([(n, lph[n]) for n in EW04] + [('W 8th', W8)], [(n, lph[n]) for n in NS04])
stats(c04, '1904 LPH now')
print('D-lite at the boulevard square (%.2f) / N-S %.2f:' % (TH_W, TH_AX))
for nm in EW04[:-1]:
    ln, mx, dev = fit_parallel(list(lph[nm].coords), TH_W); print(f'   {nm:20s} max move {mx:.1f} m')
for nm in ('Burns Street',):
    pts = list(lph[nm].coords)[2:]      # main run, W 6th to Hatmaker (north kink to W 8th kept)
    ln, mx, dev = fit_parallel(pts, TH_AX); print(f'   {nm:20s} main run max move {mx:.1f} m')

# ---------------------------------------------------------------- cleaner tallies (Garrard: west-side corners only)
def corner_w(ew, ns, region):
    out = []
    for en, el in ew:
        for nn, nl in ns:
            x = el.intersection(nl)
            for q in getattr(x, 'geoms', [x]):
                if q.is_empty or q.geom_type != 'Point' or not region(q): continue
                c = list(el.coords); segs = [(c[i], c[i + 1]) for i in range(len(c) - 1) if LineString(c[i:i + 2]).distance(q) < 0.5]
                if nn == 'Garrard': segs = [s for s in segs if (s[0][0] + s[1][0]) / 2 < q.x] or segs
                cn = list(nl.coords); nsg = [(cn[i], cn[i + 1]) for i in range(len(cn) - 1) if LineString(cn[i:i + 2]).distance(q) < 0.5]
                w = max(abs(((brg(*a) - brg(*b)) % 180) - 90) for a in segs for b in nsg)
                out.append((round(w, 2), en, nn))
    return out
lib_s, _ = seam(LIB, infline((711876, 4332405), 0))
reg = lambda q: west_of_G(q) and q.y > 4331250
EWn = [x for x in EW_now if x[0] not in ('W 8th (viaduct line)', 'Gest')]
cn = corner_w(EWn, NS_now, reg); cs = corner_w([x for x in EW_S] + [('W Liberty', lib_s)], NS_S, reg)
ce = corner_w([('W 8th', W8), ('Gest', GEST)], NS_S, reg)
for lab, c in (('now (excl. W 8th, Gest)', cn), ('seam+A (excl. W 8th, Gest)', cs), ('W 8th & Gest under seam+A', ce),
               ('W 8th & Gest now', corner_w([('W 8th', W8), ('Gest', GEST)], NS_now, reg))):
    v = np.array([x[0] for x in c]); print(f'{lab}: n={len(v)} median {np.median(v):.2f} max {v.max():.2f} >0.3: {int((v > 0.3).sum())}',
                                         sorted(set((x[0], x[1], x[2]) for x in c if x[0] > 0.3), reverse=True)[:6])
# D-lite corners: 1904 E-W x Burns main run and Depot (south of W 8th part + straightened), now vs after
BURNS_MAIN = LineString(list(lph['Burns Street'].coords)[2:])
DEP_FULL, mxd, _ = fit_parallel(list(DEPOT.coords), TH_AX); print('Depot full length straight: max move %.1f' % mxd)
E4 = ['Hatmaker Street', 'Staebler Street', 'Storrs Street', 'St. Michael Street', 'Price']
c_n = corner_w([(n, lph[n]) for n in E4], [('Burns', BURNS_MAIN), ('Depot', DEPOT)], lambda q: True)
c_d = corner_w([(n, fit_parallel(list(lph[n].coords), TH_W)[0]) for n in E4], [('Burns', fit_parallel(list(BURNS_MAIN.coords), TH_AX)[0]), ('Depot', DEP_FULL)], lambda q: q.y < 4331260 and q.x < 711800)
for lab, c in (('1904 Burns/Depot crossings now', c_n), ('after D-lite', c_d)):
    v = np.array([x[0] for x in c]); print(f'{lab}: n={len(v)} median {np.median(v):.2f} max {v.max():.2f}', sorted(c, reverse=True)[:4])
