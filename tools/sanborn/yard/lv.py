try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Levels of the lines that pass under the deck, by position, from the Rail Profiles saved docs (rp_new/_db/all.json)
# and the Deck page's RER A marks (10z.4). Plain linear interpolation between bend points (vertical curves ignored).
import json, math
from pyproj import Transformer
from shapely.geometry import LineString, Point
S = _ws.DATA
TR = Transformer.from_crs(4326, 26916, always_xy=True).transform
DB = json.load(open(S + 'rp_new/_db/all.json'))

def deck_z(n): return 151.8 + (n - 4330700) / 4840 * 8.2
def yard_z(n): return deck_z(n) - 8.5

class Route:
    def __init__(self, rid, fn):
        L = json.load(open(fn)); P = L['path'] if isinstance(L['path'], list) else eval(L['path'])
        self.c = [p[0] for p in P]; self.xy = [TR(p[1], p[2]) for p in P]; self.line = LineString(self.xy)
        d = DB[rid]; self.pvi = sorted(d['pvi']); self.st = d.get('st', {}); self.doc = d
        st = L['stations'] if isinstance(L['stations'], list) else eval(L['stations'])
        self.stc = {s['name']: s['c'] for s in st}
        self.plat = d.get('platform_m', 204.2)
    def chain(self, x, y):
        s = self.line.project(Point(x, y)); acc = 0
        for i in range(1, len(self.xy)):
            seg = math.dist(self.xy[i - 1], self.xy[i])
            if acc + seg >= s: f = (s - acc) / seg if seg else 0; return self.c[i - 1] + f * (self.c[i] - self.c[i - 1]), self.line.distance(Point(x, y))
            acc += seg
        return self.c[-1], self.line.distance(Point(x, y))
    def z(self, c):
        for name, sc in self.stc.items():   # platform flats hold the station level
            if name in self.st and abs(c - sc) <= self.plat / 2: return self.st[name]
        P = self.pvi
        if not P: return None
        if c <= P[0][0]: return P[0][1]
        for (c0, z0), (c1, z1) in zip(P, P[1:]):
            if c0 <= c <= c1: return z0 + (z1 - z0) * (c - c0) / (c1 - c0) if c1 > c0 else z0
        return P[-1][1]

R = {}
def route(rid):
    if rid not in R: R[rid] = Route(rid, S + f'rp_new/rer/lines/{rid}.json')
    return R[rid]
