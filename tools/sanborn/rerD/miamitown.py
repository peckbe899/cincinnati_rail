try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# RER D extended west of the region edge to Miamitown South (Ben, 27 October 2026). KMZ line as drawn (RER-4 'Greensburg-CUT TRIMET'),
# from the end of R-D-699000-4341758 to the west end of the Miamitown South platform (terminus). Island platform, tracks and taper as
# transit/build_transit.py (offset_curves). Idempotent. Writes deckpage/context.json (backup deckpage/context_v133.json).
import json, sys, numpy as np, xml.etree.ElementTree as ET
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import substring
S = _ws.DATA
RER = dict(h0=2.25, island=11.0, edge=1.75); TAPER = 40.0; RPL = 204.2
tr = Transformer.from_crs(4326, 26916, always_xy=True); ns = {'k': 'http://www.opengis.net/kml/2.2'}
root = ET.parse(S + 'kmz/cr.kml').getroot(); K = None; MS = None
for pm in root.iter('{http://www.opengis.net/kml/2.2}Placemark'):
    nm = (pm.find('k:name', ns).text or '').strip()
    if nm == 'Greensburg-CUT TRIMET' and K is None:
        K = LineString([tr.transform(*map(float, q.split(',')[:2])) for q in pm.find('.//k:LineString/k:coordinates', ns).text.split()])
    if nm == 'Miamitown South':
        MS = Point(tr.transform(*map(float, pm.find('.//k:Point/k:coordinates', ns).text.strip().split(',')[:2])))
C = json.load(open(S + 'deckpage/context.json'))
if any(s['name'] == 'Miamitown South' for s in C['rer_stations']): sys.exit('already there')
json.dump(C, open(S + 'deckpage/context_v133.json', 'w'), separators=(',', ':'))
west = [r for r in C['rer'] if r['id'] == 'R-D-699000-4341758'][0]
J = Point(min(west['c'], key=lambda p: p[0]))                       # the piece's west end, on the region edge
sJ, sM = K.project(J), K.project(MS)                                # the KMZ runs Greensburg (west) -> CUT, so sM < sJ
s_end = sM - RPL / 2                                                # terminus: the line stops at the platform's west end
g = substring(K, sJ, s_end)                                         # east -> west, like the other D pieces outside the window
g = LineString([J.coords[0]] + list(g.coords)[1:])
stp = K.interpolate(sM); ch = g.project(stp)
# offset_curves (transit/build_transit.py), island
n = max(2, int(g.length / 2.0)); ds = np.linspace(0, g.length, n + 1)
P = np.array([g.interpolate(d).coords[0] for d in ds])
tang = np.gradient(P, axis=0); tang /= np.hypot(tang[:, 0], tang[:, 1])[:, None] + 1e-9
for _ in range(3): tang[1:-1] = (tang[:-2] + 2 * tang[1:-1] + tang[2:]) / 4
tang /= np.hypot(tang[:, 0], tang[:, 1])[:, None] + 1e-9; nrm = np.c_[-tang[:, 1], tang[:, 0]]
h = np.full(len(ds), RER['h0']); hs = RER['island'] / 2 + RER['edge']
dd = np.abs(ds - ch) - RPL / 2; w = np.clip(1 - dd / TAPER, 0, 1); h = np.maximum(h, RER['h0'] + (hs - RER['h0']) * w)
r1 = lambda p: [round(p[0], 1), round(p[1], 1)]
pid = 'R-D-%d-%d' % (round(g.coords[-1][0]), round(g.coords[-1][1]))
for s in (1, -1): C['tracks'].append(dict(sys='rer', line='D', pid=pid, c=[r1(q) for q in LineString(P + nrm * h[:, None] * s).simplify(0.2).coords]))
sel = (ds >= ch - RPL / 2 - 0.01) & (ds <= ch + RPL / 2); Q = P[sel]; N_ = nrm[sel]; hw = RER['island'] / 2
ring = Polygon(np.r_[Q + N_ * hw, (Q - N_ * hw)[::-1]]).simplify(0.2)
C['plats'].append(dict(sys='rer', line='D', pid=pid, c=[r1(q) for q in ring.exterior.coords], st='Miamitown South', id='P-R-D-%d-%d' % (round(stp.x), round(stp.y))))
C['rer'].append(dict(id=pid, name='RER D', lines=['D'], sub='Greensburg-CUT TRIMET, outside the region: KMZ line as drawn, to Miamitown South (terminus; Ben, 27 October 2026)', c=[r1(q) for q in g.coords]))
C['rer_stations'].append(dict(name='Miamitown South', lines=['D'], p=r1(stp.coords[0])))
json.dump(C, open(S + 'deckpage/context.json', 'w'), separators=(',', ':'))
print(pid, 'length %.1f m' % g.length, 'station', r1(stp.coords[0]), 'KMZ station off line %.1f m' % K.distance(MS), 'platform west end', r1(g.coords[-1]))
