try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys, numpy as np
from shapely.geometry import LineString, Point
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'trunk2'); sys.path.insert(0, _ws.CODE + 'trunk')
import geo4 as Q
import frames as FR
T = json.load(open(SP + 'deckpage/tracks.json'))
def g(n): return np.array([f for f in T['features'] if f['properties'].get('name') == n][0]['geometry']['coordinates'])[:, :2]
# trunk heading along 7000..8600
for s in range(7000, 8601, 100):
    t = Q.TR.tan(s); print(s, 'bearing %.2f' % np.degrees(np.arctan2(t[0], t[1])))
sw = (g('APEx Southwest Chief (1 of 2)')[::-1] + g('APEx Southwest Chief (2 of 2)')[::-1]) / 2 if len(g('APEx Southwest Chief (1 of 2)')) == len(g('APEx Southwest Chief (2 of 2)')) else None
a, b = g('APEx Southwest Chief (1 of 2)')[::-1], g('APEx Southwest Chief (2 of 2)')[::-1]
m = np.array(FR._mid(a.tolist(), b.tolist()))
L = LineString(m)
for d in range(0, 4000, 200):
    p = np.array(L.interpolate(d).coords[0]); q = np.array(L.interpolate(d + 50).coords[0]); u = q - p
    print('SW', d, p.round(1), 'bearing %.2f' % np.degrees(np.arctan2(u[0], u[1])))
print('---')
def isect(p1, u1, p2, u2):
    t, v = np.linalg.solve(np.c_[u1, -u2], p2 - p1); return p1 + u1 * t, t, v
s_ref = 8300.0; pT = Q.TR.at(s_ref)[0]; uT = Q.TR.tan(s_ref)
pS = np.array(L.interpolate(400).coords[0]); uS = np.array(L.interpolate(1400).coords[0]) - pS; uS /= np.hypot(*uS)
PI, t, v = isect(pT, uT, pS, uS); sPI = Q.TR.proj(PI) if False else s_ref + t
dfl = np.arccos(uT @ uS); print('Dayton PI', PI.round(1), 's_PI %.0f' % sPI, 'defl %.2f' % np.degrees(dfl))
for s0 in (8080, 8150, 8200, 8300, 8400, 8568):
    Tn = sPI - s0; R = Tn / np.tan(dfl / 2); CT = PI + uS * Tn
    print('  start', s0, 'R %.0f' % R, 'end on SW at', CT.round(1), 'SW chain %.0f' % L.project(Point(CT)))
NO, NTV = FR.NO, FR.NTV
PIn, t2, v2 = isect(pT, uT, NO, NTV); dn = np.arccos(np.clip(uT @ NTV, -1, 1))
print('Norwood PI', PIn.round(1), 's_PI %.0f' % (s_ref + t2), 'defl %.2f' % np.degrees(dn), 'nw s at PI %.0f' % FR.nw_so(PIn)[0])
for s0 in (8080, 8200, 8300, 8400, 8500, 8600):
    Tn = s_ref + t2 - s0; R = Tn / np.tan(dn / 2); CT = PIn + NTV * Tn
    print('  start', s0, 'R %.0f' % R, 'end', CT.round(1), 'nw s %.0f' % FR.nw_so(CT)[0])
