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
a = g('APEx Transcontinental Limited (1 of 2)'); b = g('APEx Transcontinental Limited (2 of 2)')
km = np.array(FR._mid(a.tolist(), b.tolist(), n=4000)); KM = LineString(km)
S0 = 8080.0; p0 = Q.TR.at(S0)[0]; u0 = Q.TR.tan(S0); nR = np.array([u0[1], -u0[0]])
print('u0 bearing %.2f' % np.degrees(np.arctan2(*u0)))
pA = p0 + nR * 9.0                                   # Norwood centre line at s 8,080
# KMZ 70 deg straight: fit through vertices 4..6 of (1 of 2) and (2 of 2) mid
P70 = (a[4:7] + b[4:7]) / 2 if len(a) == len(b) else a[4:7]
c = P70.mean(axis=0); _, _, vt = np.linalg.svd(P70 - c); u70 = vt[0] * np.sign(vt[0] @ (P70[-1] - P70[0]))
print('70 straight bearing %.2f' % np.degrees(np.arctan2(*u70)), 'P70', P70.round(1))
NO, NTV = FR.NO, FR.NTV
def isect(p1, u1, p2, u2): t, v = np.linalg.solve(np.c_[u1, -u2], p2 - p1); return p1 + u1 * t, t, v
PI1, t1, _ = isect(pA, u0, c, u70); PI2, t2, _ = isect(c, u70, NO, NTV)
d1 = np.arccos(u0 @ u70); d2 = np.arccos(u70 @ NTV); L12 = np.hypot(*(PI2 - PI1))
print('PI1', PI1.round(1), 'T1max (from s 8080) %.0f' % t1, 'defl1 %.2f' % np.degrees(d1))
print('PI2', PI2.round(1), 'defl2 %.2f' % np.degrees(d2), 'L12 %.0f' % L12, 'nw s at PI2 %.0f' % FR.nw_so(PI2)[0])
# single arc tangent to all three lines (right-hand curve): R*(tan(d1/2)+tan(d2/2)) = L12
R3 = L12 / (np.tan(d1 / 2) + np.tan(d2 / 2)); T1 = R3 * np.tan(d1 / 2); T2 = R3 * np.tan(d2 / 2)
st = PI1 - u0 * T1; en = PI2 + NTV * T2
print('one arc touching the 70 straight: R %.0f, starts %.0f m after s 8080 (s %.0f), ends at nw s %.0f' % (R3, t1 - T1, S0 + t1 - T1, FR.nw_so(en)[0]))
# deviation from KMZ
nl = np.array([u0[1], -u0[0]]); O = st + nl * R3
ang0 = np.arctan2(*(st - O)[::-1]); ang1 = np.arctan2(*(en - O)[::-1]); da = (ang1 - ang0 + np.pi) % (2 * np.pi) - np.pi
arc = np.array([O + R3 * np.array([np.cos(ang0 + da * f), np.sin(ang0 + da * f)]) for f in np.linspace(0, 1, 400)])
dev = [KM.distance(Point(q)) for q in arc]; print('max dev from KMZ centre %.1f m' % max(dev))
# alternatives: start at s 8080 (max T1), curve 1 R and then curve 2 with remaining
R1 = t1 / np.tan(d1 / 2); rem = L12 - t1; R2 = rem / np.tan(d2 / 2)
print('curve 1 from s 8080: R1 %.0f; curve 2 with the rest: R2 %.0f, ends nw s %.0f' % (R1, R2, FR.nw_so(PI2 + NTV * rem)[0]))
# single arc trunk-line +9 to axis (ignoring 70 straight)
PIx, tx, _ = isect(pA, u0, NO, NTV); dx = np.arccos(u0 @ NTV); Rx = tx / np.tan(dx / 2); print('single arc from s 8080 to axis: R %.0f' % Rx)
Tx = tx; stx = PIx - u0 * Tx; enx = PIx + NTV * Tx; Ox = stx + nl * Rx
a0 = np.arctan2(*(stx - Ox)[::-1]); a1 = np.arctan2(*(enx - Ox)[::-1]); da = (a1 - a0 + np.pi) % (2 * np.pi) - np.pi
arcx = np.array([Ox + Rx * np.array([np.cos(a0 + da * f), np.sin(a0 + da * f)]) for f in np.linspace(0, 1, 400)])
print('R %.0f max dev %.1f, ends nw s %.0f' % (Rx, max(KM.distance(Point(q)) for q in arcx), FR.nw_so(enx)[0]))
