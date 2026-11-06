"""Corner check on the built deck layer (deckpage/deck.json or deck/deck.json) and lph/lph_streets.json."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, math, sys, numpy as np
from shapely.geometry import LineString, Point
SP = _ws.DATA
DK = sys.argv[1] if len(sys.argv) > 1 else SP + 'deck/deck.json'
D = json.load(open(DK)); F = D['features']
def brg(a, b): return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) % 360
bl = [f for f in F if f['properties']['layer'] == 'boulevard'][0]['geometry']['coordinates'][0]
TH = brg(bl[0], bl[3]); r = math.radians(TH); u = np.array([math.sin(r), math.cos(r)])
inf = lambda p: LineString([tuple(np.array(p) - u * 6000), tuple(np.array(p) + u * 6000)])
EW, NS = [], [('blvd W', inf(bl[0])), ('blvd E', inf(bl[1]))]
ga, gb = D['garrard']['a'], D['garrard']['b']
G = LineString([(ga + gb * (n - 4332000), n) for n in (4329000, 4337000)])
NS.append(('Garrard', G))
DEP = [(711689.0, 4331251.0), (711690.0, 4331305.0), (711699.0, 4331460.0), (711708.0, 4331601.0), (711719.0, 4331777.0)]
c0 = np.array(DEP).mean(0); NS.append(('Depot', LineString([tuple(c0 - u * 400), tuple(c0 + u * 600)])))
for f in F:
    p = f['properties']
    if p['layer'] != 'street': continue
    l = LineString(f['geometry']['coordinates'])
    if p['kind'] == 'NS' and p.get('side') == 'LPH': NS.append((p['name'], l))
    elif p['kind'] in ('T', 'through') and p['name'] != 'W 6th': EW.append((p['name'], l))
west = lambda q: q.x < ga + gb * (q.y - 4332000) + 0.6
def corners(ew, ns, reg):
    out = []
    for en, el in ew:
        for nn, nl in ns:
            x = el.buffer(0.05).intersection(nl) if True else None
            x = el.intersection(nl)
            if x.is_empty and el.distance(nl) < 0.4:   # ends carried to the centreline
                x = Point(nl.interpolate(nl.project(Point(el.coords[-1]))).coords[0])
            for q in getattr(x, 'geoms', [x]):
                if q.is_empty or q.geom_type != 'Point' or not reg(q): continue
                c = list(el.coords); segs = [(c[i], c[i + 1]) for i in range(len(c) - 1) if LineString(c[i:i + 2]).distance(q) < 0.5]
                if nn == 'Garrard': segs = [s for s in segs if (s[0][0] + s[1][0]) / 2 < q.x] or segs
                cn = list(nl.coords); nsg = [(cn[i], cn[i + 1]) for i in range(len(cn) - 1) if LineString(cn[i:i + 2]).distance(q) < 0.5]
                if not segs or not nsg: continue
                out.append((round(max(abs(((brg(*a) - brg(*b)) % 180) - 90) for a in segs for b in nsg), 2), en, nn))
    return out
reg = lambda q: west(q) and q.y > 4331250
ex = ('W 8th (viaduct line)', 'Gest')
for lab, ew in (('west of Garrard, north of W 8th, excl. W 8th and Gest', [e for e in EW if e[0] not in ex]), ('W 8th and Gest', [e for e in EW if e[0] in ex])):
    c = corners(ew, NS, reg); v = np.array([x[0] for x in c])
    print(f'{lab}: n={len(v)} median {np.median(v):.2f} max {v.max():.2f} >0.3: {int((v > 0.3).sum())}', sorted(set(x for x in c if x[0] > 0.3), reverse=True)[:8])
# jogs at Depot
dep = NS[3][1]
for nm, tgt in (('W 9th', (711695, 4331382)), ('Richmond', (711699, 4331460))):
    l = [x for n, x in EW if n == nm][0]; q = l.intersection(dep) if not l.intersection(dep).is_empty else Point(l.coords[-1])
    print(f'jog {nm}: meets Depot {Point(q).distance(Point(tgt)):.1f} m from the 1904 crossing')
