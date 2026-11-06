try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import sys, numpy as np
sys.path.insert(0, (_ws.CODE + 'trunk3')); import north as N, tv_profile as TP
A = TP.BED
low_tracks = (-11.25, -6.75, -2.25, 2.25); o0 = -18.0
for R in (400, 500, 600, 800, 1000, 1200):
    best = None
    for thd in np.arange(3.0, 20.01, 0.25):
        th = np.radians(thd)
        for s_c0 in np.arange(N.S_J1 + 10, 3700, 5):
            P, s_end = N.tv_centre(s_c0, R, th, o0, 12.75)
            if P is None: continue
            xs = [x for d in (2.25, -2.25) for o in low_tracks for x in N.crossings(N.offset_so(P, d), o)]
            sa, sb = min(xs), max(xs)
            need = N.CLR / (A[0] + N.G_MAX)
            if sa - N.S_J1 < need: continue
            z_low = np.polyval(A, N.S_J1) - N.G_MAX * need; g_up = (N.Z_ST - z_low) / (4150 - sb)
            if g_up > N.G_MAX: continue
            if best is None or s_end < best[3]: best = (R, thd, s_c0, s_end, sa, sb, z_low, g_up)
    print('R %.0f th %.2f start %.0f landed %.0f crossing %.0f-%.0f low %.1f up %.2f%%' % (best[0], best[1], best[2], best[3], best[4], best[5], best[6], 100 * best[7]))
