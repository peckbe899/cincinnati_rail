try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import sys, numpy as np
sys.path.insert(0, (_ws.CODE + 'trunk3')); import north as N
ss = np.arange(3000, 4201, 50.0); gz = np.array([N.gsm(s, 0, 20) for s in ss]); ok = np.abs(ss - 3400) > 60
A = np.polyfit(ss[ok], gz[ok], 1); print('bed fit: %.2f%%, %.1f m at s 3,250' % (100 * A[0], np.polyval(A, 3250)))
def bed(s): return np.polyval(A, s)
for gmax in (0.020, 0.025):
    for opt, (o0, low_tracks) in {'A': (-21.75, (-15.0, -10.5, -2.25, 2.25)), 'B': (-18.0, (-11.25, -6.75, -2.25, 2.25))}.items():
        best = None
        for R in np.arange(400, 3001, 50):
            for thd in np.arange(2.0, 15.01, 0.25):
                th = np.radians(thd)
                for s_c0 in np.arange(N.S_J1 + 10, 3700, 10):
                    P, s_end = N.tv_centre(s_c0, R, th, o0, 12.75)
                    if P is None or s_end > 3900: continue
                    tin, tout = N.offset_so(P, 2.25), N.offset_so(P, -2.25)
                    xs = [x for t in (tin, tout) for o in low_tracks for x in N.crossings(t, o)]
                    if not xs: continue
                    sa, sb = min(xs), max(xs)
                    need = N.CLR / (A[0] + gmax)
                    if sa - N.S_J1 < need: continue
                    z_low = bed(N.S_J1) - gmax * need
                    g_up = (N.Z_ST - z_low) / (4150 - sb)
                    if g_up > gmax: continue
                    cand = (R, thd, s_c0, s_end, sa, sb, z_low, g_up)
                    if best is None or (R, -s_end) > (best[0], -best[3]): best = cand
        if best: print('%.1f%%' % (100 * gmax), opt, 'R %.0f th %.2f curve start %.0f landed %.0f crossing %.0f-%.0f low %.1f climb %.2f%%' % (best[0], best[1], best[2], best[3], best[4], best[5], best[6], 100 * best[7]))
        else: print('%.1f%%' % (100 * gmax), opt, 'none')
