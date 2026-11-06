"""RER A from CUT past Evans to Westwood and to Northside: alignment, long section, structure and street crossings.
Ruled by Ben (2026-10-13): N2 (Northside branch on a viaduct over Hopple), 3.3% ramp from the deck edge, Westwood at
ground on the hill, 200 m curve; north of Hopple the viaduct eases to 167 m at the RER D crossing, holds 167 m through
South Cumminsville and Northside (both elevated) and drops at 3.3% from the Northside platform end to Linden Street,
where the line goes under on a box (Linden on the roof) into the tunnel under Spring Grove Cemetery.
Writes rera/rera.json. Usage: python3 rera/rera.py [G] [R]"""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, math, sys, numpy as np, rasterio
from pyproj import Transformer
from shapely.geometry import LineString, Point, shape
from shapely.ops import unary_union, substring
SP = _ws.DATA
DEM = rasterio.open(SP + 'handoff/out/map3_profile_dem_dm.vrt')
def gz(e, n):
    v = list(DEM.sample([(e, n)]))[0][0]; return None if v == -32768 else v / 10
T4 = Transformer.from_crs(4326, 26916, always_xy=True)
KMZ = {}
for line, sub, coords in json.load(open(SP + 'kmz/rer_lines.json')):
    g = LineString([T4.transform(lo, la) for lo, la in coords])
    KMZ.setdefault(sub, []).append(g)
def kmz_from_cut(sub):
    return min(KMZ[sub], key=lambda g: Point(g.coords[0]).distance(Point(712836, 4331872)))
A1 = kmz_from_cut('RER-1a [3:LineString]')                       # CUT to South Cumminsville
A2 = [g for g in KMZ['RER-1a [2:LineString]']][0]                # South Cumminsville to Winton Place
A = LineString(list(A1.coords) + list(A2.coords)[1:])
A1C = kmz_from_cut('RER-1c')                                     # the Westwood line (KMZ)
DK = json.load(open(SP + 'deck/deck.json'))['features']
deck = [shape(f['geometry']) for f in DK if f['properties']['layer'] == 'deck'][0]
deck_main = max(getattr(deck, 'geoms', [deck]), key=lambda g: g.area)
def decklvl(n): return 151.8 + (n - 4330700) / 4840 * 8.2
G = float(sys.argv[1]) if len(sys.argv) > 1 else 0.033          # ramp and descent grade (ruled 3.3%)
R = float(sys.argv[2]) if len(sys.argv) > 2 else 200.0          # Westwood curve radius (ruled 200 m)
CLR = 6.8                                                       # 5.8 m clear + 1.0 m structure
BOX, COVER = 4.6, 5.2                                           # portal rule (10j.7): open trough above 4.6 m rail depth, roof-as-street box 4.6-5.2 m, box with 0.6 m cover from 5.2 m
PL = 204.2
STN = {s[0]: Point(T4.transform(s[1], s[2])) for s in json.load(open(SP + 'rer_stations.json'))['RER-1']}
# ---------------- Westwood branch: platform centred on the KMZ station, heading 297.9 deg, at ground
W = np.array(STN['Westwood'].coords[0]); HW = 297.9; dW = np.array([math.sin(math.radians(HW)), math.cos(math.radians(HW))])
def a_dir(s): p, q = A.interpolate(s - 5), A.interpolate(s + 5); d = np.array([q.x - p.x, q.y - p.y]); return d / np.linalg.norm(d)
best = None
for s in np.arange(1400, 1900, 1.0):
    p = np.array(A.interpolate(s).coords[0]); d = a_dir(s)
    t, u = np.linalg.solve(np.array([d, dW]).T, W - p)
    if abs(t) < 0.6 and u > 0: best = (s, p, d, u); break
sI, I, dI, uI = best
dev = math.degrees(math.acos(np.clip(dI @ dW, -1, 1)))
TT = R * math.tan(math.radians(dev / 2))
sF = sI - TT; F = np.array(A.interpolate(sF).coords[0]); dF = a_dir(sF)
P2 = W - dW * (uI - TT)
nrm = np.array([-dF[1], dF[0]]); Cc = F + nrm * R
a0 = math.atan2(F[1] - Cc[1], F[0] - Cc[0]); a1 = math.atan2(P2[1] - Cc[1], P2[0] - Cc[0])
if a1 < a0: a1 += 2 * math.pi
arc = [tuple(Cc + R * np.array([math.cos(a), math.sin(a)])) for a in np.linspace(a0, a1, 40)]
pe, pw = W - dW * PL / 2, W + dW * PL / 2
s_join = A1C.project(Point(pw + dW * 120)); tailc = list(substring(A1C, s_join, A1C.length).coords)
WB = LineString([tuple(F)] + arc[1:] + [tuple(pe), tuple(W), tuple(pw), tuple(pw + dW * 120)] + tailc[1:])
# ---------------- long section, trunk and Northside branch (s from CUT along the KMZ line)
inter = A.intersection(deck_main.exterior)
S_EDGE = min(A.project(q) for q in getattr(inter, 'geoms', [inter]) if q.geom_type == 'Point' and A.project(q) > 800)
Z_EDGE = min(148.4, decklvl(A.interpolate(S_EDGE).y) - CLR)
S_TOP = S_EDGE + (164.5 - Z_EDGE) / G
BAS = json.load(open(SP + 'deckpage/basin.json'))['features']
HOP = [LineString(f['geometry']['coordinates']) for f in BAS if f['properties'].get('name') == 'Hopple Street' and f['properties'].get('set') == '1922'][0]   # deck level since 2026-10-14; the 1% rise from Beekman kept as a margin
hx = A.intersection(HOP); hx = hx if hx.geom_type == 'Point' else list(hx.geoms)[0]
S_HOP = A.project(hx); Z_HOPST = 160.8 + 0.010 * Point(711896, 4334920).distance(hx)
OVER = Z_HOPST + CLR
# RER D (TRIMET Greensburg-California, absolute 3D) where it crosses over
D3 = np.array(json.load(open(SP + 'cut/trimet3d.json'))['Greensburg-California 3D'])
D3L = LineString(D3[:, :2])
def d3z(p):
    i = int(np.argmin(np.hypot(D3[:, 0] - p.x, D3[:, 1] - p.y))); return float(D3[i, 2])
dx = A.intersection(D3L); dx = min(getattr(dx, 'geoms', [dx]), key=lambda q: abs(A.project(q) - S_HOP - 1500))
S_DX = A.project(dx); Z_DX = d3z(dx); Z_HOLD = 167.0
S_NS = A.project(STN['Northside']); S_NSE = S_NS + PL / 2
LIN = [LineString(f['geometry']['coordinates']) for f in BAS if f['properties'].get('name') == 'Linden Street'][0]
S_LIN = A.project(A.intersection(LIN))
S_END_PROF = S_LIN + 100                                       # beyond: bored tunnel under the cemetery, not profiled
def zA(s):
    if s <= 140: return 135.9                                  # under CUT's lower level (log 10l.26)
    if s <= 800: return 135.9 + (147.5 - 135.9) * (s - 140) / 660   # to Evans at yard level, under the deck
    if s <= S_EDGE: return 147.5 + (Z_EDGE - 147.5) * (s - 800) / (S_EDGE - 800)
    if s <= S_TOP: return Z_EDGE + G * (s - S_EDGE)
    if s <= S_HOP: return 164.5 + (OVER - 164.5) * (s - S_TOP) / (S_HOP - S_TOP)
    if s <= S_DX: return OVER + (Z_HOLD - OVER) * (s - S_HOP) / (S_DX - S_HOP)
    if s <= S_NSE: return Z_HOLD
    if s <= S_END_PROF: return Z_HOLD - G * (s - S_NSE)
    return None
zF = zA(sF)
L_to_pe = WB.project(Point(pe)); Z_PL = round(np.mean([gz(*(W + dW * t)) for t in np.linspace(-PL / 2, PL / 2, 11)]), 1)
GW = (Z_PL - zF) / L_to_pe
L_W_END = L_to_pe + PL + 60
def zW(s):
    if s <= L_to_pe: return zF + GW * s
    return Z_PL if s <= L_W_END else None
# ---------------- structure along each line
def classify(line, zf, s_deck=None, step=5.0):
    out = []
    for s in np.arange(0, line.length + step, step):
        s = min(s, line.length); z = zf(s); p = line.interpolate(s)
        if z is None: st = 'unprofiled'
        elif s_deck is not None and s <= s_deck: st = 'deck'
        else:
            g = gz(p.x, p.y); d = z - g if g is not None else 99
            st = 'viaduct' if d >= 5.0 else ('tunnel' if d <= -BOX else 'ramp')
        out.append((s, st))
    runs = []
    for s, st in out:
        if runs and runs[-1][2] == st: runs[-1][1] = s
        else: runs.append([s, s, st])
    for _ in range(3):                                        # fold runs under 25 m into the neighbour before them
        k = 1
        while k < len(runs):
            if runs[k][1] - runs[k][0] < 25 and len(runs) > 1:
                runs[k - 1][1] = runs[k][1]; del runs[k]
                if k < len(runs) and runs[k - 1][2] == runs[k][2]: runs[k - 1][1] = runs[k][1]; del runs[k]
            else: k += 1
    for k in range(1, len(runs)): runs[k][0] = runs[k - 1][1]
    return [dict(s0=round(a), s1=round(b), state=st, c=[[round(x, 1), round(y, 1)] for x, y in substring(line, a, b).coords]) for a, b, st in runs if b > a]
STRUCT = [dict(line='A', **r) for r in classify(A, zA, S_EDGE)] + [dict(line='westwood', **r) for r in classify(WB, zW)]
# ---------------- level marks for the page
def mk(line, s, label, anchor='right'):
    p = line.interpolate(s); return dict(p=[round(p.x, 1), round(p.y, 1)], label=label, anchor=anchor)
MARKS = [mk(A, 800, 'Evans, rail 147.5 m (under W Liberty)'), mk(A, S_EDGE, 'leaves the deck, rail %.1f m; 3.3%% up' % Z_EDGE, 'left'),
         mk(A, sF, 'fork, rail %.1f m' % zF, 'left'), mk(WB, L_to_pe - 150, 'Westwood branch %.2f%% up' % (GW * 100), 'left'),
         mk(WB, L_to_pe + PL / 2, 'Westwood, platform at ground %.1f m' % Z_PL),
         mk(A, S_HOP, 'over Hopple, rail %.1f m' % OVER), mk(A, S_DX, 'under RER D (%.1f m), rail %.1f m' % (Z_DX, Z_HOLD)),
         mk(A, S_NSE, 'Northside platform end, 3.3% down', 'left'), mk(A, S_LIN, 'Linden over the box, rail %.1f m' % zA(S_LIN)),
         mk(A, S_LIN + 60, 'tunnel under Spring Grove Cemetery', 'left')]
out = dict(grade=G, radius=R, option='N2', s_edge=round(S_EDGE), z_edge=round(Z_EDGE, 1), s_top=round(S_TOP), fork=[round(v, 1) for v in F], s_fork=round(sF),
           z_fork=round(zF, 1), westwood_curve_deg=round(dev, 1), westwood_grade=round(GW, 4), westwood_platform=round(Z_PL, 1), s_hopple=round(S_HOP),
           hopple_level=round(Z_HOPST, 1), rail_over_hopple=round(OVER, 1), s_rerd=round(S_DX), rerd_level=round(Z_DX, 2), hold=Z_HOLD, s_northside=round(S_NS),
           s_northside_end=round(S_NSE), s_linden=round(S_LIN), z_linden=round(zA(S_LIN), 1), s_end_profile=round(S_END_PROF))
# ---------------- crossings: deck and basin streets
streets = []
for f in DK:
    p = f['properties']
    if p['layer'] == 'street': streets.append((p['name'], p.get('id'), LineString(f['geometry']['coordinates']), 'deck'))
for f in BAS:
    p = f['properties']
    if p['layer'] != 'street' or p.get('kind') == 'we_alley' and not p.get('name'): continue
    streets.append((p['name'] or 'alley', p.get('id'), LineString(f['geometry']['coordinates']), 'hopple' if (p.get('name') == 'Hopple Street' and p.get('set') == '1922') else 'basin'))
def street_z(q, kind):
    if kind == 'hopple': return Z_HOPST
    if kind == 'deck' and deck.buffer(0.5).contains(q): return decklvl(q.y)
    return gz(q.x, q.y)
def cross(line, zf, label, s_deck=None):
    res = []
    for nm, sid, g, kind in streets:
        x = line.intersection(g)
        for q in getattr(x, 'geoms', [x]):
            if q.is_empty or q.geom_type != 'Point': continue
            s = line.project(q); zr = zf(s)
            if zr is None: continue
            zs = street_z(q, kind)
            if zs is None: continue
            d = zr - zs
            if s_deck is not None and s <= s_deck and zr <= decklvl(q.y) - CLR + 0.05: st = 'under the deck'
            elif d >= CLR: st = 'street under'
            elif d <= -COVER: st = 'over the box'
            elif d <= -BOX: st = 'on the box roof'
            else: st = 'CUT'
            res.append(dict(line=label, street=nm, id=sid, s=round(s), x=round(q.x, 1), y=round(q.y, 1), rail=round(zr, 1), street_z=round(zs, 1), diff=round(d, 1), result=st))
    return res
X = cross(A, zA, 'trunk/Northside', S_EDGE) + cross(WB, zW, 'Westwood')
out['crossings'] = sorted(X, key=lambda r: (r['line'], r['s']))
out['lines'] = dict(A=[[round(x, 1), round(y, 1)] for x, y in A.coords], westwood=[[round(x, 1), round(y, 1)] for x, y in WB.coords])
out['struct'] = STRUCT; out['marks'] = MARKS
out['profiles'] = dict(A=[[s, zA(s) and round(zA(s), 2), gz(*A.interpolate(s).coords[0])] for s in range(0, int(A.length), 10)],
                       westwood=[[s, zW(s) and round(zW(s), 2), gz(*WB.interpolate(s).coords[0])] for s in range(0, int(WB.length), 10)])
json.dump(out, open(SP + 'rera/rera.json', 'w'))
if __name__ == '__main__':
    print({k: v for k, v in out.items() if k not in ('crossings', 'lines', 'profiles', 'struct', 'marks')})
    for r in STRUCT: print('  struct', r['line'], r['state'], r['s0'], r['s1'])
    for r in out['crossings']:
        if r['result'] not in ('under the deck',) and r['s'] < S_END_PROF: print('  ', r['line'], r['street'], r['s'], r['rail'], r['street_z'], r['diff'], r['result'])
