try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# CUT approach tracks for the Mill Creek Deck page, v2 (2026-10-10): straight trunk Camp Washington-CUT,
# freight passing track, CS and C&O connections on the TRIMET_Lines.kmz 3D bridge and viaduct alignments.
# Writes deckpage/tracks.json in UTM 16N. Schematic track centrelines, not survey.
import json, math
import numpy as np
from shapely.geometry import LineString

OUT = (_ws.DATA + 'deckpage/tracks.json')
APX = json.load(open((_ws.DATA + 'cut/apex_cut.json')))

APEX_RAIL, LOWER_RAIL = 144.0, 131.9
FW, FE = 712686.0, 712838.0          # APEx platform zone (deck page precinct: headhouse east face to building)
FN0, FN1 = 4331646.0, 4332134.0      # 1,600 ft = 487.7 m, centred on the 1955 field
NT, ST = 4332400.0, 4331400.0        # APEx throat ends (1955 image)
FC = (FW + FE) / 2                   # field centre E 712,762

F = []
def add(layer, coords, **p):
    F.append(dict(type='Feature', properties=dict(layer=layer, **p),
                  geometry=dict(type='LineString', coordinates=[[round(x, 1), round(y, 1)] for x, y in coords])))
def addpoly(layer, ring, **p):
    F.append(dict(type='Feature', properties=dict(layer=layer, **p),
                  geometry=dict(type='Polygon', coordinates=[[[round(x, 1), round(y, 1)] for x, y in ring]])))
def addpt(layer, xy, **p):
    F.append(dict(type='Feature', properties=dict(layer=layer, **p),
                  geometry=dict(type='Point', coordinates=[round(xy[0], 1), round(xy[1], 1)])))

def bez(a, b, n=24, k=0.42):
    """Cubic Bezier from a to b with vertical (N-S) tangents at both ends."""
    (x0, y0), (x1, y1) = a, b
    L = abs(y1 - y0)
    c0 = (x0, y0 + math.copysign(k * L, y1 - y0)); c1 = (x1, y1 - math.copysign(k * L, y1 - y0))
    t = np.linspace(0, 1, n)
    return [((1-s)**3*x0 + 3*(1-s)**2*s*c0[0] + 3*(1-s)*s*s*c1[0] + s**3*x1,
             (1-s)**3*y0 + 3*(1-s)**2*s*c0[1] + 3*(1-s)*s*s*c1[1] + s**3*y1) for s in t]

def offs(line, d):
    """Offset a centreline by d metres, +d = east whichever way the line is drawn. Keeps the input direction."""
    c = list(line.coords)
    south = c[-1][1] < c[0][1]
    g = line.offset_curve(d if south else -d, quad_segs=8, join_style='round')   # shapely: + is left of travel
    return list(g.coords)

def length(c):
    return sum(math.dist(c[i], c[i+1]) for i in range(len(c) - 1))

def cut_at_N(c, N, keep='north'):
    """Split a N->S polyline at northing N; keep the part north or south of it."""
    out = []
    for i in range(len(c) - 1):
        a, b = c[i], c[i+1]
        if keep == 'north':
            out.append(a)
            if (a[1] - N) * (b[1] - N) <= 0 and a[1] != b[1]:
                f = (N - a[1]) / (b[1] - a[1]); out.append((a[0] + f*(b[0]-a[0]), N)); return out
        else:
            if (a[1] - N) * (b[1] - N) <= 0 and a[1] != b[1]:
                f = (N - a[1]) / (b[1] - a[1]); out = [(a[0] + f*(b[0]-a[0]), N)]
            elif out: out.append(a)
    if keep == 'north': out.append(c[-1])
    else: out.append(c[-1])
    return out

def x_at_N(c, N):
    for i in range(len(c) - 1):
        a, b = c[i], c[i+1]
        if (a[1] - N) * (b[1] - N) <= 0 and a[1] != b[1]:
            return a[0] + (N - a[1]) / (b[1] - a[1]) * (b[0] - a[0])
    raise ValueError(N)

# ---------------------------------------------------------------- APEx platform field (level 0)
# 16 tracks over 152 m in 8 units of 19 m: track, 10 m island, track. Numbered 1 at the main building (east) to 16 (west),
# so CVG Express 15-16 sit on the west side and its pair runs to Kentucky without crossing the Cardinal.
tx = []
for i in range(16):                  # i = 0 west ... 15 east
    u = i // 2
    tx.append(FW + 19 * u + (2.25 if i % 2 == 0 else 16.75))
for u in range(8):
    x0 = FW + 19 * u
    addpoly('apex_plat', [(x0 + 4.5, FN0), (x0 + 14.5, FN0), (x0 + 14.5, FN1), (x0 + 4.5, FN1), (x0 + 4.5, FN0)],
            name=f'APEx platform, tracks {16 - 2*u} / {15 - 2*u}', level='0', rail=APEX_RAIL, length_m=round(FN1 - FN0, 1))
for i, x in enumerate(tx):
    add('apex', [(x, FN1), (x, FN0)], name=f'APEx track {16 - i}', level='0', rail=APEX_RAIL, kind='platform')

TB = json.load(open((_ws.DATA + 'cut/trimet_bridges.json')))
DECK = lambda N: 151.8 + (N - 4330700) / 4840 * 8.2       # map 3 deck: 151.8 m at the Embankment to 160 m at Camp Washington (10d.4)
def offl(line, d):
    """Offset to the left of travel by d (shapely convention), keeps direction."""
    return list(line.offset_curve(d, quad_segs=8, join_style='round').coords)
def pt_at(line, s):
    p = line.interpolate(s); return (p.x, p.y)
def s_at_N(line, N):
    c = list(line.coords); acc = 0
    for i in range(len(c) - 1):
        a, b = c[i], c[i+1]
        if (a[1] - N) * (b[1] - N) <= 0 and a[1] != b[1]:
            return acc + math.dist(a, (a[0] + (N - a[1]) / (b[1] - a[1]) * (b[0] - a[0]), N))
        acc += math.dist(a, b)
    return None
def s_of(line, xy):
    return line.project(__import__('shapely.geometry', fromlist=['Point']).Point(xy))

# ---------------------------------------------------------------- straight trunk, Camp Washington to the north throat
vc = APX['Vandalia-Cincinnati|99887']['coords']
north_curve = [tuple(p) for p in vc if p[1] > 4334233][::-1]                 # NW curve toward Northside, north -> south
CW = (712750.0, 4334233.0)                                                   # Camp Washington: where the KMZ trunk bows east
straight = [(CW[0] + (FC - CW[0]) * f, CW[1] + (NT - CW[1]) * f) for f in np.linspace(0, 1, 19)]
cn_pts = north_curve + straight
CN = LineString(cn_pts)
A_OFF = [-11.25, -6.75, -2.25, 2.25, 6.75, 11.25]
for j, d in enumerate(A_OFF):
    add('apex', offs(CN, d), name=f'APEx north approach {j+1} of 6', level='0', rail=APEX_RAIL, kind='approach',
        note='3 in + 3 out; straight from Camp Washington (N 4,334,233) to the throat (N 4,332,400)')
for i, x in enumerate(tx):
    j = min(5, int(i * 6 / 16))
    add('apex', bez((x, FN1), (FC + A_OFF[j], NT)), name=f'APEx north throat, track {16 - i}', level='0', rail=APEX_RAIL, kind='throat')

# freight passing track along the west side of the field, as in the 1955 layout
XP = FW - 5.0
pas = bez((FC + A_OFF[0], NT), (XP, 4332190), n=20) + [(XP, 4331600)] + bez((XP, 4331600), (FC + 2.25 - 4.5, ST), n=20)[1:]
add('passing', pas, name='Freight passing track', level='0', rail=APEX_RAIL,
    note='bypasses the platforms throat to throat on the west side, as the 1955 track did; joins the westmost APEx main north and the first APEx main south')

# lower-level pairs on the trunk flanks
L_OFF_N = {'W': [-22.5, -18.0], 'E': [18.0, 22.5]}
NP = 4332630.0
BOXN = FN1
bx = [712700 + 20 * (i // 2) + (2.25 if i % 2 == 0 else 17.75) for i in range(8)]
LET = 'ABCDEFGH'
for side, ds in L_OFF_N.items():
    for k, d in enumerate(ds):
        surf = cut_at_N(offs(CN, d), NP, 'north')
        add('lower', surf, name=f'Lower-level north pair {side}, track {k+1}', level='0', state='surface', rail=APEX_RAIL)
        p = surf[-1]
        base = 0 if side == 'W' else 4
        for m in (0, 1):
            t_ = base + 2 * k + m
            add('lower', bez(p, (bx[t_], BOXN), n=30), name=f'Lower-level north ramp and ladder to {LET[t_]}', level='0 to -2',
                state='ramp', z0=APEX_RAIL, z1=LOWER_RAIL, note='ramp 346 m at 3.5%, then 150 m of ladder at -2')
        addpt('marker', p, kind='portal', name=f'North portal {side}{k+1}', label=('N portals' if (side == 'W' and k == 0) else ''))

# ---------------------------------------------------------------- lower platforms (-2)
AD_S, EH_S = BOXN - 200.0, BOXN - 305.0
for u in range(4):
    x0 = 712700 + 20 * u; s = AD_S if u < 2 else EH_S
    addpoly('lower_plat', [(x0 + 4.5, s), (x0 + 15.5, s), (x0 + 15.5, BOXN), (x0 + 4.5, BOXN), (x0 + 4.5, s)],
            name=f'Lower platform {LET[2*u]} / {LET[2*u+1]}', level='-2', rail=LOWER_RAIL, length_m=round(BOXN - s, 1), label=f'{LET[2*u]}{LET[2*u+1]}')
for i, x in enumerate(bx):
    add('lower', [(x, BOXN), (x, AD_S if i < 4 else EH_S)], name=f'Lower track {LET[i]}', level='-2', state='under', rail=LOWER_RAIL, kind='platform')

# ---------------------------------------------------------------- south approach: CVG pair (west, onto the TRIMET CS viaduct) + APEx 2+2
lx = APX['Cincinnati-Lexington 1|2189']['coords']
CSL = LineString([(FC, ST), (712778, 4331330)] + [tuple(p) for p in lx if 4330690 <= p[1] < 4331300])
S_OFF = [-11.25, -6.75, -2.25, 2.25, 6.75, 11.25]
S_NAME = ['CVG Express', 'CVG Express', 'APEx (Kentucky)', 'APEx (Kentucky)', 'APEx (Kentucky, Cardinal)', 'APEx (Kentucky, Cardinal)']
TCS = LineString([tuple(p[:2]) for p in TB['cs']])                          # TRIMET CS viaduct and bridge (Lebanon-Walton 3D)
for j, d in enumerate(S_OFF):
    c = offs(CSL, d)
    if j < 2:   # CVG pair leaves the APEx approach at N 4,331,200 onto the TRIMET CS viaduct
        top = cut_at_N(c, 4331200, 'north')
        tc = offs(TCS, d + 9.0)
        c = top + bez(top[-1], tc[0], n=10)[1:] + tc[1:]
    add('apex', c, name=f'South approach {j+1} of 6: {S_NAME[j]}', level='0', rail=APEX_RAIL, kind='approach')
for i, x in enumerate(tx):
    num = 16 - i
    j = 0 if num == 16 else 1 if num == 15 else 2 + min(3, int((i - 2) * 4 / 14))
    add('apex', bez((x, FN0), (FC + S_OFF[j], ST)), name=f'APEx south throat, track {num}', level='0', rail=APEX_RAIL, kind='throat')
bt = APX['Cincinnati-Batavia 1|7996']['coords']
car = LineString([tuple(p) for p in bt if p[1] < 4331060 and p[0] < 713800])
for d in (-2.25, 2.25):
    add('apex', offs(car, d), name='Cardinal branch (APEx, east along the river)', level='0', rail=APEX_RAIL, kind='branch')
addpt('marker', (712700, 4330700), kind='flag', name='APEx river crossing', label='APEx bridge: position open',
      note='the KMZ line crosses the CS bridge line mid-river; it has to stay east of the CS bridge or share a rebuilt one')

# ---------------------------------------------------------------- CS pair: A-D, west of the APEx throat, onto the TRIMET CS viaduct and bridge
LAD = 120.0
CS0 = (712712.0, AD_S - LAD)
MERGE_CS = (712631.0, 4330830.0)                                            # joins the TRIMET CS viaduct line
BANK_CS = (712595.0, 4330684.0)                                             # north bank edge (TRIMET)
BR_CS = TB['cs'][-1]
cs_ctrl = [CS0, (712690, 4331740), (712673, 4331660), (712663, 4331520), (712656, 4331300), (712650, 4331100), (712641, 4330960), MERGE_CS]
cs_line = LineString(cs_ctrl + [tuple(p[:2]) for p in TB['cs'] if p[1] < MERGE_CS[1] and p[1] >= BANK_CS[1] - 1])
CS_RAIL = 164.0                                                             # TRIMET: 164.0 m from the north bank across the river
Lcs = cs_line.length
g_cs = (CS_RAIL - LOWER_RAIL) / Lcs
z_cs = lambda s: LOWER_RAIL + g_cs * s
for d, nm in ((-2.25, 'west'), (2.25, 'east')):
    add('lower', offs(cs_line, d), name=f'CS pair ({nm} track): A-D to the Cincinnati Southern bridge', level='-2 to bridge', state='climb',
        z0=LOWER_RAIL, z1=CS_RAIL, length_m=round(Lcs), grade_pct=round(100 * g_cs, 2))
for i in range(4):
    add('lower', bez((bx[i], AD_S), (CS0[0] + (-2.25 if i < 2 else 2.25), CS0[1]), n=16), name=f'Lower track {LET[i]} to CS pair', level='-2', state='under', rail=LOWER_RAIL)
# CS bridge (TRIMET), double track shared by the CS pair and the CVG Express pair
br = [tuple(p[:2]) for p in TB['cs'] if p[1] <= BANK_CS[1] + 1]
add('bridge', br, name='Cincinnati Southern bridge (1922, double track)', rail_m='164.0-164.7 (TRIMET)', clearance_ft=78.9,
    note='TRIMET_Lines.kmz 3D alignment; Waterway Guide: fixed, 78.9 ft vertical clearance, mile 472.3')
s_g = s_at_N(cs_line, 4331557); s_8 = s_at_N(cs_line, 4331225); s_6 = s_at_N(cs_line, 4330846)
hump8 = max(0.0, z_cs(s_8) + 7.6 - DECK(4331225))
for s, lab, anchor in ((0, f'CS climbs from {LOWER_RAIL} m', 'left'), (s_g, f'Gest: CS {z_cs(s_g):.1f} m, under', 'left'),
                       (s_8, f'W 8th: CS {z_cs(s_8):.1f} m, street hump {hump8:.1f} m', 'left'),
                       (s_6, f'W 6th: CS {z_cs(s_6):.1f} m, over (needs {DECK(4330846)+6.5:.1f})', 'left'),
                       (Lcs, f'CS bridge, {CS_RAIL:.1f} m (TRIMET)', 'left')):
    addpt('marker', pt_at(cs_line, s), kind='flag' if 'hump' in lab and hump8 > 0 else 'level', name='CS pair: ' + lab, label=lab, rail=round(z_cs(s), 1), anchor=anchor)

# ---------------------------------------------------------------- C&O pair: E-H, under the APEx throat, under W 6th, up onto the TRIMET C&O viaduct
CO0 = (712770.0, EH_S - LAD)
TCO = [tuple(p) for p in TB['co']]
MERGE_I = min(range(len(TCO)), key=lambda i: math.dist(TCO[i][:2], (713433, 4330462)))
co_ctrl = [CO0, (712798, 4331600), (712826, 4331460), (712842, 4331300), (712852, 4331100), (712868, 4330950), (712895, 4330846),
           (712950, 4330775), (713040, 4330705), (713160, 4330640), (713300, 4330565)]
co_line = LineString(co_ctrl + [TCO[i][:2] for i in range(MERGE_I, len(TCO)) if TCO[i][1] >= 4329960])
CO_MERGE_Z = TCO[MERGE_I][2]
s_m = co_line.project(__import__('shapely.geometry', fromlist=['Point']).Point(TCO[MERGE_I][:2]))
s_co6 = s_at_N(co_line, 4330846)
Z6 = DECK(4330846) - 7.6                                                    # under W 6th
g1 = (Z6 - LOWER_RAIL) / s_co6
g2 = (CO_MERGE_Z - Z6) / (s_m - s_co6)
for d, nm in ((2.25, 'west'), (-2.25, 'east')):
    add('lower', offs(co_line, d), name=f'C&O pair ({nm} track): E-H to the C&O viaduct and bridge', level='-2 to viaduct', state='climb',
        z0=LOWER_RAIL, z1=163.1, note=f'{100*g1:.1f}% to pass under W 6th at {Z6:.1f} m, then {100*g2:.1f}% to the TRIMET C&O viaduct at {CO_MERGE_Z:.1f} m')
for i in range(4, 8):
    add('lower', bez((bx[i], EH_S), (CO0[0] + (-2.25 if i < 6 else 2.25), CO0[1]), n=16), name=f'Lower track {LET[i]} to C&O pair', level='-2', state='under', rail=LOWER_RAIL)
brc = [p[:2] for p in TCO if p[1] <= 4329962]
add('bridge', brc, name='C&O bridge (1929)', rail_m='163.1-165.3 (TRIMET)', note='TRIMET_Lines.kmz 3D alignment')
addpt('marker', pt_at(co_line, s_co6), kind='level', name='C&O pair under W 6th', label=f'W 6th: C&O {Z6:.1f} m, under', rail=round(Z6, 1))
addpt('marker', TCO[MERGE_I][:2], kind='level', name='C&O pair joins the TRIMET C&O viaduct', label=f'joins C&O viaduct, {CO_MERGE_Z:.1f} m', rail=CO_MERGE_Z)
addpt('marker', brc[0], kind='level', name='C&O bridge', label='C&O bridge, 163.1 m (TRIMET)', rail=163.1)

# ---------------------------------------------------------------- labels
addpt('label', (713090, 4332230), text='APEx 1-16  ·  level 0, 144 m', kind='big')
addpt('label', (713090, 4332165), text='Lower A-H  ·  -2, 131.9 m', kind='lower')
addpt('label', (712900, 4333300), text='Straight trunk: 2 lower | 6 APEx | 2 lower', kind='small')
addpt('label', (712560, 4331420), text='CS pair', kind='lower')
addpt('label', (712925, 4331330), text='C&O pair', kind='lower')
addpt('label', (712610, 4331990), text='Freight passing track', kind='small')

north_tracks, south_tracks = 6 + 4, 4 + 2 + 4
summary = dict(option='B', apex_rail=APEX_RAIL, lower_rail=LOWER_RAIL, north_tracks=north_tracks, south_tracks=south_tracks,
               north_portal_N=NP, cs_len_m=round(Lcs), cs_grade_pct=round(100 * g_cs, 2), cs_rail_8th=round(z_cs(s_8), 1), hump8=round(hump8, 1),
               cs_rail_6th=round(z_cs(s_6), 1), need_6th=round(DECK(4330846) + 6.5, 1), cs_rail_gest=round(z_cs(s_g), 1),
               co_g1=round(100 * g1, 2), co_g2=round(100 * g2, 2), co_z6=round(Z6, 1), co_merge_z=CO_MERGE_Z, co_len_m=round(co_line.length),
               trunk_straight_m=round(math.dist(CW, (FC, NT))))
json.dump(dict(crs='EPSG:26916', summary=summary, features=F), open(OUT, 'w'))
print(json.dumps(summary, indent=1)); print('features', len(F))
