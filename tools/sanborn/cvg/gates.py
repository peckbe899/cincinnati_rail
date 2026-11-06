try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben (18 October): measure how many contact gates fit along the terminals instead of guessing, split into large widebody stands
# (777 / 747 / A350) and smaller widebody stands (767 / 787 / A330). Walks each terminal face, offset by the nose clearance, and places
# stand envelopes (span + wingtip clearance wide, nose clearance + length deep) square to the face, each needing a clear taxilane
# object free area behind its tail; nothing may enter the runway parking limit, a parallel taxiway's object free area, a building or
# another stand or its taxilane. Large where it fits, else small. Prints counts; writes cvg/gates.json (stands and taxilane strips).
import json, math, sys, itertools, numpy as np
from shapely.geometry import LineString, Polygon, Point, shape, mapping
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely.prepared import prep
S = _ws.DATA
PRM = json.load(open(S + (sys.argv[3] if len(sys.argv) > 3 else 'cvg/gates_params.json')))
A = json.load(open(S + 'deckpage/airport_v58b.json'))
RW = {f['properties']['name'].replace('Runway ', ''): LineString(f['geometry']['coordinates']) for f in A['features'] if f['properties']['layer'] == 'cvg_runway_cl'}
from shapely.affinity import translate
SH = PRM.get('shift', {})
BLD = {f['properties']['name']: translate(shape(f['geometry']), *SH.get(f['properties']['name'], (0, 0))) for f in A['features'] if f['properties']['layer'] == 'cvg_building'}
for nm_, c_ in PRM.get('replace', {}).items(): BLD[nm_] = translate(Polygon(c_).buffer(0), *SH.get(nm_, (0, 0)))     # reshaped terminals (Ben, 18 October)
for nm_, c_ in PRM.get('extra', {}).items(): BLD[nm_] = Polygon(c_).buffer(0)
# landside (Ben, 18 October: T1B and T4 have landside portions, the arrivals and departures area inside the U): no stand or taxilane there
GROUNDS = prep(Polygon(PRM['grounds']).buffer(0)) if PRM.get('grounds') else None     # CVG Grounds.kmz: nothing outside
LANDSIDE = prep(unary_union([translate(Polygon(c_), *SH.get('Terminal 1B', (0, 0))) for c_ in PRM.get('landside', [])])) if PRM.get('landside') else None
TERM = ['Terminal 1A', 'Terminal 1B', 'Terminal 4', 'Terminal 2', 'Terminal 3'] + list(PRM.get('extra', {}))
def group(name):          # buildings that touch share one outline (T1B, T4 and anything built onto them)
    G_ = {name}; ch = True
    while ch:
        ch = False
        for k in TERM:
            if k not in G_ and any(BLD[k].distance(BLD[j]) < 1.0 for j in G_): G_.add(k); ch = True
    return G_
CLS = PRM['classes']                     # {'L': {span, length}, 'S': {...}}
WTC, NOSE = PRM['wingtip_clear'], PRM['nose_clear']; TLOFA = max(c['tlofa'] for c in PRM['classes'].values())
R_PARK, R_TWY, TOFA = PRM['rwy_to_parking'], PRM['rwy_to_twy'], PRM['tofa']
# parallel taxiways on both sides of each runway at R_TWY (ends carried 60 m past the runway ends)
def offset_line(l, d):
    a, b = np.array(l.coords[0]), np.array(l.coords[-1]); u = (b - a) / np.linalg.norm(b - a); n = np.array([-u[1], u[0]])
    return LineString([tuple(a - u * 60 + n * d), tuple(b + u * 60 + n * d)])
PAR = [offset_line(l, s * R_TWY) for l in RW.values() for s in (1, -1)]
park_x = prep(unary_union([l.buffer(R_PARK, cap_style=2) for l in RW.values()]))
tofa_x = prep(unary_union([p.buffer(TOFA / 2, cap_style=2) for p in PAR]))
lane_x = prep(unary_union([l.buffer(R_TWY - TLOFA / 2, cap_style=2) for l in RW.values()]))    # a taxilane centre line no closer to a runway than its parallel
LANE = {c: prep(unary_union([l.buffer(R_TWY - v['tlofa'] / 2, cap_style=2) for l in RW.values()])) for c, v in CLS.items()}
blds = unary_union(list(BLD.values()))
bld_x = prep(blds.buffer(NOSE - 0.5))
bld_t = prep(blds.buffer(1.0))
def rect(p, t, n, w, d0, d1):
    return Polygon([tuple(p - t * w / 2 + n * d0), tuple(p + t * w / 2 + n * d0), tuple(p + t * w / 2 + n * d1), tuple(p - t * w / 2 + n * d1)])
QUOTA = None
DMAX = max(v['length'] + v['tlofa'] for k, v in CLS.items() if k in ('L', 'S'))
TAIL = PRM.get('tail_clear', 0.0)
def rz(c): v = CLS[c]; return (v['obj'] + v['tl_tl'] / 2) if PRM.get('dual') else v['tlofa']     # reserve behind the stand: to mid-way between dual taxilanes
BIG = ('L', 'S', 'X')
DMAX = max(CLS[k]['length'] + TAIL + rz(k) for k in CLS if k in BIG)
TLMAX = max(rz(k) for k in CLS)
TC = PRM.get('term_class', {})
TM = PRM.get('term_mix', {})
CHORD_DEV = PRM.get('chord_dev', 3.5)
KEEPOUT = prep(unary_union([Polygon(c_) for c_ in PRM['keepout']])) if PRM.get('keepout') else None
ZONES = [(z['term'], Polygon(z['poly']), z['pref'], z.get('block', False)) for z in PRM.get('zones', [])]
MIXED = True
def run(order, prefer=('L', 'S')):
    env, tails, out = [], [], []
    for name in order:
        grp = group(name); g = unary_union([BLD[k] for k in grp])
        ring = orient(g.buffer(NOSE, join_style=1), 1).exterior          # CCW: outward normal on the right
        L = ring.length; s = 0.0
        own = BLD[name]
        while s < L:
            p = np.array(ring.interpolate(s).coords[0]); a = np.array(ring.interpolate((s - 8) % L).coords[0]); b = np.array(ring.interpolate((s + 8) % L).coords[0])
            t = (b - a) / np.linalg.norm(b - a); n = np.array([t[1], -t[0]])
            # only stands whose nose point is nearest this terminal (T1B and T4 share the bar)
            if len(grp) > 1 and own.distance(Point(*p)) > min(BLD[k].distance(Point(*p)) for k in grp) + 0.01: s += 1.0; continue
            placed = False
            nL = sum(1 for x in out if x['cls'] == 'L'); pref = prefer if QUOTA is None else (('L', 'S') if nL < QUOTA * (len(out) + 1) else ('S', 'L'))
            if name in TC: pref = tuple(TC[name])
            elif name in TM:      # per-terminal fleet mix (Ben, 18 October): the class furthest behind its share goes first
                mix = TM[name]; cnt = {c_: sum(1 for x in out if x['term'] == name and x['cls'] == c_) for c_ in mix}; n_ = sum(cnt.values())
                pref = tuple(sorted(mix, key=lambda c_: -(mix[c_] * (n_ + 1) - cnt[c_]))) + tuple(k for k in PRM.get('fallback', []) if k not in mix)
            # zones (Ben, 18 October): the A380 stands together at T1B's north end; T1A's north side almost all large widebody
            nx = PRM.get('term_count', {}).get(name, {})
            zn = next((z for z in ZONES if z[0] == name and z[1].contains(Point(*p))), None)
            if zn is not None and zn[3]: s += 1.0; continue      # blocked: no stand starts here (Ben, 18 October: no angled stand off T1A's stem tip)
            if zn is not None:
                zp = tuple(k for k in zn[2] if k not in nx or sum(1 for x in out if x['term'] == name and x['cls'] == k) < nx[k])
                pref = zp + tuple(k for k in pref if k not in zp)
            else: pref = tuple(pref) + tuple(PRM.get('fallback', []))
            for c in pref:
                w = CLS[c]['span'] + WTC; d = CLS[c]['length'] + TAIL
                # square to the facade (Ben, 18 October: no strangely angled stands): the stand faces the chord of the nose line it covers;
                # a frontage across a corner (nose line more than CHORD_DEV off the chord) is refused; on a gentle curve the stand steps out by the bulge
                pb = np.array(ring.interpolate((s + w) % L).coords[0]); ch = pb - p; cl_ = np.linalg.norm(ch)
                if cl_ < 0.9 * w: continue
                tc = ch / cl_; nc = np.array([tc[1], -tc[0]])
                offs = [(np.array(ring.interpolate((s + k_) % L).coords[0]) - p) @ nc for k_ in np.arange(0, w + 0.1, 3.0)]
                if max(abs(o_) for o_ in offs) > CHORD_DEV: continue
                d0 = max(0.0, max(offs)); pm = p + tc * cl_ / 2
                e = rect(pm, tc, nc, cl_, d0, d0 + d)
                tl = CLS[c]['tlofa']; tz = rect(pm, tc, nc, cl_, d0 + d, d0 + ((DMAX if c in BIG else d + TLMAX) if MIXED else d + tl))    # mixed rows: the straight taxilane sits behind the deepest (large) stand
                if KEEPOUT is not None and KEEPOUT.intersects(e): continue
                if bld_x.intersects(e) or park_x.intersects(e) or tofa_x.intersects(e): continue
                if LANDSIDE is not None and (LANDSIDE.intersects(e) or LANDSIDE.intersects(tz)): continue
                if GROUNDS is not None and not (GROUNDS.contains(e) and GROUNDS.contains(tz)): continue
                if bld_t.intersects(tz) or LANE[c].intersects(tz.centroid.buffer(1)): continue
                ee = e.buffer(-0.05)
                if any(ee.intersects(x) for x in env) or any(ee.intersects(x) for x in tails) or any(tz.buffer(-0.05).intersects(x) for x in env): continue
                if PRM.get('dual') and any(tz.intersects(x) and tz.intersection(x).area > 0.15 * tz.area for x in tails): continue     # dual taxilanes: facing rows keep their own lane
                env.append(e); tails.append(tz); out.append(dict(term=name, cls=c, env=e, tail=tz)); s += w; placed = True; break
            if not placed: s += 1.0
    return out
if __name__ == '__main__':
    PREF = tuple(sys.argv[1]) if len(sys.argv) > 1 else ('L', 'S'); QUOTA = float(sys.argv[4]) if len(sys.argv) > 4 else None; OUT = sys.argv[2] if len(sys.argv) > 2 else 'cvg/gates.json'
    best = None
    for order in itertools.permutations(['Terminal 1A', 'Terminal 1B', 'Terminal 2', 'Terminal 3']):
        o = list(order); o.insert(o.index('Terminal 1B') + 1, 'Terminal 4'); o += [k for k in PRM.get('extra', {})]
        r = run(o, PREF); key = (len(r), sum(1 for x in r if x['cls'] == 'L'))
        if best is None or key > best[0]: best = (key, o, r)
    key, o, r = best
    tab = {}
    for x in r: d_ = tab.setdefault(x['term'], {}); d_[x['cls']] = d_.get(x['cls'], 0) + 1
    print('order', o); print(json.dumps(tab), 'total', len(r), 'L', key[1])
    json.dump(dict(order=o, params=PRM, by_terminal=tab, stands=[dict(term=x['term'], cls=x['cls'], env=mapping(x['env']), tail=mapping(x['tail'])) for x in r]), open(S + OUT, 'w'), default=float)
