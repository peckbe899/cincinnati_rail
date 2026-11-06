"""North trunk v4 levels (10za.24-28): B/D climb linked from Camp Washington to the Indianapolis/D crossover.
Order west to east: Transvalley/R5, APEx Dayton/Norwood 4, APEx Indianapolis 2, TRI B/D 2, ORR E 2. Writes nv/v4.json."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, numpy as np, rasterio
from shapely.geometry import LineString, Point
SP = _ws.DATA
C = LineString(json.load(open(SP + 'nv/profile.json'))['C'])
DEM = rasterio.open(SP + 'handoff/out/map3_profile_dem_dm.vrt')
def gz(e, n):
    v = list(DEM.sample([(e, n)]))[0][0]; return float('nan') if v < -30000 else v / 10
def deck(n): return 151.8 + (n - 4330700) / 4840 * 8.2
S_TIP, S_LUD, Z_LUD = 3895.2, 5300.0, 155.5
Z_TIP = deck(C.interpolate(S_TIP).y) + 6.5
G_BAND = (Z_TIP - Z_LUD) / (S_LUD - S_TIP)
def band(s):            # APEx Dayton/Norwood, ORR E, Transvalley/R5
    if s <= S_TIP: return deck(C.interpolate(s).y) + 6.5
    return max(Z_LUD, Z_TIP - G_BAND * (s - S_TIP))
def pw(pts):
    def f(s):
        if s <= pts[0][0]: return pts[0][1]
        for (s0, z0), (s1, z1) in zip(pts, pts[1:]):
            if s <= s1: return z0 + (z1 - z0) * (s - s0) / (s1 - s0)
        return pts[-1][1]
    return f
S_CW, Z_CW = 3168.0, 151.4            # Camp Washington B/D platform north end (station s 2,964-3,168, TRIMET 151.3 m)
S_MON, Z_MON = 3903.0, 154.3          # under Monmouth: box with 0.6 m cover (street 159.5 m - 5.2 m)
G2 = 0.030                            # from the deck edge
Z_STN = 158.5                         # Arlington (B) platform level
S_ST0 = S_MON + (Z_STN - Z_MON) / G2  # station south end
S_ST1 = S_ST0 + 204.0
bd_pts = [(S_CW, Z_CW), (S_MON, Z_MON), (S_ST0, Z_STN)]
B = pw(bd_pts + [(S_ST1, Z_STN), (S_ST1 + (159.8 - Z_STN) / 0.004, 159.8), (4754.0, 159.8), (S_LUD, Z_LUD)])
# Indianapolis stays in the band until D, climbing beside the Arlington platforms, reaches its level; from there one 4-track viaduct
D_G, G_SH = 0.030, 0.025            # D alone at 3.0% (B/D ramp grade); shared Indianapolis + D deck at 2.5% (APEx preferred 2.0-2.5%, max 3.0%)
def D_alone(s): return Z_STN + D_G * (s - S_ST0)
S_J = next(s for s in np.arange(S_ST0, 5000, 0.5) if D_alone(s) >= band(s))
Z_J = band(S_J)
def SH(s): return min(174.3, Z_J + G_SH * (s - S_J))
def D(s):
    if s < S_ST0: return B(s)
    return D_alone(s) if s < S_J else SH(s)
def INDY(s): return band(s) if s < S_J else SH(s)
S_C0 = next(s for s in np.arange(S_J, 5000, 0.5) if SH(s) - band(s) >= 6.8)   # curve start (600 m radius): Indianapolis's west track goes over APEx D/N at once
s_dover = S_C0 + np.sqrt(2 * 600 * 9.0)           # D's west track over APEx Dayton/Norwood
s_end = S_C0 + np.sqrt(2 * 600 * 51.75)           # D's east track clear of Transvalley/R5
s_top = S_J + (174.3 - Z_J) / G_SH
out = dict(S_TIP=S_TIP, Z_TIP=Z_TIP, G_BAND=G_BAND, S_CW=S_CW, S_MON=S_MON, Z_MON=Z_MON, G2=G2, Z_STN=Z_STN, S_ST0=S_ST0, S_ST1=S_ST1,
           S_C0=S_C0, s_dover=s_dover, s_end=s_end, S_J=S_J, Z_J=Z_J, G_SH=G_SH, s_top=s_top)
print('B/D: %.1f m at Camp Washington (s %d), %.3f%% under the deck to %.1f m under Monmouth (s %d), %.1f%% to %.1f m at s %.0f' % (
    Z_CW, S_CW, 100 * (Z_MON - Z_CW) / (S_MON - S_CW), Z_MON, S_MON, 100 * G2, Z_STN, S_ST0))
print('Arlington (B): s %.0f-%.0f, centre %.0f (KMZ point s 4,146)' % (S_ST0, S_ST1, (S_ST0 + S_ST1) / 2))
print('D alone at 3.0%% from s %.0f to s %.0f, where it meets Indianapolis (in the band) at %.2f m; one deck from there at %.1f%%' % (S_ST0, S_J, Z_J, 100 * G_SH))
print('shared deck clears the band by 6.8 m from s %.0f (curve start); D over APEx D/N from s %.0f; clear of Transvalley/R5 at s %.0f; 174.3 m from s %.0f' % (S_C0, s_dover, s_end, s_top))
streets = [('Hopple (at deck level)', 3160, 158.9), ('Stock', 3471, 159.3), ('Ethan', 3573, 159.5), ('Bates', 3648, 159.6), ('Alabama', 3726, 159.8),
           ('Monmouth', 3903, 159.5), ('Sassafras', 4061, 154.1), ('Arlington St', 4135, 151.3), ('Marquis', 4211, 151.5), ('Adelaide', 4298, 151.7),
           ('Brashears', 4413, 152.1), ('Earl', 4556, 152.9), ('Whiteley', 4642, 152.9), ('Spring Grove 1904', 4801, 149.2), ('Ford', 4847, 151.2),
           ('Colerain', 4929, 151.3), ('Ford', 4943, 151.3)]
rows = []
for nm, s, z in streets:
    b = B(s); d = b - z
    res = 'street over, box cover %.1f' % (-d) if -d >= 5.2 - 0.01 else ('street under %.1f' % d if d >= 6.8 - 0.05 else 'CONFLICT %.1f' % d)
    if nm == 'Sassafras' and d < 6.8: res = 'lower the street %.1f m (to %.1f)' % (z - (b - 6.8), b - 6.8)
    rows.append(dict(street=nm, s=s, z=z, b=round(b, 2), result=res)); print('  %-22s s %d street %.1f B %.2f  %s' % (nm, s, z, b, res))
out['streets'] = rows
json.dump(out, open(SP + 'nv/v4.json', 'w'), indent=1, default=float)
