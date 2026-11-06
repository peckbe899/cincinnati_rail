"""North trunk v5 (10za.30): every path on the one viaduct from Ludlow to Camp Washington; Camp Washington (B/D) elevated;
B/D dive between Camp Washington and Straight; Indianapolis + D one deck from the lobe; Arlington (B) at band level. Writes nv/v5.json."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, math, numpy as np, rasterio
from shapely.geometry import LineString, Point, shape
SP = _ws.DATA
C = LineString(json.load(open(SP + 'nv/profile.json'))['C'])
DEM = rasterio.open(SP + 'handoff/out/map3_profile_dem_dm.vrt')
def gz(e, n):
    v = list(DEM.sample([(e, n)]))[0][0]; return float('nan') if v < -30000 else v / 10
def deck(n): return 151.8 + (n - 4330700) / 4840 * 8.2
def at(s, o):
    p = C.interpolate(s); q = C.interpolate(s + 3); d = np.array([q.x - p.x, q.y - p.y]); d /= np.linalg.norm(d)
    return p.x + d[1] * o, p.y - d[0] * o
def soff(x, y, s):
    p = C.interpolate(s); q = C.interpolate(s + 3); d = np.array([q.x - p.x, q.y - p.y]); d /= np.linalg.norm(d)
    return (x - p.x) * d[1] - (y - p.y) * d[0]
S_TIP, S_LUD, Z_LUD = 3895.2, 5300.0, 155.5
Z_TIP = deck(C.interpolate(S_TIP).y) + 6.5
G_BAND = (Z_TIP - Z_LUD) / (S_LUD - S_TIP)
def band(s):
    if s <= S_TIP: return deck(C.interpolate(s).y) + 6.5
    return max(Z_LUD, Z_TIP - G_BAND * (s - S_TIP))
out = dict(S_TIP=S_TIP, Z_TIP=Z_TIP, G_BAND=G_BAND)
# ---- canon station points
cw = Point(712401.5, 4334799.9); st = Point(712754.5, 4334139.1)
S_CWC, S_STC = C.project(cw), C.project(st)
print('canon points: Camp Washington s %.0f (off %.1f), Straight s %.0f (off %.1f)' % (S_CWC, soff(cw.x, cw.y, S_CWC), S_STC, soff(st.x, st.y, S_STC)))
S_CW0, S_CW1 = 2964.0, 3168.0; S_ST0, S_ST1 = 2199.0, 2403.0; Z_STR = 151.64
# ---- B/D south: band level through Camp Washington, 3.3% down from the platform's south end, level into Straight
G_DIVE = 0.033
Z_CWS = band(S_CW0)
S_BOT = S_CW0 - (Z_CWS - Z_STR) / G_DIVE
def BDs(s):
    if s >= S_CW0: return band(s)
    return max(Z_STR, Z_CWS - G_DIVE * (S_CW0 - s))
S_SEP = S_CW0 - 6.8 / G_DIVE      # 6.8 m under the band from here south: B/D can go under the APEx tracks, ORR E over B/D
print('Camp Washington elevated: s %.0f-%.0f, %.2f-%.2f m (band); dive 3.3%% from s %.0f (%.2f) to %.2f m at s %.0f, level %.0f m to Straight (s %.0f)' % (
    S_CW0, S_CW1, band(S_CW0), band(S_CW1), S_CW0, Z_CWS, Z_STR, S_BOT, S_BOT - S_ST1, S_ST1))
s_deck = next(s for s in np.arange(S_CW0, 2400, -0.5) if BDs(s) <= deck(C.interpolate(s).y))
s_box = next(s for s in np.arange(S_CW0, 2400, -0.5) if BDs(s) <= deck(C.interpolate(s).y) - 5.2)
s_46 = next(s for s in np.arange(S_CW0, 2400, -0.5) if BDs(s) <= deck(C.interpolate(s).y) - 4.6)
print('  ramp above the deck s %.0f-%.0f (%.0f m), open trough s %.0f-%.0f (%.0f m; 4.6 m cover at s %.0f), box from s %.0f; 6.8 m under the band from s %.0f' % (
    s_deck, S_CW0, S_CW0 - s_deck, s_box, s_deck, s_deck - s_box, s_46, s_box, S_SEP))
out.update(S_CW0=S_CW0, S_CW1=S_CW1, Z_CWS=Z_CWS, S_BOT=S_BOT, s_deck=s_deck, s_box=s_box, s_46=s_46, S_SEP=S_SEP)
# lateral: B/D centre +20.25 m from s S_SEP north (between Indianapolis and ORR E), reverse curve onto the KMZ line by Straight's north end
O_BD = 20.25
def o_c(s):
    if s <= S_ST1: return 0.0
    if s >= S_SEP: return O_BD
    return O_BD * (1 - math.cos(math.pi * (s - S_ST1) / (S_SEP - S_ST1))) / 2
def spread(s):  # island at Camp Washington: east track 18 -> 32.5 m
    return 0.0 if s <= S_CW0 - 80 else min(10.0, 10.0 * (s - (S_CW0 - 80)) / 80)
R_rev = (S_SEP - S_ST1) ** 2 / (4 * O_BD)
print('  B/D reverse curve onto the KMZ line s %.0f-%.0f, radius about %.0f m' % (S_ST1, S_SEP, R_rev))
ss = np.arange(2380, 3200, 2.0)
TW = LineString([at(s, o_c(s) - 2.25) for s in ss]); TE = LineString([at(s, o_c(s) + 2.25 + spread(s)) for s in ss])
# ---- dive-zone streets (v26 cut them at the corridor; extended across it here)
F = json.load(open(SP + 'deck/deck.json'))['features']
st_ = {f['properties']['id']: f for f in F if f['properties']['layer'] == 'street'}
def ends(fid):
    g = shape(st_[fid]['geometry']); c = list(g.coords) if g.geom_type == 'LineString' else list(list(g.geoms)[0].coords)
    a, b = Point(c[0]), Point(c[-1]); return (a, b) if C.distance(a) > C.distance(b) else (b, a)   # far, near
def ext(fid, L=90):
    far, near = ends(fid); d = np.array([near.x - far.x, near.y - far.y]); d /= np.linalg.norm(d)
    return LineString([(near.x, near.y), (near.x + d[0] * L, near.y + d[1] * L)])
def join(a, b):
    return LineString([ends(a)[1].coords[0], ends(b)[1].coords[0]])
X = {'Garrard line': (join('S041', 'S042'), 18.3), 'Meeker (carried south)': (join('S055', 'S056'), 9.1), 'Rawson (carried south)': (ext('S054'), 12.2),
     'Johnson (carried south)': (ext('S053'), 15.2), 'New street N': (ext('S052'), 18.3), 'Township (carried west)': (ext('S050'), 12.2),
     'Willow Lane (carried west)': (ext('S051'), 18.3), 'Marshall': (LineString(shape(st_['S049']['geometry']).coords), 18.3)}
rows = []
print('\n  street                      s range     street  rail     result')
for nm, (ln, w) in X.items():
    poly = ln.buffer(w / 2, cap_style=2)
    hits = []
    for T in (TW, TE):
        I = T.intersection(poly)
        if I.is_empty: continue
        for g in (I.geoms if hasattr(I, 'geoms') else [I]):
            for xy in g.coords: hits.append(C.project(Point(xy)))
    if not hits: print('  %-26s no crossing' % nm); rows.append(dict(street=nm, result='does not reach the B/D line')); continue
    s0, s1 = min(hits), max(hits); smid = (s0 + s1) / 2
    zs = deck(C.interpolate(smid).y)
    rails = [BDs(s) for s in np.arange(s0, s1 + 0.5, 0.5)]
    hi, lo = max(rails), min(rails)
    over = hi - zs; cover = zs - hi
    if lo - zs >= 6.5 - 0.05: res = ('under the station (%.1f m)' if s0 >= S_CW0 else 'under the ramp (%.1f m)') % (lo - zs)
    elif cover >= 5.2 - 0.01: res = 'box, cover %.1f m' % cover
    elif cover >= 4.6: res = 'roof as street, cover %.1f m (warning)' % cover
    else:
        lower = 6.5 - (lo - zs); raise_ = 5.2 - cover
        if min(lower, raise_) <= 3.0: res = ('lower the street %.1f m (passes under)' % lower) if lower <= raise_ else ('raise the street %.1f m (box)' % raise_)
        else: res = 'ENDS AT THE DIVE (lower %.1f m or raise %.1f m)' % (lower, raise_)
    rows.append(dict(street=nm, s0=round(s0), s1=round(s1), z=round(zs, 2), rail_hi=round(hi, 2), rail_lo=round(lo, 2), result=res))
    print('  %-26s %5.0f-%5.0f  %6.2f  %6.2f-%6.2f  %s' % (nm, s0, s1, zs, lo, hi, res))
out['dive_streets'] = rows
# ---- Indianapolis + D: KMZ curve (fit) and the climb
L = json.load(open(SP + 'nv/lines.json'))
IK = LineString([o for o in L if o['src'] == 'APEx' and o['name'] == 'Greensburg-CUT TRIMET'][0]['c'])
def kmz_off(s):
    p = C.interpolate(s); q = C.interpolate(s + 3); d = np.array([q.x - p.x, q.y - p.y]); d /= np.linalg.norm(d)
    a = (p.x - d[1] * 200, p.y + d[0] * 200); b = (p.x + d[1] * 200, p.y - d[0] * 200)
    I = IK.intersection(LineString([a, b])); g = I if I.geom_type == 'Point' else list(I.geoms)[0]
    return soff(g.x, g.y, s)
base = np.mean([kmz_off(s) for s in (3850, 3875, 3900)])
fit = [(s, base - kmz_off(s)) for s in range(4050, 4301, 25)]
best = min(((s0, R) for s0 in np.arange(3900, 3990, 1.0) for R in np.arange(600, 900, 5)),
           key=lambda t: sum(((s - t[0]) ** 2 / (2 * t[1]) - y) ** 2 for s, y in fit))
S_C, R_C = best
print('\nKMZ Indianapolis curve: starts s %.0f, radius about %.0f m (fit to s 4,050-4,300)' % (S_C, R_C))
G_SH, Z_TOP = 0.025, 174.3
S_A = next(s for s in np.arange(3300, S_C, 0.5) if min(Z_TOP, band(s) + G_SH * (S_C - s)) - band(S_C) <= 6.8) - 0.5
S_A = max(s for s in np.arange(3300, S_C, 0.5) if band(s) + G_SH * (S_C - s) - band(S_C) >= 6.8)
def SH(s): return band(s) if s <= S_A else min(Z_TOP, band(S_A) + G_SH * (s - S_A))
s_top = S_A + (Z_TOP - band(S_A)) / G_SH
# Indianapolis 6.75/11.25, D 15.75/20.25 east of the APEx line; the group follows the KMZ curve
y_clear = 20.25 + 22.5 + 9.0
s_clear = S_C + math.sqrt(2 * R_C * y_clear)
print('Indianapolis + D (one deck): leave the band at s %.0f (%.2f m), %.1f%% to %.1f m by s %.0f; %.2f m at the curve start (band %.2f, +%.2f); D clear of Transvalley/R5 at s %.0f' % (
    S_A, band(S_A), 100 * G_SH, Z_TOP, s_top, SH(S_C), band(S_C), SH(S_C) - band(S_C), s_clear))
# RER A crossing along the KMZ line
ra = Point(711810, 4336404); ell_c = IK.project(Point(at(S_C, base))); ell_ra = IK.project(ra)
print('RER A crossing about %.0f m along the curve from its start: %.1f m over RER A (167.0)' % (abs(ell_ra - ell_c), Z_TOP - 167.0))
out.update(S_C=S_C, R_C=R_C, S_A=S_A, s_top=s_top, s_clear=s_clear, G_SH=G_SH)
# D split (flat junction) between Camp Washington and the climb
print('D splits from B between s %.0f (Camp Washington north end) and s %.0f: %.0f m' % (S_CW1, S_A, S_A - S_CW1))
# ---- B north: band, Arlington level centred on the KMZ point
S_AR = 4146.0; S_AR0, S_AR1 = S_AR - 102, S_AR + 102; Z_AR = band(S_AR)
G_IN = (Z_TIP - Z_AR) / (S_AR0 - S_TIP)
S_OUT = S_AR1 + (Z_AR - band(S_AR1)) / (G_IN - G_BAND)
def B(s):
    if s <= S_TIP: return band(s)
    if s <= S_AR0: return Z_TIP - G_IN * (s - S_TIP)
    if s <= S_AR1: return Z_AR
    return max(band(s), Z_AR - G_IN * (s - S_AR1))
print('\nArlington (B): s %.0f-%.0f, level %.2f m (band %.2f-%.2f); B %.2f%% in from the tip, back on the band at s %.0f' % (S_AR0, S_AR1, Z_AR, band(S_AR0), band(S_AR1), 100 * G_IN, S_OUT))
out.update(S_AR0=S_AR0, S_AR1=S_AR1, Z_AR=Z_AR, G_IN=G_IN, S_OUT=S_OUT)
nst = [('Johnson (under the station)', 3130, None), ('Hopple', 3170, 158.9), ('Stock', 3471, 159.3), ('Ethan', 3573, 159.5), ('Bates', 3648, 159.6), ('Alabama', 3726, 159.8),
       ('Monmouth', 3903, 159.5), ('Sassafras', 4061, 154.1), ('Arlington St', 4135, 151.3), ('Marquis', 4211, 151.5), ('Adelaide', 4298, 151.7),
       ('Brashears', 4413, 152.1), ('Earl', 4556, 152.9), ('Whiteley', 4642, 152.9), ('Spring Grove 1904', 4801, 149.2), ('Ford', 4847, 151.2),
       ('Colerain', 4929, 151.3), ('Ford', 4943, 151.3)]
nrows = []
for nm, s, z in nst:
    if z is None: z = deck(C.interpolate(s).y)
    b = B(s); nrows.append(dict(street=nm, s=s, z=z, b=round(b, 2), clr=round(b - z, 2))); print('  %-28s s %d street %.1f  B %.2f  %.1f m' % (nm, s, z, b, b - z))
out['north_streets'] = nrows
# ---- widths (4.5 m in a group, 6.75 m between groups, 4.75 m to the edge)
W = {'Camp Washington to Arlington (ORR E 39.25/43.75)': (-22.5, 43.75), 'North of Arlington (10 tracks)': (-22.5, 24.75), 'Lobe as built (v26)': (-22.5, 22.5)}
for k, (a, b) in W.items(): print('  width %-48s %.2f m between outer tracks, deck %.2f m (%.2f to %.2f)' % (k, b - a, b - a + 9.5, a - 4.75, b + 4.75))
out['widths'] = {k: dict(tracks=b - a, deck=b - a + 9.5) for k, (a, b) in W.items()}
json.dump(out, open(SP + 'nv/v5.json', 'w'), indent=1, default=float)
