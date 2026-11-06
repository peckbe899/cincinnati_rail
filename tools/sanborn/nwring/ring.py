try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Inner Ring North (OH-562 boulevard) for the deck page, 2026-10-23. The highway map's line (hwy/data.json, 'Inner ring' Boulevard, 8.1 km)
# runs on top of the rail corridor west of Norwood Central (frame s 3,400-4,350) and clips the station's north (Transvalley) tracks.
# Where it does, it is pushed north until its south edge (22.86 m from the centre) is 3 m outside the corridor (6 tracks, north rail at
# o +15, so +17.5 with the train) and outside Ben's station track area; elsewhere the map's line is kept. Writes nwring/ring_utm.json.
import json, numpy as np
from shapely.geometry import LineString, Point, Polygon
SP = _ws.DATA
F = json.load(open(SP + 'norwood/frame.json')); O = np.array(F['o']); t = np.array(F['t']); n = np.array(F['n'])
def P(s, o): return O + t * (s - 4300) + n * o
def so(p): d = np.asarray(p) - O; return float(d @ t) + 4300, float(d @ n)
H = json.load(open(SP + 'hwy/data.json')); Og = H['origin']
q = next(q for q in H['segs'] if q['r'] == 'Inner ring' and q['t'] == 'Boulevard')
L0 = LineString([(x + Og[0], y + Og[1]) for x, y in q['c']])
HALF, GAP = 22.86, 3.0
A = Polygon(json.load(open(SP + 'norwood/area_utm.json')))
def north_edge(s):                                    # north edge of what the ring must clear, at frame station s
    e = 17.5 if s <= 4300 else -1e9                   # the six-track corridor west of the station (Transvalley north track +15)
    if 4283 <= s <= 5209:
        seg = LineString([P(s, -300), P(s, 300)]).intersection(A)
        if not seg.is_empty: e = max(e, max(so(c)[1] for g in getattr(seg, 'geoms', [seg]) for c in g.coords))
    return e
S0, S1 = 3300.0, 4700.0                               # stretch to treat (the map's line leaves the corridor's side at both ends)
s_kmz = np.array([so(c)[0] for c in L0.coords]); o_kmz = np.array([so(c)[1] for c in L0.coords])
order = np.argsort(s_kmz); ss = np.arange(S0, S1 + 1, 5.0)
# the map line in this stretch is a function of s (monotone there)
okmz = np.interp(ss, s_kmz[order], o_kmz[order])
req = np.array([north_edge(s) + GAP + HALF for s in ss])
o = np.maximum(okmz, req)
for it in range(40):                                  # smooth (about 150 m window), keep clear of the corridor, keep the map line at the ends
    k = 31; pad = np.r_[np.full(k // 2, o[0]), o, np.full(k // 2, o[-1])]; o = np.convolve(pad, np.ones(k) / k, 'valid')
    o = np.maximum(o, req); o[:6] = okmz[:6]; o[-6:] = okmz[-6:]
moved = np.abs(o - okmz) > 0.5
print('moved from s', ss[moved].min(), 'to', ss[moved].max(), 'max shift', round(float((o - okmz).max()), 1), 'm at s', ss[np.argmax(o - okmz)])
# radius check of the new stretch
pts = np.array([P(s_, o_) for s_, o_ in zip(ss, o)]); d1 = np.gradient(pts, 5.0, axis=0); d2 = np.gradient(d1, 5.0, axis=0)
k_ = np.abs(d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]) / np.hypot(*d1.T) ** 3; print('min radius in stretch', round(float(1 / k_[10:-10].max())), 'm')
# splice: map line before S0, the treated stretch, map line after S1 (the ring runs east to west: start at Duck Creek)
a = L0.project(Point(P(S1, okmz[-1]))); b = L0.project(Point(P(S0, okmz[0])))
from shapely.ops import substring
east = substring(L0, 0, a); west = substring(L0, b, L0.length)
mid = [tuple(p) for p in pts[::-1]]
new = LineString(list(east.coords)[:-1] + mid + list(west.coords)[1:])
print('length map', round(L0.length), 'new', round(new.length))
print('south edge vs station area: band ∩ area', round(new.buffer(HALF, cap_style=2).intersection(A).area, 1), 'm2')
json.dump(dict(coords=[[round(x, 2), round(y, 2)] for x, y in new.coords], s_moved=[float(ss[moved].min()), float(ss[moved].max())],
               max_shift=float((o - okmz).max())), open(SP + 'nwring/ring_utm.json', 'w'))
