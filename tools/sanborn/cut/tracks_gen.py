try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# CUT approach tracks for the Mill Creek Deck page (Option B, 2026-10-10).
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

# ---------------------------------------------------------------- north approach: 6 APEx + 4 lower + 2 TRI B/D (proposed)
vc = APX['Vandalia-Cincinnati|99887']['coords']
cn_pts = ([(FC, NT)] + [tuple(p) for p in vc if 4332500 < p[1] < 4334300])[::-1]   # drawn north -> south
CN = LineString(cn_pts)
A_OFF = [-11.25, -6.75, -2.25, 2.25, 6.75, 11.25]
for j, d in enumerate(A_OFF):
    add('apex', offs(CN, d), name=f'APEx north approach {j+1} of 6', level='0', rail=APEX_RAIL, kind='approach',
        note='3 in + 3 out (directional, like the canon Penn Hudson tunnels)')
# north throat fan 16 -> 6
for i, x in enumerate(tx):
    j = min(5, int(i * 6 / 16))
    add('apex', bez((x, FN1), (FC + A_OFF[j], NT)), name=f'APEx north throat, track {16 - i}', level='0', rail=APEX_RAIL, kind='throat')

# lower-level pairs on the trunk flanks
L_OFF_N = {'W': [-22.5, -18.0], 'E': [18.0, 22.5]}
NP = 4332630.0                         # north portals: 231 m of ramp before the APEx ladder overruns the flanks at ~4,332,372
BOXN = FN1                             # lower platforms start under the north end of the APEx field
bx = []                                # lower box tracks A..H (west -> east), 4 units of 20 m from E 712,700
for i in range(8):
    u = i // 2
    bx.append(712700 + 20 * u + (2.25 if i % 2 == 0 else 17.75))
LET = 'ABCDEFGH'
for side, ds in L_OFF_N.items():
    for k, d in enumerate(ds):
        c = offs(CN, d)
        surf = cut_at_N(c, NP, 'north')
        add('lower', surf, name=f'Lower-level north pair {side}, track {k+1}', level='0', state='surface', rail=APEX_RAIL,
            note='at yard level on the trunk flank, north of the portal')
        p = surf[-1]
        # ramp (346 m, 12.1 m at 3.5%) then 150 m ladder at -2 into two platform tracks
        base = 0 if side == 'W' else 4
        for m in (0, 1):
            t = base + 2 * k + m
            add('lower', bez(p, (bx[t], BOXN), n=30), name=f'Lower-level north ramp and ladder to {LET[t]}', level='0 to -2',
                state='ramp', z0=APEX_RAIL, z1=LOWER_RAIL, note='ramp 346 m at 3.5% (portal to 131.9 m), then 150 m of ladder at -2')
        addpt('marker', p, kind='portal', name=f'North portal {side}{k+1}', label=('N portals, 144 m' if (side == 'W' and k == 0) else ''))

# ---------------------------------------------------------------- lower platforms (-2)
AD_S = BOXN - 200.0                    # A-D: 200 m (TRI 8-car standard), Transvalley
EH_S = BOXN - 305.0                    # E-H: 305 m (1,000 ft), ORR and intercity
for u in range(4):
    x0 = 712700 + 20 * u
    s = AD_S if u < 2 else EH_S
    addpoly('lower_plat', [(x0 + 4.5, s), (x0 + 15.5, s), (x0 + 15.5, BOXN), (x0 + 4.5, BOXN), (x0 + 4.5, s)],
            name=f'Lower platform {LET[2*u]} / {LET[2*u+1]}', level='-2', rail=LOWER_RAIL, length_m=round(BOXN - s, 1),
            label=f'{LET[2*u]}{LET[2*u+1]}')
for i, x in enumerate(bx):
    s = AD_S if i < 4 else EH_S
    add('lower', [(x, BOXN), (x, s)], name=f'Lower track {LET[i]}', level='-2', state='under', rail=LOWER_RAIL, kind='platform')

# ---------------------------------------------------------------- south approach (level 0): CVG pair (west) + APEx 2+2
lx = APX['Cincinnati-Lexington 1|2189']['coords']
cs_pts = [(FC, ST), (712778, 4331330)] + [tuple(p) for p in lx if 4330690 <= p[1] < 4331300]
CSL = LineString(cs_pts)
S_OFF = [-11.25, -6.75, -2.25, 2.25, 6.75, 11.25]
S_NAME = ['CVG Express', 'CVG Express', 'APEx (Kentucky)', 'APEx (Kentucky)', 'APEx (Kentucky, Cardinal)', 'APEx (Kentucky, Cardinal)']
for j, d in enumerate(S_OFF):
    add('apex', offs(CSL, d), name=f'South approach {j+1} of 6: {S_NAME[j]}', level='0', rail=APEX_RAIL, kind='approach')
for i, x in enumerate(tx):
    num = 16 - i
    j = 0 if num == 16 else 1 if num == 15 else 2 + min(3, int((i - 2) * 4 / 14))
    add('apex', bez((x, FN0), (FC + S_OFF[j], ST)), name=f'APEx south throat, track {num}', level='0', rail=APEX_RAIL, kind='throat')
# Cardinal branch (2 tracks) off the east pair, along the KMZ Cardinal line
bt = APX['Cincinnati-Batavia 1|7996']['coords']
car = LineString([tuple(p) for p in bt if p[1] < 4331060 and p[0] < 713800])
for d in (-2.25, 2.25):
    c = offs(car, d)
    add('apex', c, name='Cardinal branch (APEx, east along the river)', level='0', rail=APEX_RAIL, kind='branch')

# ---------------------------------------------------------------- CS pair: A-D south, peels west, climbs to the CS bridge
ABUT_CS = (712585.0, 4330665.0)        # north abutment on Ben's river outline
CS_RAIL = 165.0                        # 162.3-163.7 m low chord + ~1.5-2 m floor (assumed); mid value
LAD = 120.0                            # south ladder at -2: four platform tracks onto one pair
CS0 = (712712.0, AD_S - LAD)
cs_ctrl = [CS0, (712690, 4331740), (712673, 4331660), (712663, 4331520), (712656, 4331300),
           (712650, 4331100), (712640, 4330930), (712618, 4330790), ABUT_CS]
csl = LineString(cs_ctrl)
Lcs = csl.length
g_cs = (CS_RAIL - LOWER_RAIL) / Lcs   # constant grade from the ladder end to the abutment
def z_cs(s): return LOWER_RAIL + g_cs * s
for d, nm in ((-2.25, 'west'), (2.25, 'east')):
    c = list(LineString(offs(csl, d)).coords)
    add('lower', c, name=f'CS pair ({nm} track): A-D to the Cincinnati Southern bridge', level='-2 to bridge', state='climb',
        z0=LOWER_RAIL, z1=CS_RAIL, length_m=round(Lcs), grade_pct=round(100 * g_cs, 2))
# A-D ladder onto the CS pair (A, B west track; C, D east track)
for i in range(4):
    add('lower', bez((bx[i], AD_S), (CS0[0] + (-2.25 if i < 2 else 2.25), CS0[1]), n=16), name=f'Lower track {LET[i]} to CS pair',
        level='-2', state='under', rail=LOWER_RAIL)
# key levels along the CS pair
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
s144 = (APEX_RAIL - LOWER_RAIL) / g_cs
DECK_AT = lambda N: 151.8 + (N - 4330300) / 4840 * 8.2      # map 3 deck, Embankment 151.8 m rising to 160 m (10d.4)
# where the CS rail passes deck level
s_deck = None
for s in np.linspace(0, Lcs, 2000):
    N = pt_at(csl, s)[1]
    if z_cs(s) >= DECK_AT(N) - 0.0:
        s_deck = s; break
marks = [(0, f'CS climbs from {LOWER_RAIL} m'), (s144, 'yard level 144 m'), (s_deck, f'deck level {DECK_AT(pt_at(csl, s_deck)[1]):.1f} m'),
         (Lcs, f'CS bridge, about {CS_RAIL:.0f} m')]
for s, lab in marks:
    addpt('marker', pt_at(csl, s), kind='level', name=f'CS pair: {lab}', label=lab, rail=round(z_cs(s), 1), anchor='left')
s8 = s_at_N(csl, 4331225)
addpt('marker', pt_at(csl, s8), kind='flag', name='CS pair under W 8th St', label=f'8th St: CS rail {z_cs(s8):.1f} m', anchor='left',
      rail=round(z_cs(s8), 1), note='8th St over it needs a local hump of about 3 m, or keeps a viaduct like the real one')
# CS bridge
add('bridge', [ABUT_CS, (712612, 4330358)], name='Cincinnati Southern bridge (1922, double track)', clearance_ft=78.9,
    rail_est_m='164-166', note='Waterway Guide: fixed, 78.9 ft vertical clearance, mile 472.3')

addpt('marker', (712700, 4330700), kind='flag', name='APEx river crossing',
      label='APEx bridge: position open', note='the KMZ line crosses the CS bridge line mid-river; it has to stay east of the CS bridge or share a rebuilt one')

# ---------------------------------------------------------------- C&O pair: E-H south, under the APEx throat, east of it, riverfront
CO0 = (712770.0, EH_S - LAD)
co_ctrl = [CO0, (712798, 4331600), (712826, 4331460), (712838, 4331300),
           (712846, 4331140), (712866, 4330990), (712905, 4330880), (712980, 4330790), (713100, 4330705),
           (713280, 4330620), (713500, 4330535), (713760, 4330470)]
col = LineString(co_ctrl)
CO_CLIMB_N = 4331460                   # clear of the APEx throat footprint from here
s_c0 = s_at_N(col, CO_CLIMB_N)
G_CO = 0.025
s_c144 = s_c0 + (APEX_RAIL - LOWER_RAIL) / G_CO
for d, nm in ((-2.25, 'west'), (2.25, 'east')):
    add('lower', list(LineString(offs(col, d)).coords), name=f'C&O pair ({nm} track): E-H to the C&O viaduct', level='-2 to 0',
        state='climb', z0=LOWER_RAIL, z1=APEX_RAIL, note=f'level at -2 under the APEx throat, then 2.5% to yard level, then along the riverfront')
for i in range(4, 8):
    add('lower', bez((bx[i], EH_S), (CO0[0] + (-2.25 if i < 6 else 2.25), CO0[1]), n=16), name=f'Lower track {LET[i]} to C&O pair',
        level='-2', state='under', rail=LOWER_RAIL)
addpt('marker', pt_at(col, s_c0), kind='level', name='C&O pair starts to climb', label='C&O climbs from 131.9 m', rail=LOWER_RAIL)
addpt('marker', pt_at(col, s_c144), kind='level', name='C&O pair at yard level', label='C&O at 144 m', rail=APEX_RAIL)
addpt('marker', co_ctrl[-1], kind='level', name='C&O pair continues east to the C&O viaduct', label='to C&O viaduct')

# ---------------------------------------------------------------- TRI B/D, proposed east flank
tri_n = offs(CN, 33.25)
tri_n = [p for p in tri_n if p[1] > 4332560]          # already north -> south
tri_s = [(712800, 4332440), (712848, 4332250), (712862, 4332100), (712876, 4331976), (712904, 4331928), (712934, 4331897),
         (712976, 4331876), (713033, 4331862), (713157, 4331848)]
tri = tri_n + tri_s
for d in (-2.25, 2.25):
    add('tri_prop', list(LineString(offs(LineString(tri), d)).coords), name='TRI B/D, proposed east flank',
        note='stays outside the APEx tracks and the lower ramps; joins the canon path at the field NE corner; Union Terminal TRI box at E 713,157')

# ---------------------------------------------------------------- labels
addpt('label', (713090, 4332230), text='APEx 1-16  ·  level 0, 144 m', kind='big')
addpt('label', (713090, 4332165), text='Lower A-H  ·  -2, 131.9 m', kind='lower')
addpt('label', (x_at_N(cn_pts, 4333300) + 60, 4333300), text='12-track trunk: 2 lower | 6 APEx | 2 lower | 2 TRI B/D', kind='small')
addpt('label', (712590, 4331420), text='CS pair', kind='lower')
addpt('label', (712925, 4331330), text='C&O pair', kind='lower')

# ---------------------------------------------------------------- summary
north_tracks = 6 + 4 + 2
south_tracks = 4 + 2 + 4
summary = dict(option='B', apex_rail=APEX_RAIL, lower_rail=LOWER_RAIL, north_tracks=north_tracks, south_tracks=south_tracks,
               north_portal_N=NP, cs_len_m=round(Lcs), cs_grade_pct=round(100 * g_cs, 2), cs_rail_8th=round(z_cs(s8), 1),
               cs_deck_N=round(pt_at(csl, s_deck)[1]), cs_grade_range=[round(100*(r-LOWER_RAIL)/Lcs,2) for r in (164.0,166.0)], cs_start_N=CS0[1], cs_out_of_field_s=round((135.9-LOWER_RAIL)/g_cs), cs_x_at_that=round(pt_at(csl,(135.9-LOWER_RAIL)/g_cs)[0],1), cs_N_at_that=round(pt_at(csl,(135.9-LOWER_RAIL)/g_cs)[1]), co_144_N=round(pt_at(col, s_c144)[1]))
json.dump(dict(crs='EPSG:26916', summary=summary, features=F), open(OUT, 'w'))
print(json.dumps(summary, indent=1))
print('features', len(F))
