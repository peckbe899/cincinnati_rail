try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Unbroken lines (Ben, 24 October: "check all RER and metro lines to see if they're unbroken").
# Every loose piece end of a line is joined to the piece of the same line it was drawn to meet:
#   - end to end (the next piece starts where this one should carry on): two quadratic curves, tangent to both pieces;
#   - onto another piece's middle (a branch drawn short of its trunk): the same curves, landing on the trunk ahead;
#   - gaps under 20 m: the loose end point is moved onto the other piece.
# Pieces Ben has edited on the page (live layout) are never moved; the other piece moves to meet them.
# Left open: the Union Terminal box (drawn on its own, meta ut_box) and real line ends.
import json, math, numpy as np
from shapely.geometry import LineString, Point
import metro400 as M
SP = _ws.DATA
UT = np.array([712858.0, 4331868.0]); UT_R = 300.0
MAXGAP = 300.0
SPLITS = [('RER A', 'R-A-716800-4335070', -1, ['R-A-718533-4336147', 'R-A-718498-4336199'])]   # Xavier: RER-1y to Milford, RER-1x to Norwood
def _lines(m, sysn): return [m['name']] if sysn == 'metro' else ['RER ' + l for l in m.get('lines', [])]
def _geom(m, E):
    e = E.get(m['id'])
    if e: return LineString(M._dense(e['c'], e.get('k') or {})) if e.get('k') else LineString(e['c'])
    return M.frame(m)[0]
def _tan(g, e):
    L = g.length; p = np.array(g.coords[0 if e == 0 else -1]); r = np.array(g.interpolate(min(12, L / 2) if e == 0 else max(L - 12, L / 2)).coords[0])
    v = p - r; return v / (np.linalg.norm(v) + 1e-9)
def _tan_at(g, s):
    a = np.array(g.interpolate(max(0, s - 6)).coords[0]); b = np.array(g.interpolate(min(g.length, s + 6)).coords[0]); v = b - a; return v / (np.linalg.norm(v) + 1e-9)
def _bridge(q, t, T, tT):
    """two quadratics from q (heading t) to T (heading tT on arrival); returns [mid, T] vertices and their controls"""
    d = float(np.linalg.norm(T - q)); a = d / 3.0
    K1 = q + t * a; K2 = T - tT * a; Mm = (K1 + K2) / 2
    return [Mm, T], [K1, K2]
def plan(C, E):
    PIE = {}
    for sysn in ('metro', 'rer'):
        for m in C[sysn]: PIE[m['id']] = (sysn, m, _geom(m, E), m['id'] in E)
    byline = {}
    for pid, (sysn, m, g, ed) in PIE.items():
        for ln in _lines(m, sysn): byline.setdefault(ln, []).append(pid)
    WX, WY = (699000.0, 736900.0), (4320800.0, 4347000.0)              # the plan's outer edges: a line ending there carries on off the map
    def at_edge(p): return min(abs(p[0] - v) for v in WX) < 2 or min(abs(p[1] - v) for v in WY) < 2
    ends = {}
    for ln, ids in byline.items():
        for pid in ids:
            g = PIE[pid][2]
            for e in (0, -1):
                q = Point(g.coords[e]); ok = any(PIE[o][2].distance(q) < 0.5 for o in ids if o != pid)
                ends.setdefault((pid, e), {})[ln] = ok
    loose = []
    for (pid, e), st in ends.items():
        g = PIE[pid][2]; q = np.array(g.coords[e])
        if np.linalg.norm(q - UT) < UT_R or at_edge(q): continue
        free = (not any(st.values())) and not PIE[pid][3]                  # loose for every line it carries, and not Ben's edit: it may move
        for ln, ok in st.items():
            if not ok: loose.append(dict(ln=ln, pid=pid, e=e, q=q, t=_tan(g, e), free=free, nl=len(st)))
    joins, done = [], set()
    def key(z): return (z['pid'], z['e'], z['ln'])
    # 0. a trunk that splits in two where it ends: both branches start from the trunk's end
    for ln, tp, te, brs in SPLITS:
        xs = [z for z in loose if z['ln'] == ln and z['pid'] == tp and z['e'] == te]
        ys = [z for z in loose if z['ln'] == ln and z['pid'] in brs and z['e'] == 0]
        if not xs or len(ys) != len(brs): continue
        for y in ys:
            joins.append(dict(kind='pair', ln=ln, a=y, b=xs[0], d=round(float(np.linalg.norm(y['q'] - xs[0]['q'])), 1), mov=y)); done.add(key(y))
        done.add(key(xs[0]))
    # 1. end to end
    pairs = []
    for i, x in enumerate(loose):
        for y in loose[i + 1:]:
            if y['ln'] != x['ln'] or y['pid'] == x['pid'] or not (x['free'] or y['free']): continue
            v = y['q'] - x['q']; d = float(np.linalg.norm(v))
            if d > MAXGAP or d < 0.3: continue
            u = v / d
            ok = u @ x['t'] > 0.5 and -u @ y['t'] > 0.5
            # a free branch end may also run in to a shared end (a junction drawn as the trunk piece's end)
            ok = ok or (x['free'] and not y['free'] and u @ x['t'] > 0.3 and -u @ y['t'] > 0.0) or (y['free'] and not x['free'] and -u @ y['t'] > 0.3 and u @ x['t'] > 0.0)
            if d < 20 or ok: pairs.append((d, x, y))
    for d, x, y in sorted(pairs, key=lambda r: r[0]):
        if key(x) in done or key(y) in done: continue
        done |= {key(x), key(y)}; joins.append(dict(kind='pair', ln=x['ln'], a=x, b=y, d=round(d, 1)))
    # 2. a free end onto another piece of the line, ahead of it
    for x in loose:
        if key(x) in done: continue
        if not x['free']:
            # Ben's edit or a shared end: the other piece's nearest end within 20 m moves to it
            near = [(float(np.linalg.norm(np.array(PIE[o][2].coords[f]) - x['q'])), o, f) for o in byline[x['ln']] if o != x['pid'] and not PIE[o][3] for f in (0, -1)]
            near = [r for r in near if r[0] < 20]
            if near:
                d, o, f = min(near); done.add(key(x))
                joins.append(dict(kind='pull', ln=x['ln'], a=x, o=o, f=f, d=round(d, 1)))
            continue
        cand = [(PIE[o][2].distance(Point(x['q'])), o) for o in byline[x['ln']] if o != x['pid']]
        cand = [c for c in cand if c[0] < MAXGAP]
        if not cand: continue
        dn, o = min(cand); g2 = PIE[o][2]; s0 = g2.project(Point(x['q']))
        tg = _tan_at(g2, s0); sg = 1.0 if tg @ x['t'] >= 0 else -1.0
        done.add(key(x))
        if dn < 20:
            joins.append(dict(kind='onto', ln=x['ln'], a=x, onto=o, T=np.array(g2.interpolate(s0).coords[0]), tT=tg * sg, d=round(dn, 1), K=None)); continue
        # one quadratic: its control is where the loose end's line meets the trunk's tangent at the landing point; the landing point is
        # the one that gives equal tangent lengths (the nearest to a circular arc)
        best = None
        for sT in np.arange(0, g2.length, 2.0):
            T = np.array(g2.interpolate(sT).coords[0]); tT = _tan_at(g2, sT) * sg
            A = np.c_[x['t'], tT]
            if abs(np.linalg.det(A)) < 1e-3: continue
            a, b = np.linalg.solve(A, T - x['q'])                         # q + t a = T - tT b  ->  t a + tT b = T - q
            if a < 8 or b < 8: continue
            sc = abs(a - b) / (a + b)
            if best is None or sc < best[0]: best = (sc, T, tT, x['q'] + x['t'] * a)
        if best is None or best[0] > 0.6:
            L = float(np.clip(3.0 * dn, 20.0, 250.0)); sT = float(np.clip(s0 + sg * L, 0, g2.length))
            joins.append(dict(kind='onto', ln=x['ln'], a=x, onto=o, T=np.array(g2.interpolate(sT).coords[0]), tT=_tan_at(g2, sT) * sg, d=round(dn, 1), K=None))
        else:
            joins.append(dict(kind='onto', ln=x['ln'], a=x, onto=o, T=best[1], tT=best[2], d=round(dn, 1), K=best[3]))
    return joins, PIE
def _reverse_k(m):
    n = len(m['c']); k = m.get('k') or {}
    m['c'] = m['c'][::-1]; m['k'] = {str(n - 2 - int(i)): v for i, v in k.items()}
def _extend(m, e, verts, ctrls):
    """add verts after the piece's end e (0: before its start, -1: after its end); ctrls[i] is the control into verts[i]"""
    flip = e == 0
    if flip: _reverse_k(m)
    k = dict(m.get('k') or {}); n = len(m['c'])
    for i, (v, c) in enumerate(zip(verts, ctrls)):
        m['c'].append(M._r1([v])[0])
        if c is not None: k[str(n - 1 + i)] = M._r1([c])[0]
    m['k'] = k
    if flip: _reverse_k(m)
def _snap(m, e, T):
    m['c'][0 if e == 0 else -1] = M._r1([T])[0]
def respread(C, m, sysn):
    if sysn == 'metro' and m.get('era') == 'bore':
        cfg, spans = dict(C['meta']['metro_bore'], island=2 * (C['meta']['metro_bore']['h0'] - C['meta']['metro_bore']['edge'])), []
    else:
        cfg = C['meta']['metro_twin'] if sysn == 'metro' else C['meta']['rer']
        g, ds, Pp, nr = M.frame(m)
        spans = sorted(set((round(a, 1), round(b, 1)) for a, b, lo, hi in (M.measure(g, ds, Pp, nr, p['c']) for p in C['plats'] if p.get('pid') == m['id'])))
    g, ds, Pp, nr = M.frame(m)
    line = m['name'] if sysn == 'metro' else ' '.join(m.get('lines', []))
    keep = [t for t in C['tracks'] if t.get('pid') != m['id']]
    C['tracks'] = keep + [dict(sys=sysn, line=line, pid=m['id'], c=c) for c in M.twin_tracks(ds, Pp, nr, spans, cfg, C['meta'].get('taper_m', 40.0))]
def apply(C, E):
    rep = []
    # RER A at Wesselman runs straight from its north piece to its south piece across D, not round D's 150 m piece
    for m in C['rer']:
        if m['id'] == 'R-AD-700206-4341384' and 'A' in m['lines']:
            m['lines'] = [l for l in m['lines'] if l != 'A']; rep.append(('R-AD-700206-4341384', 'A taken off: A crosses D here'))
    joins, PIE = plan(C, E)
    changed = {}
    for j in joins:
        a = j['a']
        if j['kind'] == 'pair':
            b = j['b']
            cands = [z for z in (a, b) if z['free']]
            mov = j.get('mov') or min(cands, key=lambda z: (z['nl'], z['e'] == 0)); fix = b if mov is a else a
            sysn, m = PIE[mov['pid']][:2]
            if j['d'] < 20: _snap(m, mov['e'], fix['q']); how = 'snapped'
            else:
                vs, ks = _bridge(mov['q'], mov['t'], fix['q'], -fix['t']); _extend(m, mov['e'], vs, ks); how = 'joined'
            changed[m['id']] = (sysn, m); rep.append((j['ln'], how, j['d'], mov['pid'], 'start' if mov['e'] == 0 else 'end', '->', fix['pid'], 'start' if fix['e'] == 0 else 'end'))
        elif j['kind'] == 'pull':
            sysn, m = PIE[j['o']][:2]; _snap(m, j['f'], a['q']); changed[m['id']] = (sysn, m)
            rep.append((j['ln'], 'snapped', j['d'], j['o'], 'start' if j['f'] == 0 else 'end', '->', a['pid'], 'start' if a['e'] == 0 else 'end'))
        else:
            sysn, m = PIE[a['pid']][:2]
            if j['d'] < 20: _snap(m, a['e'], j['T']); how = 'snapped onto'
            else:
                if j.get('K') is not None: vs, ks = [j['T']], [j['K']]
                else: vs, ks = _bridge(a['q'], a['t'], j['T'], j['tT'])
                _extend(m, a['e'], vs, ks); how = 'joined onto'
            changed[m['id']] = (sysn, m); rep.append((j['ln'], how, j['d'], a['pid'], 'start' if a['e'] == 0 else 'end', '->', j['onto']))
    for pid, (sysn, m) in changed.items(): respread(C, m, sysn)
    for t in C['tracks']:                                               # earlier passes wrote 'RER A' / 'RER E' as the line
        if t['sys'] == 'rer' and t['line'].startswith('RER '): t['line'] = t['line'][4:]
    return rep
# ---------------------------------------------------------------- Line 5 at Pennsylvania (Ben, 24 October): the loop stub off the station is
# taken out and the two arms are one line, on a curve through the station; the platform curves east with it
L5A, L5S, L5B = 'M-L5-712097-4339800', 'M-L5-716208-4331118', 'M-L5-716208-4331118-868'
L5_S2 = 120.0                                                           # the curve takes in the drawn line's own bend just east of the station
# (its landing 120 m along the east arm: one curve, about 100 m radius at its tightest, within 3.3 m of the line as drawn)
def _l5_tail(cA, b):
    from shapely.ops import substring
    cor = np.array(cA[-1], float); u = cor - np.array(cA[-2], float); u /= np.linalg.norm(u)
    gb = M.frame(b)[0]; P2 = np.array(gb.interpolate(L5_S2).coords[0]); t = _tan_at(gb, L5_S2)
    x = np.linalg.solve(np.c_[u, -t], P2 - cor); K = cor + u * x[0]; T = float(np.linalg.norm(P2 - K)); P1 = K - u * T
    tail = np.asarray(LineString(substring(gb, L5_S2, gb.length).coords).simplify(0.1).coords)
    return P1, K, tail
def l5_edit(e, b):
    """the same change on Ben's live edit of the west arm"""
    P1, K, tail = _l5_tail(e['c'], b); n0 = len(e['c']) - 1
    k = dict(e.get('k') or {}); k[str(n0)] = M._r1([K])[0]
    return dict(e, c=e['c'][:-1] + M._r1([P1]) + M._r1(tail), k=k)
def apply_l5(C):
    byid = {m['id']: m for m in C['metro']}
    if L5B not in byid or L5A not in byid: return {'skipped': 'already one piece'}
    a, b = byid[L5A], byid[L5B]
    lat = [M.measure(*M.frame(byid[p['pid']]), p['c'])[2:4] for p in C['plats'] if p['sys'] == 'metro' and p['st'] == 'Pennsylvania' and p.get('pid') == L5A]
    lo, hi = lat[0] if lat else (-C['meta']['metro_twin']['island'] / 2, C['meta']['metro_twin']['island'] / 2)
    P1, K, tail = _l5_tail(a['c'], b); n0 = len(a['c']) - 1
    a['c'] = a['c'][:-1] + M._r1([P1]) + M._r1(tail)
    a['k'] = dict(a.get('k') or {}); a['k'][str(n0)] = M._r1([K])[0]
    C['metro'] = [m for m in C['metro'] if m['id'] not in (L5S, L5B)]
    C['tracks'] = [t for t in C['tracks'] if t.get('pid') not in (L5S, L5B)]
    C['plats'] = [p for p in C['plats'] if not (p.get('pid') in (L5A, L5S, L5B) and p['st'] == 'Pennsylvania')]
    st = next(s for s in C['stations'] if s['name'] == 'Pennsylvania' and s['line'] == 'Line 5')
    fr = M.frame(a); g = fr[0]; c = g.project(Point(st['p'])); NEW = C['meta']['metro_platform_m']
    g_, ds, Pp, nr = fr; sel = (ds >= c - NEW / 2) & (ds <= c + NEW / 2); Q, Nn = Pp[sel], nr[sel]
    from shapely.geometry import Polygon
    ring = M._r1(np.asarray(Polygon(np.r_[Q + Nn * hi, (Q + Nn * lo)[::-1]]).simplify(0.2).exterior.coords))
    cen = np.mean(ring[:-1], axis=0)
    C['plats'].append(dict(sys='metro', line='Line 5', pid=L5A, st='Pennsylvania', id=f'P-M-L5-{int(cen[0])}-{int(cen[1])}', c=ring))
    respread(C, a, 'metro')
    return dict(P1=M._r1([P1])[0], K=M._r1([K])[0], P2=M._r1(tail[:1])[0], platform_arc=[round(c - NEW / 2, 1), round(c + NEW / 2, 1)], lat=[round(lo, 2), round(hi, 2)])
