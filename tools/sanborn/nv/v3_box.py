"""North trunk viaduct v3 (10za.13+): Indianapolis leaves from the west side, ORR stays east, TRI B/D in a box.
True chainage (profile.json rebuilt after the KMZ vertex-order glitch). Writes nv/v3.json."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, math, numpy as np, rasterio
from shapely.geometry import LineString, Point
SP = _ws.DATA
P = json.load(open(SP + 'nv/profile.json')); C = LineString(P['C'])
V = json.load(open(SP + 'nv/viaduct.json'))
DEM = rasterio.open(SP + 'handoff/out/map3_profile_dem_dm.vrt')
def gz(e, n):
    v = list(DEM.sample([(e, n)]))[0][0]; return float('nan') if v < -30000 else v / 10
def deck(n): return 151.8 + (n - 4330700) / 4840 * 8.2
L = json.load(open(SP + 'nv/lines.json'))
R5K = json.load(open(SP + 'nv/orr_near.json'))['lines']
RA = json.load(open(SP + 'rera/rera.json'))

S_TIP, S_LUD = V['s_tip'], 5300.0          # Ludlow Avenue (OSM) on the corrected chainage; the 1922 bridge is at s 5,368
Z_TIP = deck(C.interpolate(S_TIP).y) + 6.5; Z_LUD = 155.5
G = (Z_TIP - Z_LUD) / (S_LUD - S_TIP)
def band(s):                                 # APEx Dayton/Norwood + ORR (and B north of Ford, Transvalley north of its dip)
    if s <= S_TIP: return deck(C.interpolate(s).y) + 6.5
    if s <= S_LUD: return Z_TIP - G * (s - S_TIP)
    return Z_LUD
# Transvalley pair: drops 2% from the tip so the Indianapolis pair can pass over it, holds, then rejoins the band
TV_G, TV_HOLD = 0.02, 159.8
S_TV1 = S_TIP + (Z_TIP - TV_HOLD) / TV_G
S_TV2 = S_TIP + (Z_TIP - TV_HOLD) / G
def tv(s):
    if s <= S_TIP: return band(s)
    if s <= S_TV1: return Z_TIP - TV_G * (s - S_TIP)
    if s <= S_TV2: return TV_HOLD
    return band(s)
# Indianapolis pair: climbs from S_I0 on the west side of the arch viaduct
S_I0, I_G, I_TOP = 3800.0, 0.013, 174.3
def indy_at(ell):                            # ell = distance along the Indianapolis path measured from S_I0 (path follows the trunk to the KMZ curve)
    return min(I_TOP, band(S_I0) + I_G * max(0.0, ell))
# TRI B/D (box): under the deck at 151.8, 1.7% down to the Arlington box station, level, dip under the 1904 Spring Grove Ave, up to Ludlow
BD_PTS = [(3700, 151.8), (4053, 145.8), (4600, 145.8), (4801, 143.9), (4943, 146.1), (5350, 155.5)]
def bd(s):
    if s <= BD_PTS[0][0]: return 151.8
    for (s0, z0), (s1, z1) in zip(BD_PTS, BD_PTS[1:]):
        if s <= s1: return z0 + (z1 - z0) * (s - s0) / (s1 - s0)
    return 155.5
S_STN = (4044, 4248)                         # Arlington box station, 204 m, centred on the KMZ point (s 4,146)
S_D = 4295                                   # D leaves the box westward (TRIMET 3D divergence)
# R5: leaves the ORR pair on the east at S_R0, climbs gently while the band comes down, crosses over the band west
S_R0, R_G, R_TOP = 4300.0, 0.006, 166.4
def r5(s): return min(R_TOP, band(S_R0) + R_G * (s - S_R0))

out = dict(S_TIP=S_TIP, S_LUD=S_LUD, Z_TIP=Z_TIP, G=G, S_TV1=S_TV1, S_TV2=S_TV2, S_I0=S_I0, I_G=I_G, BD=BD_PTS, S_STN=S_STN, S_D=S_D, S_R0=S_R0, R_G=R_G, R_TOP=R_TOP)
print('band: %.2f m at the tip (s %.0f), %.3f%% to %.1f m at Ludlow (s %.0f), %.0f m' % (Z_TIP, S_TIP, 100 * G, Z_LUD, S_LUD, S_LUD - S_TIP))
print('Transvalley: 2%% from the tip to %.1f m at s %.0f, level to s %.0f, then with the band' % (TV_HOLD, S_TV1, S_TV2))

# street checks (crossing chainages on the APEx line, corrected)
rows = sorted([r for r in V['rows'] if r[1] == 'APEx/ORR'], key=lambda r: r[2])
chk = []
print('\nstreet        s     ground  band  clr | Transv clr | B/D box cover')
for nm, _, s, x, y, zs in rows:
    need = 6.5 if s < S_TIP + 10 else 6.8
    b, t, d = band(s), tv(s), bd(s)
    cov = zs - d
    boxres = 'under the deck' if s < S_TIP + 10 else ('box' if cov >= 5.2 else ('roof-as-street' if cov >= 4.6 else 'OPEN TROUGH'))
    chk.append(dict(street=nm, s=s, ground=zs, band=round(b, 2), band_clr=round(b - zs, 2), tv=round(t, 2), tv_clr=round(t - zs, 2), bd=round(d, 2), bd_cover=round(cov, 2), bd_result=boxres, ok=bool(b - zs >= need - 0.05 and t - zs >= need - 0.05)))
    print('%-13s %5d  %5.1f  %5.1f %4.1f | %5.1f %4.1f | %5.1f %4.1f %s' % (nm[:13], s, zs, b, b - zs, t, t - zs, d, cov, boxres))
out['streets'] = chk

# Indianapolis over Transvalley (KMZ curve): where the path is 16-27 m west of the APEx line (Transvalley tracks at -22.5/-18 m)
ik = [o for o in L if o['src'] == 'APEx' and o['name'] == 'Greensburg-CUT TRIMET'][0]
I = np.array(ik['c'])
ii = [i for i, p in enumerate(I) if C.distance(Point(p)) < 2 and abs(C.project(Point(p)) - S_I0) < 400]
i0 = min(ii, key=lambda i: abs(C.project(Point(I[i])) - S_I0))
step = -1 if C.project(Point(I[i0 - 1])) > C.project(Point(I[i0])) else 1
seq = [I[i0]]; i = i0
while 0 <= i + step < len(I) and len(seq) < 60: i += step; seq.append(I[i])
IP = LineString(seq)
print('\nIndianapolis path from s %.0f (vertex %d), %d vertices, %.0f m' % (C.project(Point(I[i0])), i0, len(seq), IP.length))
cross = []
for ell in np.arange(0, 700, 5):
    p = IP.interpolate(ell); d = C.distance(p); s = C.project(p)
    if 15.5 <= d <= 27.5: cross.append((ell, s, d, indy_at(ell), tv(s)))
cmin = min(cross, key=lambda r: r[3] - r[4])
print('Indy over Transvalley: s %.0f-%.0f; least clearance %.1f m at s %.0f (Indy %.1f, Transvalley %.1f)' % (cross[0][1], cross[-1][1], cmin[3] - cmin[4], cmin[1], cmin[3], cmin[4]))
out['indy_over_tv'] = dict(s0=cross[0][1], s1=cross[-1][1], min_clear=cmin[3] - cmin[4], at_s=cmin[1], indy=cmin[3], tv=cmin[4])
ra = Point(711810, 4336404); ell_ra = IP.project(ra)
print('Indy at the RER A crossing: %.0f m along, %.1f m (RER A 167.0: %.1f m)' % (ell_ra, indy_at(ell_ra), indy_at(ell_ra) - 167.0))
out['indy_at_rera'] = dict(ell=ell_ra, z=indy_at(ell_ra), clear=indy_at(ell_ra) - 167.0, dist_to_path=IP.distance(ra))
out['indy_path'] = [list(map(float, q)) for q in IP.coords]
# R5 crossing over the band (needs 6.8 m over band and Transvalley)
r5ok = [(s, r5(s), band(s), tv(s)) for s in range(4300, 5301, 10)]
first = next(s for s, r, b, t in r5ok if r - max(b, t) >= 6.8)
print('\nR5: leaves ORR at s %.0f (%.1f m), %.1f%% up to %.1f m; 6.8 m over the band and Transvalley from s %d' % (S_R0, band(S_R0), 100 * R_G, R_TOP, first))
out['r5_first_cross'] = first
# B/D grades
for (s0, z0), (s1, z1) in zip(BD_PTS, BD_PTS[1:]): print('B/D s %d-%d: %.1f -> %.1f (%.2f%%)' % (s0, s1, z0, z1, 100 * (z1 - z0) / (s1 - s0)))
print('Arlington box station s %d-%d at %.1f m; street levels over it: Sassafras 154.1, Arlington 151.3, Marquis 151.5' % (S_STN[0], S_STN[1], bd(4146)))
# D westward from the box: TRIMET's tunnel point 187.1 m at (710982, 4336782)
dk = [o for o in L if o['src'] == 'TRIMET3D' and o['name'] == 'Greensburg-California 3D'][0]
D3 = np.array(dk['c']); jd = int(np.argmin([C.distance(Point(p)) + abs(C.project(Point(p)) - S_D) * 0.0 for p in D3]))
pD = C.interpolate(S_D); kd = int(np.argmin(np.hypot(D3[:, 0] - pD.x, D3[:, 1] - pD.y)))
kt = int(np.argmin(np.hypot(D3[:, 0] - 710982, D3[:, 1] - 4336782)))
seg = D3[min(kd, kt):max(kd, kt) + 1]; dl = float(np.sum(np.hypot(*np.diff(seg, axis=0).T)))
print('D: box %.1f m at s %d to TRIMET 187.1 m (in tunnel, ground 240) over %.0f m along TRIMET: %.2f%%' % (bd(S_D), S_D, dl, 100 * (187.1 - bd(S_D)) / dl))
out['d_climb'] = dict(len=dl, g=(187.1 - bd(S_D)) / dl)
# widths
def span(groups):
    x = 0; first = True; prev = None
    for g, n in groups:
        if not first: x += 6.75
        x += 4.5 * (n - 1); first = False
    return x
W = {}
for k, g in (('lobe', [('Tv', 2), ('APEx', 6), ('ORR', 2)]), ('north', [('Tv', 2), ('B', 2), ('APEx', 4), ('ORR', 2)])):
    sp = span(g); W[k] = dict(span=sp, deck=sp + 9.5)
    print('%s: %s between outer tracks %.2f m, deck %.2f m' % (k, g, sp, sp + 9.5))
out['widths'] = W
# I-75 trench vs the west edge north of Ford (west edge 27.25 m west of the APEx line)
tr = []
for s in range(4950, 7400, 100):
    p = C.interpolate(s); q = C.interpolate(s + 2); t = np.array([q.x - p.x, q.y - p.y]); t /= np.linalg.norm(t); n = np.array([t[1], -t[0]])
    prof = [(o, gz(p.x - n[0] * o, p.y - n[1] * o)) for o in range(0, 101, 2)]
    lip = next((o for o, z in prof if z < 148.0), None)
    tr.append((s, lip))
print('\ntrench (<148 m) nearest point west of the APEx line, by s:', tr)
out['trench'] = tr
json.dump(out, open(SP + 'nv/v3.json', 'w'), indent=1, default=float)
