try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Lines north of Mitchell (s 8,080) for the 26 October extension. Returns dict name -> dict(c=Nx2 south->north / west->east, kind, ...)
import sys, numpy as np
from shapely.geometry import LineString, Point
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'trunk3')
import north as N
FR = N.FR
OPT = 'B'
TV = dict(A=dict(R=2100.0, th=7.25, s_c0=3360.0, o0=-21.75), B=dict(R=800.0, th=11.25, s_c0=3375.0, o0=-18.0))
def dedup(c):
    c = np.asarray(c, float); return c[np.r_[True, np.hypot(*np.diff(c, axis=0).T) > 0.05]]
def so2xy(P): return np.array([FR.nw_P(s, o) for s, o in P])
def build(opt=OPT):
    L = {}
    S_END_FD = N.FD.s[-1]
    # west group: X2 (to the plan window edge), APEx Dayton (to the border, on the ORR APEx alignment beyond Ivorydale)
    for k in (0, 1):
        c = N.FD.line(N.o_x2(k), N.S0, S_END_FD - 1, 2.0); L[f'X2 {k+1}'] = dict(c=N.clip_y(c, N.Y_WIN), kind='orr')
        c = N.FD.line(N.o_dayton(k), N.S0, S_END_FD - 1, 2.0); L[f'Dayton {k+1}'] = dict(c=N.clip_y(c, 4347000.0), kind='apex')
    # RER B: its own frame on the centre line built in north.b_centre()
    bc = np.load(SP + 'trunk3/bcen.npy'); FB = N.Frame(bc, 0.0)
    st = []
    for nm in ('Ivorydale', 'Elmwood Place', 'Paddock', 'Hamilton County Fairgrounds', 'Arlington Heights', 'Lockland/Reading', 'Aviation'):
        p = N._st[(nm, ('B',))]; sb = FB.proj(p); q = FB.at(sb)[0]
        sd = N.FD.proj(q); qd = N.FD.at(sd)[0]; ed = N.FD.at(sd, 1.0)[0] - qd; od = float((q - qd) @ ed)
        mode = 'sym' if abs(od) > 20 else ('west' if od < 0 else 'east'); st.append((nm, sb, mode, od))
    def b_off(k):
        def f(s):
            s = np.asarray(s, float); o = np.full(s.shape, (-2.25, 2.25)[k])
            for nm, sb, mode, od in st:
                a0, a1 = sb - N.LPL / 2, sb + N.LPL / 2
                d = {'west': (-9.9, 0.0), 'east': (0.0, 9.9), 'sym': (-4.95, 4.95)}[mode][k]
                if d == 0: continue
                up = N.bl(s, a0 - N.TP, a0, 0, d); dn = N.bl(s, a1, a1 + N.TP, d, 0); o = o + np.where(s < a0, up, np.where(s > a1, dn, d))
            return o
        return f
    for k in (0, 1):
        L[f'B {"SB" if k == 0 else "NB"}'] = dict(c=FB.line(b_off(k), 0.0, FB.s[-1], 2.0), kind='rer')
    L['B centre'] = dict(c=bc, kind='ref')
    L['_bst'] = [(nm, sb, mode, od, np.vstack([FB.at(np.arange(sb - N.LPL / 2, sb + N.LPL / 2 + 0.1, 2.0), b_off(0)(np.arange(sb - N.LPL / 2, sb + N.LPL / 2 + 0.1, 2.0)) + 1.75),
                   FB.at(np.arange(sb - N.LPL / 2, sb + N.LPL / 2 + 0.1, 2.0), b_off(1)(np.arange(sb - N.LPL / 2, sb + N.LPL / 2 + 0.1, 2.0)) - 1.75)[::-1]])) for nm, sb, mode, od in st]
    L['_FB'] = FB
    # east group: APEx Norwood on the branch frame (left track = north)
    for k in (0, 1):
        L[f'Norwood {k+1}'] = dict(c=N.FW.line(lambda s, o=(-2.25, 2.25)[k]: np.full(np.shape(s), o), N.S0, N.FW.s[-1], 2.0), kind='apex')
    # ORR / TV shared pair, then ORR to the throat (o_nw -10.5 = track 1, -15 = track 2)
    tv = TV[opt]
    for k in (0, 1):
        o_t = (-10.5, -15.0)[k]
        if opt == 'A':
            R, st, a, s_end = N.e_track_A(k)
            ax = N.NWL(lambda s, o=o_t: np.full(np.shape(s), o), s_end + 1.0, FR.S_NW, 2.0)
            c = np.vstack([st, a, ax]); L[f'ORR {k+1}'] = dict(c=dedup(c), kind='orr', R=R)
        else:
            o_c = (-6.75, -11.25)[k]
            st = np.array([N.p0 + N.rnorm(N.u0) * (15.75, 20.25)[k] + N.u0 * x for x in np.arange(0.0, N.S_NC0 - N.S0, 1.0)])
            R = N.R_N - (6.75, 11.25)[k]; O = N.O_N; p = N.p0 + N.rnorm(N.u0) * (15.75, 20.25)[k] + N.u0 * (N.S_NC0 - N.S0)
            Tt = O + (FR.nw_P(N.S_NCE, o_c) - O) / np.hypot(*(FR.nw_P(N.S_NCE, o_c) - O)) * R
            a = N.arc(O, R, p, Tt)
            ax = N.NWL(lambda s, oc=o_c, ot=o_t: N.bl(s, 3650.0, 3900.0, oc, ot), N.S_NCE + 1.0, FR.S_NW, 2.0)
            L[f'ORR {k+1}'] = dict(c=dedup(np.vstack([st, a, ax])), kind='orr', R=R)
    # Transvalley: off the shared pair east of Reading Road (Aloysius), parallel to the south, then over ORR and APEx onto T10 / T9
    o_in0, o_out0 = (-10.5, -15.0) if opt == 'A' else (-6.75, -11.25)
    P, s_land = N.tv_centre(tv['s_c0'], tv['R'], np.radians(tv['th']), tv['o0'], 12.75)
    for k, (d, o_from, nm) in enumerate(((2.25, o_in0, 'TV 1 (inbound, T10)'), (-2.25, o_out0, 'TV 2 (outbound, T9)'))):
        o_par = tv['o0'] + d
        s0 = N.S_J0; s1 = N.S_J1 + (30.0 if k == 0 else 0.0)
        j = np.array([(s, float(N.bl(s, s0, s1, o_from, o_par))) for s in np.arange(s0, s1 + 0.1, 2.0)])
        par = np.array([(s, o_par) for s in np.arange(s1 + 2.0, tv['s_c0'], 2.0)])
        dia = N.offset_so(P, d)
        tail = np.array([(s, 12.75 + d) for s in np.arange(s_land + 2.0, FR.S_NW, 2.0)] + [(FR.S_NW, 12.75 + d)])
        L[nm] = dict(c=dedup(so2xy(np.vstack([j, par, dia, tail]))), kind='tv', s_from=s0)
    L['_meta'] = dict(s_land=s_land, opt=opt, tv=tv)
    return L
if __name__ == '__main__':
    L = build()
    for k, v in L.items():
        if k.startswith('_'): print(k, v); continue
        c = v['c']; print('%-22s %5d pts  %.0f m  start %s end %s' % (k, len(c), LineString(c).length, c[0].round(1), c[-1].round(1)))
