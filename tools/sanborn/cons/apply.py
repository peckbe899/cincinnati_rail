try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Metro track spacing by construction (Ben, 26 October 2026): bored stretches (shield, deep tube) are two single-track tubes, 8 m apart;
# cut-and-cover, open trough, at grade and elevated are one double-track structure, 3.9 m. Types from the Rail Profiles page's own
# typeAt on Ben's saved / default profiles. Island platforms open the tracks to 5.45 m either side; side platforms sit 1.45 m outside the tracks.
import json, sys, numpy as np
from shapely.geometry import LineString, Point, Polygon
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'cons'); sys.path.insert(0, _ws.CODE + 'rer1023')
import map_types as MT
from metro400 import frame, measure, _r1
H_TUBE, H_BOX, EDGE, ISL, SIDE_W, TAP, MIN_RUN = 4.0, 1.95, 1.45, 8.0, 4.0, 40.0, 60.0
def clean_runs(b, step):
    """fill gaps (nan) from neighbours, then merge runs shorter than MIN_RUN into the run before them"""
    b = b.copy(); idx = np.where(np.isfinite(b))[0]
    if len(idx) == 0: return np.zeros_like(b)
    b = np.interp(np.arange(len(b)), idx, b[idx]); b = (b >= 0.5).astype(float)
    for _ in range(3):
        runs = []; i = 0
        while i < len(b):
            j = i
            while j < len(b) and b[j] == b[i]: j += 1
            runs.append([i, j, b[i]]); i = j
        changed = False
        for k, (i0, j0, v) in enumerate(runs):
            if (j0 - i0) * step < MIN_RUN and len(runs) > 1:
                nb = runs[k - 1][2] if k > 0 else runs[k + 1][2]; b[i0:j0] = nb; changed = True
        if not changed: break
    return b
def smooth(h, step):
    n = max(1, int(round(TAP / step))); k = np.ones(n) / n; pad = np.r_[np.full(n, h[0]), h, np.full(n, h[-1])]
    return np.convolve(pad, k, mode='same')[n:-n]
def run(C):
    R = MT.piece_types(C); rep = {}
    plats = {}
    for p in C['plats']:
        if p['sys'] == 'metro': plats.setdefault(p['pid'], []).append(p)
    stub = {m['id'] for m in C['metro'] if np.hypot(*(np.array(m['c'][0]) - np.array(m['c'][-1]))) < 5 and LineString(m['c']).length < 300}
    newtracks = []
    for m in C['metro']:
        v = R.get(m['id'])
        if v is None or m['id'] in stub:
            newtracks += [t for t in C['tracks'] if t.get('sys') == 'metro' and t.get('pid') == m['id']]; continue
        g, ds, P, nr = v['g'], v['ds'], v['P'], v['nr']; step = float(ds[1] - ds[0]) if len(ds) > 1 else 2.0
        b = clean_runs(v['b'], step); h = smooth(np.where(b > 0.5, H_TUBE, H_BOX), step)
        base = h.copy(); hL = h.copy(); hR = h.copy(); W = np.zeros(len(ds))
        # stations on this piece: island (one polygon) or side (two)
        by_st = {}
        for p in plats.get(m['id'], []): by_st.setdefault(p['st'], []).append(p)
        for st, pp in by_st.items():
            meas = [measure(g, ds, P, nr, p['c']) for p in pp]
            a = min(x[0] for x in meas); bb = max(x[1] for x in meas)
            sel = (ds >= a) & (ds <= bb)
            if len(pp) == 1:                                   # island
                lo, hi = meas[0][2], meas[0][3]; tL = hi + EDGE; tR = -lo + EDGE
            else:                                              # side platforms: tracks keep the station's structure spacing, platforms outside
                hs = float(np.median(base[sel])) if sel.any() else H_BOX; tL = tR = hs
                for p, x in zip(pp, meas):
                    side = 1 if (x[2] + x[3]) > 0 else -1
                    Q, N_ = P[sel], nr[sel]
                    if len(Q) >= 2:
                        i0, i1 = (hs + EDGE, hs + EDGE + SIDE_W)
                        ring = np.r_[Q + N_ * side * i0, (Q + N_ * side * i1)[::-1]]
                        p['c'] = _r1(np.asarray(Polygon(ring).simplify(0.2).exterior.coords))
            d = np.maximum(np.maximum(a - ds, ds - bb), 0); w = np.clip(1 - d / TAP, 0, 1)
            upd = w > W; W = np.where(upd, w, W)
            hL = np.where(upd, base + (tL - base) * w, hL); hR = np.where(upd, base + (tR - base) * w, hR)
        for c in (P + nr * hL[:, None], P - nr * hR[:, None]):
            newtracks.append(dict(sys='metro', line=m['name'], pid=m['id'], c=_r1(np.asarray(LineString(c).simplify(0.15).coords))))
        # samples for the page (live-edited lines): every 20 m, 1 = bored twin tubes, 0 = double-track structure
        k = max(1, int(round(20.0 / step))); m['hs'] = [[round(float(P[i, 0]), 1), round(float(P[i, 1]), 1), int(b[i] > 0.5)] for i in range(0, len(ds), k)]
        rep[m['id']] = dict(bored_pct=round(100 * float(b.mean())), runs=int(1 + np.sum(np.diff(b) != 0)))
    C['tracks'] = [t for t in C['tracks'] if t.get('sys') != 'metro'] + newtracks
    C['meta']['metro_spacing'] = ('By construction (Ben, 26 October 2026): bored (shield, deep tube) two single-track tubes 8 m apart; cut-and-cover, trough, at grade and elevated '
                                  'one double-track structure 3.9 m; types from the Rail Profiles page (saved profiles, else its defaults); runs under 60 m merged; 40 m transitions')
    return rep
if __name__ == '__main__':
    C = json.load(open(SP + 'deckpage/context.json'))
    rep = run(C)
    for k, v in rep.items(): print(k, v)
    json.dump(C, open(SP + 'deckpage/context.json', 'w'), separators=(',', ':'))
