# Metro platforms to a new length (Ben, 23 October: 400 ft, 121.92 m; 6 x ~67 ft or 8 x ~50 ft cars).
# Every Metro platform keeps its centre (a platform at a line end keeps that end) and its sideways extent;
# twin-tube tracks re-spread to the new platform ends with the build's 40 m tapers. Bore tracks don't spread.
import math, numpy as np
from shapely.geometry import LineString, Point, Polygon
def _A(p): return np.asarray(p, float)
def _dense(V, K, step=2.0):
    out = [_A(V[0])]
    for i in range(len(V) - 1):
        a, b = _A(V[i]), _A(V[i + 1]); q = K.get(str(i))
        if q is None:
            n = max(1, int(math.ceil(np.hypot(*(b - a)) / step))); out += [a + (b - a) * j / n for j in range(1, n + 1)]; continue
        q = _A(q); n = max(4, int(np.hypot(*(b - a)) * 1.1 / step)); out += [(1 - t) ** 2 * a + 2 * (1 - t) * t * q + t * t * b for t in (np.arange(1, n + 1) / n)]
    return np.array(out)
def _r1(a): return [[round(float(x), 1), round(float(y), 1)] for x, y in a]
def frame(m):
    g = LineString(_dense(m['c'], m.get('k') or {})) if m.get('k') else LineString(m['c'])
    n = max(2, int(g.length / 2.0)); ds = np.linspace(0, g.length, n + 1); P = np.array([g.interpolate(d).coords[0] for d in ds])
    tg = np.gradient(P, axis=0); tg /= np.hypot(*tg.T)[:, None] + 1e-9
    for _ in range(3): tg[1:-1] = (tg[:-2] + 2 * tg[1:-1] + tg[2:]) / 4
    tg /= np.hypot(*tg.T)[:, None] + 1e-9; nr = np.c_[-tg[:, 1], tg[:, 0]]
    return g, ds, P, nr
def measure(g, ds, P, nr, ring):
    v = np.asarray(ring[:-1] if ring[0] == ring[-1] else ring, float)
    s = np.array([g.project(Point(q)) for q in v]); i = np.clip(np.searchsorted(ds, s), 0, len(ds) - 1)
    lat = np.einsum('ij,ij->i', v - P[i], nr[i]); ok = (s > 0.5) & (s < g.length - 0.5)   # vertices past a piece end project onto the end: their offsets are not used
    if ok.sum() >= 2: lat = lat[ok]
    return s.min(), s.max(), lat.min(), lat.max()
def spans_new(a, b, L, NEW):
    if a < 1.0: return 0.0 if a < 0 else a, min(L, max(a, 0) + NEW)
    if b > L - 1.0: return max(0.0, min(b, L) - NEW), min(b, L)
    c = (a + b) / 2; return max(0.0, c - NEW / 2), min(L, c + NEW / 2)
def twin_tracks(ds, P, nr, spans, cfg, taper):
    h = np.full(len(ds), cfg['h0']); hs = cfg['island'] / 2 + cfg['edge']
    for a, b in spans:
        d = np.maximum(np.maximum(a - ds, ds - b), 0); h = np.maximum(h, cfg['h0'] + (hs - cfg['h0']) * np.clip(1 - d / taper, 0, 1))
    return [_r1(np.asarray(LineString(P + nr * h[:, None] * sg).simplify(0.2).coords)) for sg in (1, -1)]
def apply(C, NEW, check_only=False):
    MT, TAP = C['meta']['metro_twin'], C['meta'].get('taper_m', 40.0); rep = dict(plats=0, pieces=0, dev=[], joined=[], dropped=0)
    FR = {m['id']: frame(m) for m in C['metro']}; NAME = {m['id']: m['name'] for m in C['metro']}
    info = {}
    for p in C['plats']:
        if p['sys'] != 'metro' or p.get('pid') not in FR: continue
        g, ds, P, nr = FR[p['pid']]; info[id(p)] = list(measure(g, ds, P, nr, p['c'])) + [g.length]
    span = {k: spans_new(v[0], v[1], v[4], NEW) for k, v in info.items()}
    # a station at a split between two pieces of one line (Price Hill, Newport-6th, Pennsylvania, West Covington): the platform is centred on the
    # station and the part past the piece end goes onto the next piece; loop stubs (pieces that start and end at one point) carry no platform
    stub = {k for k, f in FR.items() if np.hypot(*(np.array(f[2][0]) - np.array(f[2][-1]))) < 5 and f[0].length < 300}
    ends = {k: (np.array(f[2][0]), np.array(f[2][-1])) for k, f in FR.items()}
    drop, extra = set(), []
    for p in [p for p in C['plats'] if id(p) in info]:
        if p['pid'] in stub: drop.add(id(p)); continue
        a, b, lo, hi, L = info[id(p)]
        at = 'end' if b > L - 1 else 'start' if a < 1 else None
        if not at: continue
        e = ends[p['pid']][1 if at == 'end' else 0]
        cand = [(k, 'start' if np.hypot(*(ends[k][0] - e)) < 5 else 'end') for k in FR if k != p['pid'] and k not in stub and NAME[k] == NAME[p['pid']]
                and min(np.hypot(*(ends[k][0] - e)), np.hypot(*(ends[k][1] - e))) < 5]
        if not cand: continue
        k2, side2 = max(cand, key=lambda kv: FR[kv[0]][0].length)
        stp = min((st for st in C['stations'] if st['name'] == p['st']), key=lambda st: FR[p['pid']][0].distance(Point(st['p'])), default=None)
        if stp is None: continue
        sp = FR[p['pid']][0].project(Point(stp['p'])); u0, u1 = sp - NEW / 2, sp + NEW / 2
        span[id(p)] = (max(0.0, u0), min(L, u1)); over = (u1 - L) if at == 'end' else -u0
        if over <= 1: continue
        L2 = FR[k2][0].length; s2 = (0.0, min(L2, over)) if side2 == 'start' else (max(0.0, L2 - over), L2)
        flip = (at == 'end') == (side2 == 'end')
        q = dict(p); q['pid'] = k2; q['id'] = p['id'] + '-b'; extra.append(q)
        info[id(q)] = [s2[0], s2[1], (-hi if flip else lo), (-lo if flip else hi), L2]; span[id(q)] = s2
        rep['joined'].append((NAME[p['pid']], p['st'], round(span[id(p)][1] - span[id(p)][0], 1), round(s2[1] - s2[0], 1)))
        for r in C['plats']:                                           # the next piece's own cut part of this platform, if any, is replaced
            if r is not p and r.get('pid') == k2 and r['st'] == p['st'] and id(r) in info: drop.add(id(r))
    C['plats'] = [p for p in C['plats'] if id(p) not in drop] + extra; rep['dropped'] = len(drop)
    keep = []
    for p in C['plats']:
        if id(p) not in info: keep.append(p); continue
        na, nb = span[id(p)]; a, b, lo, hi, L = info[id(p)]
        if nb - na < 1.0: continue
        if not check_only:
            g, ds, P, nr = FR[p['pid']]; sel = (ds >= na - 1e-6) & (ds <= nb + 1e-6); Q, N_ = P[sel], nr[sel]
            if len(Q) >= 2:
                p['c'] = _r1(np.asarray(Polygon(np.r_[Q + N_ * hi, (Q + N_ * lo)[::-1]]).simplify(0.2).exterior.coords)); rep['plats'] += 1
        keep.append(p)
    if not check_only: C['plats'] = keep
    for m in C['metro']:
        mine_p = [p for p in keep if id(p) in info and p.get('pid') == m['id']]
        if not mine_p: continue
        g, ds, P, nr = FR[m['id']]
        if m.get('era') == 'twin':
            sp_old = sorted(set((round(info[id(p)][0], 1), round(info[id(p)][1], 1)) for p in mine_p))
            sp_new = sorted(set((round(span[id(p)][0], 1), round(span[id(p)][1], 1)) for p in mine_p))
            mine = [t for t in C['tracks'] if t['sys'] == 'metro' and t.get('pid') == m['id']]
            if check_only:
                re = twin_tracks(ds, P, nr, sp_old, MT, TAP)
                for t in mine: rep['dev'].append((m['id'], round(min(LineString(t['c']).hausdorff_distance(LineString(r)) for r in re), 2)))
            else:
                C['tracks'] = [t for t in C['tracks'] if not (t['sys'] == 'metro' and t.get('pid') == m['id'])] + [dict(sys='metro', line=m['name'], pid=m['id'], c=c) for c in twin_tracks(ds, P, nr, sp_new, MT, TAP)]
        rep['pieces'] += 1
    if not check_only: C['meta']['metro_platform_m'] = NEW
    return rep
