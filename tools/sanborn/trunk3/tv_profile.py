try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import sys, numpy as np
sys.path.insert(0, (_ws.CODE + 'trunk3'))
import north as N, build as B
FR = N.FR
_ss = np.arange(3000, 4201, 50.0); _gz = np.array([N.gsm(s, 0, 20) for s in _ss]); _ok = np.abs(_ss - 3400) > 60
BED = np.polyfit(_ss[_ok], _gz[_ok], 1)
def bed(s): return np.polyval(BED, s)
def crossing_span(opt):
    L = B.build(opt); tv = B.TV[opt]
    P, s_land = N.tv_centre(tv['s_c0'], tv['R'], np.radians(tv['th']), tv['o0'], 12.75)
    low = (-15.0, -10.5, -2.25, 2.25) if opt == 'A' else (-11.25, -6.75, -2.25, 2.25)
    xs = [x for d in (2.25, -2.25) for o in low for x in N.crossings(N.offset_so(P, d), o)]
    return min(xs), max(xs), s_land
def profiles(opt, ss):
    xa, xb, s_land = crossing_span(opt); g = N.G_MAX
    need = N.CLR / (BED[0] + g); s_lowa = N.S_J1 + need; z_low = bed(N.S_J1) - g * need
    g_up = (N.Z_ST - z_low) / (4150 - xb)
    low = np.where(ss <= N.S_J1, bed(ss), np.where(ss <= s_lowa, bed(N.S_J1) - g * (ss - N.S_J1), np.where(ss <= xb, z_low, z_low + g_up * (ss - xb))))
    # TV: the formation to the end of the crossing, then down to the platforms
    z_xb = bed(xb + 80); tv = np.where(ss <= xb + 80, bed(ss), z_xb + (N.Z_ST - z_xb) * (ss - xb - 80) / (4150 - xb - 80))
    gr = np.array([N.gsm(s, 0, 10) for s in ss])
    return dict(ground=gr, tv=tv, low=low, xa=xa, xb=xb, z_low=z_low, g_up=g_up, s_lowa=s_lowa, s_land=s_land, tv_down=(N.Z_ST - z_xb) / (4150 - xb - 80))
if __name__ == '__main__':
    for opt in ('A', 'B'):
        ss = np.arange(2900, 4201, 5.0); z = profiles(opt, ss)
        # clearance at each crossing point
        print(opt, 'crossing %.0f-%.0f, APEx/ORR down %.1f%% from %.0f to %.1f m at %.0f, up %.2f%% to %.1f m; TV landed %.0f, TV %.1f m at Section Ave, down %.2f%%' % (
            z['xa'], z['xb'], 100 * N.G_MAX, N.S_J1, z['z_low'], z['s_lowa'], 100 * z['g_up'], N.Z_ST, z['s_land'], np.interp(3939, ss, z['tv']), 100 * z['tv_down']))
        i = (ss >= z['xa']) & (ss <= z['xb']); print('   min TV over APEx/ORR in the span %.2f m; APEx/ORR under the ground at Section Ave %.1f m, at Reading Rd %.1f m' % ((z['tv'] - z['low'])[i].min(), N.gsm(3939, 0, 10) - np.interp(3939, ss, z['low']), N.gsm(3023, 0, 10) - np.interp(3023, ss, z['low'])))
