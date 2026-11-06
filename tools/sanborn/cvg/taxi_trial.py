try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Ben (18 October): trial taxi paths gate <-> runway on the CVG taxiway network.
# Graph from cvg/_taxi_raw.json (centre lines before the runway pavement is cut out). A node on a runway centre line that a path passes
# through (not its start or end) is a runway crossing. Departures start at the threshold of the departure end; arrivals leave the runway by
# an exit angled for the landing direction at least MIN_ROLL along the runway (or the far-end entry). Reports, per terminal and runway
# direction: mean taxi distance over the terminal's stands, crossings, and stands with no route.
import json, sys, math, numpy as np, networkx as nx
from shapely.geometry import LineString, Point, shape, MultiLineString
from shapely.ops import unary_union, nearest_points
S = _ws.DATA
RAW = json.load(open(S + (sys.argv[1] if len(sys.argv) > 1 else 'cvg/_taxi_raw.json')))
AP = json.load(open(S + (sys.argv[2] if len(sys.argv) > 2 else 'deckpage/airport.json')))
MIN_ROLL = 1500.0
RW = {f['properties']['name'].replace('Runway ', ''): LineString(f['geometry']['coordinates']) for f in AP['features'] if f['properties']['layer'] == 'cvg_runway_cl'}
lines = [LineString(r['c']) for r in RAW]
names = [r['name'] for r in RAW]
U = unary_union(lines + list(RW.values()))        # runway centre lines node the taxiways that cross them
segs = list(getattr(U, 'geoms', [U]))
def key(p): return (round(p[0], 1), round(p[1], 1))
G = nx.Graph()
from shapely.strtree import STRtree
tree = STRtree(lines)
for sg in segs:
    c = list(sg.coords)
    m = sg.interpolate(0.5, normalized=True); idx = tree.query(m.buffer(0.5)); nm = next((names[i] for i in idx if lines[i].distance(m) < 0.5), None)
    if nm is None: continue          # a piece of runway centre line, not a taxiway
    for a, b in zip(c[:-1], c[1:]):
        G.add_edge(key(a), key(b), w=math.dist(a, b), name=nm)
# runway nodes
rwn = {}
for k in G.nodes:
    for r, l in RW.items():
        if l.distance(Point(k)) < 1.5: rwn[k] = r
def crossings(path):
    out = []
    for k in path[1:-1]:
        if k in rwn and (not out or out[-1] != rwn[k]): out.append(rwn[k])
    return out
def nearest_node(pt, pool=None):
    pool = pool or list(G.nodes); a = np.array(pool); d = np.hypot(a[:, 0] - pt[0], a[:, 1] - pt[1]); i = int(d.argmin()); return tuple(pool[i]), float(d[i])
# gate nodes: the point of the apron taxilane network nearest each stand's tail
apr = [l for l, n in zip(lines, names) if n == 'Apron taxilane']
AU = unary_union(apr)
stands = [f for f in AP['features'] if f['properties']['layer'] == 'cvg_stand']
def gate_node(f):
    g = shape(f['geometry']); c = np.array(g.exterior.coords); tail = (c[2] + c[3]) / 2
    q = nearest_points(AU, Point(*tail))[0]
    # insert q into the graph by splitting the edge it lies on
    best = None
    for a, b in G.edges:
        if G.edges[a, b]['name'] != 'Apron taxilane': continue
        d = LineString([a, b]).distance(q)
        if best is None or d < best[0]: best = (d, a, b)
    d, a, b = best; k = key((q.x, q.y))
    if k not in G:
        w = G.edges[a, b]['w']; G.remove_edge(a, b)
        G.add_edge(a, k, w=math.dist(a, k), name='Apron taxilane'); G.add_edge(k, b, w=math.dist(k, b), name='Apron taxilane')
    return k
for f in stands: f['_n'] = gate_node(f)
# runway ends and exits
def ends(r):
    l = RW[r]; a, b = l.coords[0], l.coords[-1]; return (a, b)
DIRS = {}     # 'dep 18R' -> threshold node; 'arr 18R' -> list of (exit node)
for r, l in RW.items():
    a, b = np.array(l.coords[0]), np.array(l.coords[-1]); lo, hi = r.split('/')
    # lo = 18x / 9x (heading 180 / 090): 18 departs from the north end, 9 from the west end
    if lo.startswith('18'): first = a if a[1] > b[1] else b
    else: first = a if a[0] < b[0] else b
    last = b if first is a else a
    for name_, start, stop in ((lo, first, last), (hi, last, first)):
        u = (stop - start) / np.linalg.norm(stop - start)
        thr, dth = nearest_node(start, [k for k in rwn if rwn[k] == r])
        ex = []
        for k in [k for k in rwn if rwn[k] == r]:
            roll = (np.array(k) - start) @ u
            if roll < MIN_ROLL: continue
            ok = False
            for nb in G.neighbors(k):
                v = np.array(nb) - np.array(k); vn = v / max(np.linalg.norm(v), 1e-6)
                if vn @ u > 0.3 or (np.linalg.norm(np.array(k) - stop) < 5 and abs(vn @ u) < 0.3): ok = True     # exit angled forward, or the far-end entry
                if abs(vn @ u) < 0.3 and roll > 2600: ok = True                                                         # a right-angle exit late in the roll
            if ok: ex.append((roll, k))
        DIRS[name_] = dict(thr=thr, dth=dth, exits=sorted(ex))
# graph without passing along a runway (only crossing it): forbid edges whose both ends lie on the same runway centre line
H = G.copy()
for a, b in list(H.edges):
    if a in rwn and b in rwn and rwn[a] == rwn[b]: H.remove_edge(a, b)
def route(src, dst):
    try: p = nx.shortest_path(H, src, dst, weight='w'); return nx.path_weight(H, p, 'w'), p
    except nx.NetworkXNoPath: return None, None
T = ['Terminal 1A', 'Terminal 1B', 'Terminal 2', 'Terminal 3', 'Terminal 4']
res = {}
for t in T:
    sts = [f for f in stands if f['properties']['terminal'] == t]
    for dname, D in DIRS.items():
        dep = [route(f['_n'], D['thr']) for f in sts]
        arr = []
        for f in sts:
            best = None
            for roll, k in D['exits']:
                w, p = route(k, f['_n'])
                if w is not None and (best is None or w < best[0]): best = (w, p)
            arr.append(best or (None, None))
        def summ(rr):
            ok = [x for x in rr if x[0] is not None]
            if not ok: return dict(n_none=len(rr))
            cr = [len(crossings(p)) for w, p in ok]
            return dict(km=round(np.mean([w for w, p in ok]) / 1000, 2), cross=round(float(np.mean(cr)), 1), maxcross=max(cr), n_none=len(rr) - len(ok),
                        via=sorted({G.edges[a, b]['name'].split(' (')[0] for w, p in ok[:1] for a, b in zip(p[:-1], p[1:])}))
        res[(t, dname)] = dict(dep=summ(dep), arr=summ(arr))
# dead ends: degree-1 nodes that are not on a runway, not a gate
gates = {f['_n'] for f in stands}
dead = [k for k in G.nodes if G.degree(k) == 1 and k not in rwn and k not in gates]
comp = sorted((len(c) for c in nx.connected_components(G)), reverse=True)
print('components', comp[:6], 'dead ends', len(dead))
for (t, d), v in res.items():
    print(f"{t:12s} {d:4s} DEP {v['dep'].get('km','-'):>5} km x{v['dep'].get('cross','-')} none {v['dep']['n_none']:2d} | ARR {v['arr'].get('km','-'):>5} km x{v['arr'].get('cross','-')} none {v['arr']['n_none']:2d}")
json.dump(dict(dead=dead, res={f'{t}|{d}': v for (t, d), v in res.items()}), open(S + 'cvg/_taxi_trial.json', 'w'), default=float)
# ---------------------------------------------------------------- plot (python3 cvg/taxi_trial.py RAW AIRPORT PNG)
if len(sys.argv) > 3:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(22, 13))
    PRIM = {'Terminal 1A': ['18R', '36L'], 'Terminal 1B': ['18R', '36L'], 'Terminal 2': ['18C', '36C', '18L', '36R'], 'Terminal 3': ['18C', '36C', '18L', '36R'], 'Terminal 4': ['18L', '36R', '18C', '36C']}
    cols = {'Terminal 1A': 'tab:red', 'Terminal 1B': 'tab:orange', 'Terminal 2': 'tab:blue', 'Terminal 3': 'tab:green', 'Terminal 4': 'tab:purple'}
    for ax, mode in zip(axs, ('dep', 'arr')):
        for f in AP['features']:
            p = f['properties']
            if p['layer'] in ('cvg_runway', 'cvg_building', 'cvg_stand'):
                g = shape(f['geometry'])
                for q in getattr(g, 'geoms', [g]): ax.fill(*q.exterior.xy, color={'cvg_runway': '0.55', 'cvg_building': '#7a5c99', 'cvg_stand': '0.85'}[p['layer']], lw=0)
        for a, b in G.edges: ax.plot([a[0], b[0]], [a[1], b[1]], color='0.7', lw=0.8)
        for k in dead: ax.plot(*k, 'kx', ms=5)
        for t, rws in PRIM.items():
            sts = [f for f in stands if f['properties']['terminal'] == t]
            f = sts[len(sts) // 2]
            for i, r in enumerate(rws):
                D = DIRS[r]
                if mode == 'dep': w, p = route(f['_n'], D['thr'])
                else:
                    best = None
                    for roll, k in D['exits']:
                        w, pp = route(k, f['_n'])
                        if w is not None and (best is None or w < best[0]): best = (w, pp)
                    w, p = best or (None, None)
                if p: ax.plot([q[0] for q in p], [q[1] for q in p], color=cols[t], lw=2.2 - 0.4 * i, alpha=0.8, ls=['-', '--', '-.', ':'][i])
        for r, l in RW.items(): ax.annotate(r, l.coords[0], fontsize=9)
        ax.set_aspect('equal'); ax.set_title(mode + ' (solid/dashed: first two runways listed; T1A/T1B -> 18R/36L, T2/T3 -> 18C/36C then 18L/36R, T4 -> 18L/36R then 18C/36C); x = dead end')
        ax.set_xlim(699300, 704100); ax.set_ylim(4322400, 4327700)
    plt.tight_layout(); plt.savefig(S + sys.argv[3], dpi=70)
