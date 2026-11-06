try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, math, numpy as np
from shapely.geometry import LineString, Point
S = _ws.DATA
F = json.load(open(S + 'cvgkmz/cvg_final.json'))
D = np.load(S + 'topo/dem2m.npy', mmap_mode='r'); M = json.load(open(S + 'topo/dem2m.json'))
def gnd(p): return float(D[int((M['y1'] - p[1]) / 2), int((p[0] - M['x0']) / 2)]) / 10
TD = F['CVG Express 5 - Today']['c']; P4 = F['CVG Express 4']['c']
STP = {k: tuple(F['Terminal ' + k]['c'][0]) for k in ('3', '2', '4', '1B', '1A')}
def line_fit(pts):
    P = np.array(pts); c = P.mean(0); u = np.linalg.svd(P - c)[2][0]; return c, u / np.linalg.norm(u)
def inter(c1, u1, c2, u2):
    A = np.array([u1, -u2]).T; t = np.linalg.solve(A, np.subtract(c2, c1)); return np.array(c1) + u1 * t[0]
p4e = np.array(P4[-1]); u1 = np.subtract(P4[-1], P4[-3]); u1 = u1 / np.linalg.norm(u1)
c2, u2 = line_fit([TD[5], TD[6]])
c3, u3 = line_fit([TD[11], TD[12], STP['3'], STP['2'], STP['4']])
c4, u4 = line_fit([TD[17], TD[18], STP['1B'], STP['1A']])
c5, u5 = line_fit([TD[-2], TD[-1]])
V12, V23, V34, V45 = inter(p4e, u1, c2, u2), inter(c2, u2, c3, u3), inter(c3, u3, c4, u4), inter(c4, u4, c5, u5)
END = np.array(TD[-1])
print('V', [list(map(round, v)) for v in (V12, V23, V34, V45)])
def turn(a, b, c):
    u = (a - b) / np.linalg.norm(a - b); w = (c - b) / np.linalg.norm(c - b); return math.pi - math.acos(np.clip(np.dot(u, w), -1, 1))
def proj(c, u, p): return np.array(c) + u * np.dot(np.subtract(p, c), u)
st = {k: (proj(c3, u3, STP[k]) if k in '324' else proj(c4, u4, STP[k])) for k in STP}
print('station offsets from fitted lines', {k: round(math.dist(st[k], STP[k]), 1) for k in st})
L = 150 / 2
# tangent limits
th12, th23, th34, th45 = turn(p4e, V12, V23), turn(V12, V23, V34), turn(V23, V34, V45), turn(V34, V45, END)
d3s = math.dist(V23, st['3']) - L; d4n = math.dist(V34, st['4']) - L; d1be = math.dist(V34, st['1B']) - L; d1aw = math.dist(V45, st['1A']) - L
Tben12 = min(math.dist(V12, p4e), math.dist(V12, TD[5])); Tben23 = (math.dist(V23, TD[6]) + math.dist(V23, TD[11])) / 2
Tben34 = (math.dist(V34, TD[12]) + math.dist(V34, TD[17])) / 2; Tben45 = (math.dist(V45, TD[18]) + math.dist(V45, TD[-2])) / 2
print('turns deg', [round(math.degrees(t), 1) for t in (th12, th23, th34, th45)])
print('Ben tangents', round(Tben12), round(Tben23), round(Tben34), round(Tben45), '-> Ben radii', [round(T / math.tan(t / 2)) for T, t in ((Tben12, th12), (Tben23, th23), (Tben34, th34), (Tben45, th45))])
print('limits: T3 S end', round(d3s), 'T4 N end', round(d4n), 'T1B E end', round(d1be), 'T1A W end', round(d1aw), 'V12 to p4e', round(math.dist(V12, p4e)))
for k in st: print(k, list(map(round, st[k])), 'ground', round(gnd(st[k]), 1))
for p in [(700800, 4326650), (700800, 4326800), (700820, 4327000), (700850, 4327200), (700790, 4326550), (701100, 4326100), (702573, 4325547)]: print('ground', p, round(gnd(p), 1))
