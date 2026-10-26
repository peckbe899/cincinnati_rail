"""Fountain Square complex as built today (2026-10-05): one model of every floor, stair, escalator, elevator, fare line and
entrance, for the level plans (fs_levels4.py), the 3D view (fs_3d.py) and the stage drawing.
History as fs_stages4.py (version 4, piecemeal): 1905-07 Lines 1 and 2, 1913 Line 7, 1927 square passage, 1931 store link,
1936 Vine mezzanine, 1958 Sixth Street link, 1985 TRI A/D, after 1985 TRI B, 1999 Pan Am Tower; 'today' = later retrofits
(mostly elevators). Frame as fs_geom.py: metres, u east, v north, turned 11 degrees from true north.
Entrances cut from 31 to 20 (Ben, 2026-10-05: "I'm not sure it needs 31 entrances/exits").
Platforms as locked 2026-10-05: Metro 500 ft (152.4 m), TRI 670 ft (204.2 m). Metro trimmed 7.6 m at the end with nothing
tied to it (Line 1 east, Line 7 west, Line 2 south); TRI lengthened 2.1 m at each end.
Platforms placed from Ben's KMZ files (2026-10-05): FS Layout.kmz for Lines 1, 2 and 7 (each on its street's centre line,
as cut-and-cover), New RER A-D Platform.kmz (the street-aligned westbound island; the eastbound island 27 m south, twin
caverns as before) and New RER B Platform.kmz (under Walnut, just north of the A/D trunk to 7th). Turned into the frame by
fs_kmz_layout.py. Halls, flights, elevators, fare lines and entrances refitted to match (previous model fs_model_v4.py).
A/D track use (proposal): A on the outer tracks of each cavern, D on the inner ones; eastbound in the south cavern."""
import numpy as np
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union

# floor depths below the street, m (drawing values; Lines 1 and 7 and the passages at -1, Line 2 at -2, crossunders between)
Z = {0: 0.0, -1: 5.36, -1.5: 9.40, -2: 12.06, -3: 28.0, -4: 42.0}
STAIR_K = 0.67                                   # rise / run of a fixed stair
ESC_K = np.tan(np.radians(30))                   # escalators at 30 degrees


def R(u0, u1, v0, v1):
    return box(u0, v0, u1, v1)


def C(pts, w):
    return LineString(pts).buffer(w / 2, cap_style='flat', join_style='mitre', mitre_limit=3)


# ---- lines (platform level, axis, centre, extent) ----
LINES = {
    '1': dict(level=-1, axis='u', c=-57.5, a=-7.8, b=144.6, kind='side'),
    '7': dict(level=-1, axis='u', c=84.25, a=-129.6, b=22.8, kind='side'),
    '2': dict(level=-2, axis='v', c=-54.5, a=-108.9, b=43.5, kind='side'),
}
B2, EDGE = 9.45, 4.0
AD_ISL = {'south': (-17.9, -7.9), 'north': (9.1, 19.1)}           # A/D islands (v), u -185.1 to 19.1 (204.2 m)
AD_CAV = {'south': (-22.4, -3.4), 'north': (4.6, 23.6)}
AD_U = (-185.1, 19.1)
B_ISL = (81.0, 93.0); B_CAV = (76.5, 97.5); B_V = (22.7, 226.9)

PARTS = []      # dict(name, level, kind, era, geom, op): kind plat / hall / pass / mezz / court / xunder / island / lobby
FLIGHTS = []    # dict(kind stair/esc, top, bot, geom, d (down-slope unit vector), era, ent, units)
LIFTS = []      # dict(xy, levels [top..bottom], era)
GATES = []      # dict(geom LineString, level): TRI fare lines
TRACKS = []     # dict(line, level, back, front, label)
ENT = []        # dict(n, xy, kind, name, era, level it lands on)


def part(name, level, kind, era, geom, op='metro'):
    PARTS.append(dict(name=name, level=level, kind=kind, era=era, geom=geom, op=op))


def flight(kind, top, bot, start, d, w, era, run=None, ent=None, units=1, extra=0.0):
    d = np.asarray(d, float); d /= np.hypot(*d); n = np.array([-d[1], d[0]])
    rise = Z[bot] - Z[top]
    if run is None:
        run = rise / (STAIR_K if kind == 'stair' else ESC_K) + extra
    s = np.asarray(start, float); e = s + d * run
    g = Polygon([s - n * w / 2, e - n * w / 2, e + n * w / 2, s + n * w / 2])
    FLIGHTS.append(dict(kind=kind, top=top, bot=bot, geom=g, d=tuple(d), era=era, ent=ent, units=units, start=tuple(s), end=tuple(e), w=w))
    return g


def lift(xy, levels, era='today'):
    LIFTS.append(dict(xy=tuple(xy), levels=list(levels), era=era))


def gate(pts, level):
    GATES.append(dict(geom=LineString(pts), level=level))


def ent(n, xy, kind, name, era, level):
    ENT.append(dict(n=n, xy=tuple(xy), kind=kind, name=name, era=era, level=level))


# =================== level -1 (5.4 m) ===================
L1, L7 = LINES['1'], LINES['7']
part('Line 1 westbound platform', -1, 'plat', '1905', R(-7.8, 144.6, -53.5, -48.05)); PARTS[-1]['line'] = '1'
part('Line 1 eastbound platform', -1, 'plat', '1905', R(-7.8, 144.6, -66.95, -61.5)); PARTS[-1]['line'] = '1'
part('Line 7 westbound platform', -1, 'plat', '1913', R(-129.6, 22.8, 88.25, 93.7)); PARTS[-1]['line'] = '7'
part('Line 7 eastbound platform', -1, 'plat', '1913', R(-129.6, 22.8, 74.8, 80.25)); PARTS[-1]['line'] = '7'
part('Line 1 ticket hall', -1, 'hall', '1905', R(12.0, 72.0, -86.0, -67.0))
part('Line 2 south hall', -1, 'mezz', '1907', R(-64.5, -44.5, -121.2, -97.2))
part('1907 link', -1, 'pass', '1907', C([(-48.0, -87.0), (-30.0, -87.0), (-26.0, -83.5), (12.0, -83.5)], 5.0))
part('1907 link stair head', -1, 'pass', '1907', R(-48.0, -44.5, -93.0, -84.5))
part('1907 stair landing', -1, 'pass', '1907', R(-45.05, -38.0, -47.725, -37.75))
part('1927 passage', -1, 'pass', '1927', C([(-7.8, -50.775), (-9.0, -50.775), (-14.0, -45.0), (-38.0, -45.0)], 5.45))
part('1931 store link', -1, 'pass', '1931', C([(-8.0, -85.5), (-8.0, -104.0)], 3.5))
part('Store basement', -1, 'lobby', '1931', R(-14.0, -2.0, -112.0, -104.0))
part('Vine mezzanine', -1, 'mezz', '1936', R(-63.95, -45.05, -47.725, 22.6))
part('Sixth Street link', -1, 'pass', '1958', C([(-45.5, 16.0), (-37.0, 16.0), (-31.0, 24.0), (-31.0, 61.0), (-26.0, 68.0), (-26.0, 77.0)], 5.0))
part('1958 building basement', -1, 'lobby', '1958', R(-44.0, -33.5, 50.0, 61.801))
part('Sunken court', -1, 'court', '1985', R(-25.0, 10.0, -36.0, -12.0))
part('Court link', -1, 'pass', '1985', R(-21.0, -15.0, -42.275, -36.0))
part('5th & Vine SW vestibule', -1, 'lobby', 'today', R(-84.0, -61.75, -82.0, -74.5))
part('5th & Walnut SW vestibule', -1, 'lobby', 'today', R(60.0, 74.0, -96.0, -86.0))
part('6th & Vine NE vestibule', -1, 'lobby', 'today', R(-40.0, -32.0, 93.7, 97.0))
part('Pan Am 6th St vestibule', -1, 'lobby', '1999', R(-123.4, -117.4, 72.0, 74.8))
# crossunders below the tracks (-1.5)
part('Line 1 crossunder', -1.5, 'xunder', '1905', R(34.0, 42.0, -66.5, -49.0))
part('Line 1 east crossunder', -1.5, 'xunder', '1905', R(127.0, 131.0, -66.5, -49.0))
part('Line 7 crossunder, Vine E', -1.5, 'xunder', '1913', R(-50.5, -45.05, 70.0, 93.5))
part('Line 7 crossunder, Vine W', -1.5, 'xunder', '1913', R(-63.95, -58.5, 70.0, 93.5))

# =================== level -2 (12 m) ===================
part('Line 2 southbound platform', -2, 'plat', '1907', R(-63.95, -58.5, -108.9, 43.5)); PARTS[-1]['line'] = '2'
part('Line 2 northbound platform', -2, 'plat', '1907', R(-50.5, -45.05, -108.9, 43.5)); PARTS[-1]['line'] = '2'
part('Vine west passage', -2, 'pass', '1913', R(-63.95, -58.5, 43.5, 70.0))
part('Vine east passage', -2, 'pass', '1913', R(-50.5, -45.05, 43.5, 70.0))
part('TRI hall', -2, 'hall', '1985', R(-44.5, 33.0, -47.0, 0.0), op='tri')
part('TRI hall north arm', -2, 'pass', '1985', unary_union([R(-32.0, -22.0, 0.0, 37.0), R(-32.0, -15.0, 8.0, 20.0)]), op='tri')
part('West hall', -2, 'hall', '1985', R(-110.0, -64.5, -18.0, 40.0), op='tri')
part('East hall', -2, 'hall', '1985', R(14.0, 78.0, -20.0, 38.0), op='tri')
part('Walnut passage', -2, 'pass', 'B', C([(82.5, -48.0), (82.5, 16.0)], 9.0), op='tri')
part('B south end hall', -2, 'hall', 'B', R(78.0, 96.5, 16.0, 30.0), op='tri')
part('Walnut hall', -2, 'hall', 'B', R(60.0, 96.5, -67.0, -48.0), op='tri')
part('B north hall', -2, 'hall', 'B', R(77.5, 96.5, 76.5, 92.0), op='tri')
part('Line 7 east hall', -2, 'hall', 'B', R(0.0, 29.0, 74.8, 93.7))
part('Sixth Street passage', -2, 'pass', 'B', R(29.0, 77.5, 80.0, 88.5))
part('5th & Walnut NE lobby', -2, 'lobby', 'B', R(96.5, 112.0, -62.0, -20.0), op='tri')
part('6th & Walnut NE lobby', -2, 'lobby', 'B', R(96.5, 112.0, 84.0, 122.0), op='tri')
part('B north end hall', -2, 'hall', 'B', R(77.5, 112.0, 158.0, 190.0), op='tri')

# =================== level -3 (28 m) and -4 (42 m) ===================
part('A/D eastbound island', -3, 'island', '1985', R(AD_U[0], AD_U[1], *AD_ISL['south']), op='tri')
part('A/D westbound island', -3, 'island', '1985', R(AD_U[0], AD_U[1], *AD_ISL['north']), op='tri')
part('B island', -4, 'island', 'B', R(B_ISL[0], B_ISL[1], B_V[0], B_V[1]), op='tri')
CAVERNS = [dict(level=-3, geom=R(AD_U[0], AD_U[1], *AD_CAV['south'])), dict(level=-3, geom=R(AD_U[0], AD_U[1], *AD_CAV['north'])),
           dict(level=-4, geom=R(B_CAV[0], B_CAV[1], B_V[0], B_V[1]))]

# =================== tracks (back, front: front = the way trains run) ===================
TRACKS += [
    dict(line='1', level=-1, back=(-7.8, -59.5), front=(144.6, -59.5), dir='EB'), dict(line='1', level=-1, back=(144.6, -55.5), front=(-7.8, -55.5), dir='WB'),
    dict(line='7', level=-1, back=(-129.6, 82.25), front=(22.8, 82.25), dir='EB'), dict(line='7', level=-1, back=(22.8, 86.25), front=(-129.6, 86.25), dir='WB'),
    dict(line='2', level=-2, back=(-52.5, -108.9), front=(-52.5, 43.5), dir='NB'), dict(line='2', level=-2, back=(-56.5, 43.5), front=(-56.5, -108.9), dir='SB'),
    dict(line='A', level=-3, back=(AD_U[0], -20.15), front=(AD_U[1], -20.15), dir='EB'), dict(line='D', level=-3, back=(AD_U[0], -5.65), front=(AD_U[1], -5.65), dir='EB'),
    dict(line='D', level=-3, back=(AD_U[1], 6.85), front=(AD_U[0], 6.85), dir='WB'), dict(line='A', level=-3, back=(AD_U[1], 21.35), front=(AD_U[0], 21.35), dir='WB'),
    dict(line='B', level=-4, back=(95.25, B_V[0]), front=(95.25, B_V[1]), dir='NB'), dict(line='B', level=-4, back=(78.75, B_V[1]), front=(78.75, B_V[0]), dir='SB'),
]

E, W, N, S = (1, 0), (-1, 0), (0, 1), (0, -1)
# =================== flights (start = top edge centre, d = downhill) ===================
# Line 2 south hall (1907) to both platforms
flight('stair', -1, -2, (-62.85, -109.2), N, 2.2, '1907'); flight('stair', -1, -2, (-46.15, -109.2), N, 2.2, '1907')
# 1907 link: up from Line 2 northbound
flight('stair', -1, -2, (-46.15, -87.5), S, 2.2, '1907')
# Vine mezzanine (1936): stairs, and escalators added later, both platforms
for u in (-62.85, -46.15):
    flight('stair', -1, -2, (u, -10.0), N, 2.2, '1936'); flight('stair', -1, -2, (u, 22.0), S, 2.2, '1936')
    flight('esc', -1, -2, (u, -45.0), N, 1.6, 'today', extra=1.5)
# Line 1 crossunders (1905)
for u0, uc in ((48.0, 42.0), (137.0, 131.0)):
    flight('stair', -1, -1.5, (u0, -64.2), W, 2.2, '1905'); flight('stair', -1, -1.5, (u0, -50.75), W, 2.2, '1905')
# Line 7 crossunders (1913): down from both platforms, then on down to the Vine passages
for uc, top in ((-47.775, -41.0), (-61.225, -68.0)):
    dd = W if top > uc else E
    flight('stair', -1, -1.5, (top, 76.2), dd, 2.2, '1913'); flight('stair', -1, -1.5, (top, 92.6), dd, 2.2, '1913')
    flight('stair', -1.5, -2, (uc, 74.0), S, 3.5, '1913')
# Line 1 to B south hall; Line 7 to its east hall (after 1985)
flight('stair', -1, -2, (72.0, -65.5), W, 2.2, 'B'); flight('stair', -1, -2, (72.0, -49.8), W, 2.2, 'B')
flight('stair', -1, -2, (0.0, 76.2), E, 2.2, 'B'); flight('stair', -1, -2, (0.0, 92.6), E, 2.2, 'B')
# 1958 corridor down to the TRI hall's north arm (1985)
flight('stair', -1, -2, (-30.0, 47.0), S, 2.4, '1985')
# sunken court (1985): broad stair and escalators down from the square, escalators and a stair on down to the TRI hall
flight('stair', 0, -1, (-25.0, -27.0), E, 14.0, '1985', ent=3)
flight('esc', 0, -1, (-1.0, -13.5), W, 2.8, '1985', ent=3, units=2, extra=1.5)
flight('esc', -1, -2, (4.5, -17.0), S, 2.8, '1985', units=2, extra=1.5)
flight('stair', -1, -2, (-1.0, -17.0), S, 2.6, '1985')
# TRI hall (-2) down to the A/D islands; west hall and east hall likewise (1985)
flight('esc', -2, -3, (-17.0, -12.9), W, 4.6, '1985', units=3, extra=2.0)           # TRI hall to the eastbound island, landing under Line 2
flight('esc', -2, -3, (-24.0, 13.5), E, 4.6, '1985', units=3, extra=2.0)            # north arm to the westbound island
for v in (12.5, -14.5):
    flight('esc', -2, -3, (-84.0, v), W, 4.6, '1985', units=3, extra=2.0)
    flight('esc', -2, -3, (45.0, v), W, 4.6, '1985', units=3, extra=2.0)
# B halls down to the B island (after 1985): long escalators, three abreast; the south bank starts north of the A/D bores
flight('esc', -2, -4, (84.0, 8.0), N, 5.0, 'B', units=3, extra=2.0)
flight('esc', -2, -4, (88.5, 84.0), N, 6.6, 'B', units=3, extra=2.0)
flight('esc', -2, -4, (85.0, 166.0), N, 4.6, 'B', units=2, extra=2.0)

# =================== entrances (20) and their flights ===================
ent(1, (24, -44), 'pavilion', 'Fountain Square pavilion, Walnut end', '1905', -1)
flight('stair', 0, -1, (28.0, -50.75), W, 2.4, '1905', ent=1)
ent(2, (-30, -33), 'pavilion', 'Fountain Square pavilion, Vine end', '1907', -1)
flight('stair', 0, -1, (-30.0, -40.0), W, 4.5, '1907', ent=2)
ent(3, (-7.5, -24), 'court', 'Sunken court', '1985', -1)
ent(4, (-76, -36), 'tower', 'Pan Am Tower, 5th & Vine', '1999', -2)
flight('esc', 0, -2, (-74.0, -28.0), N, 4.6, '1999', ent=4, units=2, extra=1.5)
ent(5, (-82, -96), 'building', '5th & Vine, SW corner', 'today', -1)
flight('stair', 0, -1, (-82.0, -90.0), N, 3.0, 'today', ent=5); flight('stair', -1, -2, (-62.85, -80.0), N, 2.2, 'today')
ent(6, (-62.5, -134.2), 'sidewalk', 'Vine, 4th to 5th, west side', '1907', -1)
flight('stair', 0, -1, (-62.5, -129.2), N, 2.5, '1907', ent=6)
ent(7, (-46.5, -134.2), 'sidewalk', 'Vine, 4th to 5th, east side', '1907', -1)
flight('stair', 0, -1, (-46.5, -129.2), N, 2.5, '1907', ent=7)
ent(8, (-8, -125), 'building', '5th St, south side (store)', '1931', -1)
flight('stair', 0, -1, (-8.0, -120.0), N, 3.0, '1931', ent=8)
ent(9, (66, -110), 'building', '5th & Walnut, SW corner', 'today', -1)
flight('stair', 0, -1, (66.0, -104.0), N, 3.0, 'today', ent=9)
ent(10, (155, -72), 'pavilion', 'Government Square pavilion', '1905', -1)
flight('stair', 0, -1, (150.0, -64.2), W, 2.2, '1905', ent=10)
ent(11, (104, -15), 'building', '5th & Walnut, NE corner', 'B', -2)
flight('esc', 0, -2, (104.0, -21.0), S, 4.6, 'B', ent=11, units=2, extra=1.5)
ent(12, (66, 41), 'building', 'Walnut, 5th to 6th, west side', '1985', -2)
flight('esc', 0, -2, (66.0, 35.0), S, 4.6, '1985', ent=12, units=2, extra=1.5)
ent(13, (104, 127), 'building', '6th & Walnut, NE corner', 'B', -2)
flight('esc', 0, -2, (104.0, 121.0), S, 4.6, 'B', ent=13, units=2, extra=1.5)
ent(14, (104, 194), 'building', 'Walnut, 6th to 7th (TRI B north end)', 'B', -2)
flight('esc', 0, -2, (104.0, 189.0), S, 4.6, 'B', ent=14, units=2, extra=1.5)
ent(15, (16, 96.5), 'sidewalk', '6th, Vine to Walnut, north side', '1913', -1)
flight('stair', 0, -1, (14.0, 90.6), E, 2.0, '1913', ent=15)
ent(16, (16, 72), 'sidewalk', '6th, Vine to Walnut, south side', '1913', -1)
flight('stair', 0, -1, (14.0, 77.9), E, 2.0, '1913', ent=16)
ent(17, (-44, 75), 'building', '6th & Vine, SE corner', '1958', -1)
flight('stair', 0, -1, (-41.5, 70.0), S, 3.0, '1958', ent=17); flight('esc', 0, -1, (-37.0, 71.5), S, 2.8, 'today', ent=17, units=2, extra=1.0)
ent(18, (-36, 104), 'building', '6th & Vine, NE corner', 'today', -1)
flight('stair', 0, -1, (-36.0, 105.0), S, 3.0, 'today', ent=18)
ent(19, (-132, 96.5), 'sidewalk', '6th, Race to Vine, north side', '1913', -1)
flight('stair', 0, -1, (-128.0, 90.6), E, 2.0, '1913', ent=19)
ent(20, (-120.4, 58), 'tower', 'Pan Am Tower, 6th St', '1999', -1)
flight('stair', 0, -1, (-120.4, 64.0), N, 3.0, '1999', ent=20)

# =================== elevators ===================
lift((-49.5, -118.7), (0, -1)); lift((-60.0, -106.2), (-1, -2)); lift((-49.0, -106.2), (-1, -2))          # Line 2 south end
lift((-60.6, -20.0), (-1, -2)); lift((-48.4, -20.0), (-1, -2))                                            # Vine mezzanine
lift((36.0, -64.2), (-1, -1.5)); lift((36.0, -50.8), (-1, -1.5))                                          # Line 1 crossunder
lift((-46.5, 79.0), (-1, -1.5)); lift((-46.5, 89.6), (-1, -1.5))                                          # Line 7 crossunder, Vine E
lift((7.0, -14.5), (0, -1, -2), era='1985')                                                               # sunken court
lift((-15.0, -9.5), (-2, -3), era='1985'); lift((-29.0, 17.5), (-2, -3), era='1985')                      # TRI hall, north arm
lift((-88.0, 17.3), (-2, -3), era='1985'); lift((-88.0, -9.6), (-2, -3), era='1985')                      # west hall
lift((16.5, 17.3), (-2, -3), era='1985'); lift((16.5, -9.6), (-2, -3), era='1985')                        # east hall
lift((-68.0, -2.5), (0, -2), era='1999')                                                                  # Pan Am
lift((73.0, 33.0), (0, -2), era='1985')                                                                   # entrance 12
lift((75.5, -64.2), (-1, -2), era='B'); lift((75.5, -50.8), (-1, -2), era='B')                            # Line 1 to B south hall
lift((91.0, 26.0), (-2, -4), era='B'); lift((82.5, 88.0), (-2, -4), era='B'); lift((91.0, 177.0), (-2, -4), era='B')   # to the B island
lift((109.5, -26.0), (0, -2), era='B'); lift((109.5, 116.0), (0, -2), era='B'); lift((109.5, 184.0), (0, -2), era='B')  # entrances 11, 13, 14
lift((12.0, 76.4), (-1, -2), era='B'); lift((12.0, 92.4), (-1, -2), era='B')                             # Line 7 to its east hall
lift((70.0, -92.0), (0, -1)); lift((-36.0, 53.0), (0, -1))                                                # entrances 9 and 17

# =================== TRI fare lines ===================
gate([(-44.5, -24.0), (-44.5, -12.0)], -2)                 # TRI hall door from Line 2 northbound
gate([(-7.0, -33.0), (12.0, -33.0), (12.0, -12.0), (-7.0, -12.0), (-7.0, -33.0)], -2)   # round the foot of the court escalators and lift
gate([(-80.0, -18.0), (-80.0, 40.0)], -2)                   # west hall: Metro side east (Line 2 SB, Vine W, Pan Am), TRI side west
gate([(-32.0, 36.0), (-22.0, 36.0)], -2)                   # north arm, foot of the stair from the 1958 corridor
gate([(60.0, 38.0), (60.0, 8.0), (78.0, 8.0), (78.0, 30.0)], -2)   # east hall: entrance 12's landing outside, the B south end hall inside
gate([(76.0, 80.0), (76.0, 88.5)], -2)                     # Sixth Street passage into the B north hall
gate([(78.0, -67.0), (78.0, -48.0)], -2)                   # Walnut hall: Line 1 stairs and lifts land west of it
gate([(97.0, -62.0), (97.0, -48.0)], -2); gate([(96.5, 84.0), (96.5, 92.0)], -2); gate([(96.5, 158.0), (96.5, 190.0)], -2)


HEADROOM = 2.3 + 1.1                             # clear height over a flight plus the floor slab, m


def well(f):
    """The opening a flight needs in the floor at its top: from its top edge until it has dropped a headroom below that
    floor (the rest of the flight runs on under the floor or out past its edge in its own tunnel)."""
    s0, e0 = np.array(f['start']), np.array(f['end']); d = np.array(f['d']); L = np.hypot(*(e0 - s0))
    rise = Z[f['bot']] - Z[f['top']]
    run = min(L, HEADROOM / (rise / L)) if rise > 0 else L
    n = np.array([-d[1], d[0]]); w = f['w']; e = s0 + d * run
    return Polygon([s0 - n * w / 2, e - n * w / 2, e + n * w / 2, s0 + n * w / 2])


def at(level):
    return [p for p in PARTS if p['level'] == level]


def flights_touching(level):
    return [f for f in FLIGHTS if f['top'] == level or f['bot'] == level]


if __name__ == '__main__':
    print(len(PARTS), 'parts', len(FLIGHTS), 'flights', len(LIFTS), 'elevators', len(GATES), 'fare lines', len(ENT), 'entrances')
    k = {}
    for e in ENT:
        k[e['kind']] = k.get(e['kind'], 0) + 1
    print(k, sum(k.values()))
