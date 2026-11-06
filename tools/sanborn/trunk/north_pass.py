try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# North trunk, option 3 (Ben, 25 October 2026): installs trunk/plan.py's layout into context.json (RER B, B/D, D) and tracks.json
# (ORR, Transvalley, APEx north of Ludlow, the Norwood branch, ORR X2). Hooked at the end of rer1023/apply.py: apply(C, T).
import json, sys, numpy as np
from shapely.geometry import LineString, Point, Polygon
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'trunk'); sys.path.insert(0, _ws.CODE + 'rer1023')
import plan as P
from plan import G, FN, FE, NTF, bl, pw, shift_west, frame_s, s_of, nt_at, nt_e, ss_
import frames as FR
import metro400 as M

def r1(a): return [[round(float(x), 1), round(float(y), 1)] for x, y in a]
def r2(a): return [[round(float(x), 2), round(float(y), 2)] for x, y in a]
def simp(a, tol=0.05): return np.asarray(LineString(a).simplify(tol).coords)
def trunk_line(fn, s0, s1, F=FN):
    """offset line from s0 to s1 (s0 < s1): geom27's NT south of S_L, frame F north of it, then the westward bend"""
    parts = []
    if s0 < P.S_L: parts.append(P.south(fn, s0, min(s1, P.S_L)))
    if s1 > P.S_L: parts.append(P.north(F, fn, max(s0, P.S_L), s1))
    Q = parts[0] if len(parts) == 1 else np.vstack([parts[0], parts[1][1:] if np.hypot(*(parts[0][-1] - parts[1][0])) < 0.5 else parts[1]])
    return shift_west(Q, F)
def band(F, s0, s1, lo, hi):
    ss = np.arange(s0, s1 + 1e-6, 2.0)
    if F is NTF: a = NTF.at(ss, lo); b = NTF.at(ss, hi)
    else: a = F.at(ss, np.full(ss.shape, lo)); b = F.at(ss, np.full(ss.shape, hi))
    ring = np.vstack([shift_west(a, FN), shift_west(b, FN)[::-1]]); ring = np.vstack([ring, ring[:1]])
    return np.asarray(Polygon(ring).simplify(0.1).exterior.coords)
def feat(layer, c, **p): return dict(type='Feature', properties=dict(layer=layer, **p), geometry=dict(type='LineString', coordinates=r2(c)))
def pt(layer, xy, **p): return dict(type='Feature', properties=dict(layer=layer, **p), geometry=dict(type='Point', coordinates=[round(float(xy[0]), 1), round(float(xy[1]), 1)]))
def fpt(F, s, o): return shift_west(F.at(s, o), FN)[0]

def apply(C, T):
    rep = {}
    TF = T['features']
    byname = {}
    for f in TF: byname.setdefault(f['properties'].get('name') or '', []).append(f)
    # ------------------------------------------------------------ tracks.json
    # 1. the v124 viaduct tracks that stay (APEx 1-4, Transvalley/R5 pair): the westward bend at their north ends
    for nm in [f'APEx north approach {j} of 6' for j in (1, 2, 3, 4)] + [f'Lower-level pair W, track {k}, on the viaduct' for k in (1, 2)]:
        f = byname[nm][0]; f['geometry']['coordinates'] = r2(shift_west(np.array(f['geometry']['coordinates'])[:, :2], FN))
    # 2. ORR (lower pair E) on the viaduct: beside the APEx from Marshall, in to 9 / 13.5 after Arlington
    for k in (0, 1):
        f = byname[f'Lower-level pair E, track {k + 1}, on the viaduct'][0]; c = np.array(f['geometry']['coordinates'])[:, :2]
        keep = c[np.array([s_of(q) for q in c]) < G.S_MAR]
        c2 = trunk_line(P.o_orr(k), G.S_MAR, P.S_L)
        f['geometry']['coordinates'] = r2(np.vstack([keep, c2]))
        f['properties']['note'] = ('ORR/intercity (E-H): beside the APEx from Marshall (no longer 22 m further east from Camp Washington), in beside the APEx '
                                   'Norwood pair north of Arlington, where RER B goes to the east edge (Ben, 25 October): on the viaduct from just north of Ludlow, '
                                   f'where the rails stand {G.Z_LUD:.1f} m over Ludlow Avenue at ground on its 1914 line (fill north of there), to Bank')
    # 3. out: the v124 trunk north of Ludlow, the region lines from the split, the old crossovers
    drop = lambda n: (n.startswith('APEx Southwest Chief') or n.startswith('Crossover 1:46 (north trunk') or n.startswith('turnout (north trunk'))
    T['features'] = TF = [f for f in TF if not drop(f['properties'].get('name') or '')]
    # the Transcontinental from Norwood Central's west throat east only (the branch to it is drawn below)
    for f in TF:
        nm = f['properties'].get('name') or ''
        if nm.startswith('APEx Transcontinental Limited ('):
            c = np.array(f['geometry']['coordinates'])[:, :2]; so = np.array([FR.nw_so(q)[0] for q in c]); i = int(np.argmax(so >= FR.S_NW))
            a, b = c[i - 1], c[i]; t = (FR.S_NW - so[i - 1]) / (so[i] - so[i - 1]); cut = a + (b - a) * t
            f['geometry']['coordinates'] = r2(np.vstack([cut, c[i:]]))
            f['properties']['note'] = (f['properties'].get('note') or '') + ' From Norwood Central\'s west throat east; west of it, the Norwood branch (2026-10-25).'
    # 4. north of Ludlow
    ends = {}
    FEND = FE.s[-1]
    def tv(k): return lambda s: np.where(np.asarray(s) < P.S_TV1, P.o_tv(k)(s), P.o_tv_e(k)(s))
    new = []
    lvl_n = (f'fill from Ludlow ({G.Z_LUD:.1f} m, level through the RER B Northside / Spring Grove platforms, {100 * G.G_NFILL:.1f}% down to ground at s {P.S_FILL1:,.0f}), '
             'then at ground')
    for k in (0, 1):
        new.append(feat('apex', trunk_line(P.o_ad(k), P.S_L, FN.s[-1], FN), name=f'APEx Dayton (Southwest Chief), track {k + 1} of 2', kind='region', level='0',
                        note=f'West pair of the four APEx tracks from CUT; {lvl_n}. Moves 13.5 m west under the Transvalley flyover (s {P.S_AD0:,.0f}-{P.S_AD1:,.0f}), '
                             f'leaves the KMZ line at s {P.S_TC:,.0f} on a 1,000 m curve onto the Southwest Chief straight (APEx Routes.kmz line, Vandalia-Cincinnati), and closes up to it '
                             'once the Norwood tracks have gone. Track spacing is a drawing value'))
        new.append(feat('apex', trunk_line(P.o_an(k), P.S_L, FEND, FE), name=f'APEx Norwood (Transcontinental), track {k + 1} of 2', kind='region', level='0',
                        note=f'East pair of the four APEx tracks from CUT; {lvl_n}. Carries straight on at the split along the Transcontinental (APEx Routes.kmz, St Bernard-Norwood) to '
                             'Norwood Central\'s through tracks (T7, T6). Track spacing is a drawing value'))
        new.append(feat('lower', trunk_line(tv(k), P.S_L, FEND, FE), name=f'Transvalley, track {k + 1} of 2 (Ludlow to Norwood Central)', level='0', state='surface',
                        note=f'The west pair from the viaduct (R5 has left it at the Cumminsville spur). On the fill north of Ludlow it holds {P.Z_TV_HOLD:.1f} m while the trunk comes '
                             f'down, crosses over the APEx Dayton pair (s {P.S_TV0:,.0f}-{P.S_TV1:,.0f}, 8.7 m or more rail to rail), then falls 2.5% to ground by about s 6,720, '
                             'between the two APEx pairs. Along the Norwood branch north of the APEx (Norwood Central T10, T9)'))
        new.append(feat('lower', trunk_line(P.o_orr_e(k), P.S_L, FEND, FE), name=f'ORR, track {k + 1} of 2 (Ludlow to Norwood Central)', level='0', state='surface',
                        note=f'ORR X1, R1, R2, R3, L71, L75 beside the APEx Norwood pair; {lvl_n}. X2 turns off for the Mill Creek after Mitchell Ave; the rest run along the '
                             'Norwood branch south of the APEx (Norwood Central T4, T2)'))
    # ORR X2: from ORR after the Mitchell Ave station, east of it, climbing with RER B over the Norwood tracks, then north beside the Dayton line
    yN = 4339800.0
    s_win = next(float(s) for s in np.arange(9000, FN.s[-1], 2.0) if FN.at(s, 11.25)[0][1] >= yN)
    for k in (0, 1):
        new.append(feat('lower', trunk_line(P.o_x2(k), P.S_X0, s_win, FN), name=f'ORR X2, track {k + 1} of 2 (Mill Creek)', level='0', state='surface',
                        note=(f'Leaves ORR at s {P.S_X0:,.0f}-{P.S_X1:,.0f} after the Mitchell Ave station; ' + ('the southbound track crosses ORR northbound on the level (one flat crossing, '
                              'about two X2 trains an hour); ' if k == 0 else '') + f'climbs 2.5% beside RER B from s {P.S_BU:,.0f} to {P.CLR_APX:.1f} m over the Norwood tracks '
                              f'(s {P.S_BX0:,.0f}-{P.S_BX1:,.0f}), down by s {P.S_BD:,.0f}, then north beside the Dayton line (east of it). Drawn to the RER window edge (N 4,339,800); '
                              'its route up the Mill Creek beyond is not drawn')))
    # crossovers: one set per APEx line, where the old pair stood (1:46, 160 km/h)
    for (F, fn, nm) in ((FN, P.o_ad, 'APEx Dayton'), (FE, P.o_an, 'APEx Norwood')):
        for s0, s1, a, b in ((6960, 7168, 0, 1), (7210, 7418, 1, 0)):
            oa, ob = fn(a), fn(b)
            fo = (lambda oa, ob, s0, s1: (lambda s: bl(s, s0, s1, 0, 1) * (ob(s) - oa(s)) + oa(s)))(oa, ob, s0, s1)
            c = trunk_line(fo, s0, s1, F)
            new.append(feat('apex', c, name=f'Crossover 1:46 ({nm}, north trunk)', kind='crossover', num=46, kmh=160, level='0'))
            for q in (c[0], c[-1]): new.append(pt('marker', q, kind='switch', sw='turnout', num=46, kmh=160, label='', name=f'turnout ({nm}, north trunk)'))
    TF.extend(new)
    # markers
    mk = []
    mk.append(pt('marker', fpt(FE, 6150, -16.0), kind='level', anchor='left', name='Transvalley over APEx Dayton',
                 label=f'Transvalley over APEx Dayton, {P.Z_TV_HOLD:.1f} m (8.7 m or more over it)'))
    mk.append(pt('marker', fpt(FE, 6720, -11.25), kind='level', anchor='left', name='Transvalley at ground', label='Transvalley back at ground, between the APEx pairs'))
    mk.append(pt('marker', fpt(FE, P.S_X0 + 60, 13.5), kind='flag', anchor='right', name='X2 flat crossing', label='ORR X2 turns off: southbound X2 crosses ORR northbound on the level'))
    mk.append(pt('marker', fpt(FN, P.S_TC, -26.0), kind='level', anchor='left', name='Dayton line leaves', label='APEx Dayton leaves on a 1,000 m curve; Norwood tracks straight on'))
    mk.append(pt('marker', fpt(FE, 10200, -18.0), kind='level', anchor='left', name='Norwood branch order', label='Norwood branch, north to south: Transvalley, APEx, ORR'))
    TF.extend(mk)
    for f in TF:
        p_ = f['properties']
        if p_.get('layer') == 'label' and p_.get('text') == 'Viaduct: Transvalley/R5, APEx 4, TRI B, ORR E': p_['text'] = 'Viaduct: Transvalley/R5, APEx 4, ORR, RER B'
        if p_.get('layer') == 'label' and p_.get('text') == 'Viaduct: Transvalley/R5, APEx 6, TRI B/D, ORR E (12)': p_['text'] = 'Viaduct: Transvalley/R5, APEx 6, ORR, RER B/D (12)'
        if p_.get('name') == 'trunk fill ends':
            q = fpt(FN, P.S_FILL1, 30.0); f['geometry']['coordinates'] = [round(float(q[0]), 1), round(float(q[1]), 1)]
    # ------------------------------------------------------------ context.json: RER B, B/D, D
    RER = {r['id']: r for r in C['rer']}
    trk = lambda pid: [t for t in C['tracks'] if t.get('pid') == pid]
    # B/D: shifted 11.25 m east from s 2,460 (still in the box) to where it is 6.8 m under the viaduct, then beside ORR on the east
    def bd_shift(Q):
        Q = np.asarray(Q, float); out = Q.copy()
        for i, q in enumerate(Q):
            s = s_of(q)
            if s <= G.S_SCUT: continue
            w = float(bl(s, G.S_SCUT, G.S_SEP, 0, 1)); e = nt_e(s); out[i] = q + e * w * 11.25
        return out
    def bd_fix(c, fn):              # c north -> south (junction first); returns the new line, junction first
        c = np.asarray(c, float); s = np.array([s_of(q) for q in c])
        southpart = bd_shift(c[s < G.S_SEP])
        ss = ss_(G.S_SEP, P.S_J)[::-1]; top = nt_at(ss, fn(ss))            # north -> south
        return np.vstack([top, southpart if np.hypot(*(top[-1] - southpart[0])) > 0.3 else southpart[1:]])
    bd = RER['R-BD-712316-4334957']
    dense = M._dense(bd['c'], bd.get('k') or {}) if bd.get('k') else np.array(bd['c'], float)
    cen = lambda s: (P.o_bd(0)(s) + P.o_bd(1)(s)) / 2
    bd['c'] = r1(simp(bd_fix(dense, cen))); bd['k'] = {}
    bd['sub'] = 'B/D bored section (2026-10-12), B/D: up from the box east of ORR to the viaduct at Camp Washington, flying junction north of it (2026-10-25)'
    for t in trk('R-BD-712316-4334957'):
        if t.get('name', '').startswith('RER B/D southbound'): t['c'] = r1(simp(bd_fix(t['c'], P.o_bd(0)), 0.02))
        elif t.get('name', '').startswith('RER B/D northbound'): t['c'] = r1(simp(bd_fix(t['c'], P.o_bd(1)), 0.02))
    # B, junction to Ludlow (piece R-B-712689-4336858), Ludlow to the split (R-B-715612-4338596), on to the window (R-B-716551-4339800), beyond
    def bcen(s): s = np.asarray(s, float); return np.where(s < 8500, (P.o_b(0)(s) + P.o_b(1)(s)) / 2, (P.o_b_north(0)(s) + P.o_b_north(1)(s)) / 2)
    def btr(k): return lambda s: np.where(np.asarray(s) < 8500, P.o_b(k)(s), P.o_b_north(k)(s))
    s_b1 = FN.proj(RER['R-B-712689-4336858']['c'][0]); s_b2 = FN.proj(RER['R-B-715612-4338596']['c'][0])
    s_bw = next(float(s) for s in np.arange(9000, FN.s[-1], 2.0) if FN.at(s, 22.5)[0][1] >= yN)
    rep['b_bounds'] = [round(P.S_J), round(s_b1), round(s_b2), round(s_bw)]
    def bpiece(pid, s0, s1, sub, step_simplify=0.05):
        r = RER[pid]; c = trunk_line(bcen, s0, s1, FN)[::-1]; r['c'] = r1(simp(c, step_simplify)); r['k'] = {}; r.pop('curves', None); r['sub'] = sub
        tt = trk(pid)
        newt = [trunk_line(btr(k), s0, s1, FN)[::-1] for k in (0, 1)]
        for t, c2 in zip(tt, newt): t['c'] = r1(simp(c2, 0.02))
        return r
    bpiece('R-B-712689-4336858', P.S_J, s_b1, 'B on the viaduct from the B/D junction to Ludlow, east edge (Ben, 25 October: option 3)')
    bpiece('R-B-715612-4338596', s_b1, s_b2, 'RER Mill Creek trunk north of Ludlow: east edge, over the Norwood tracks at the split (2026-10-25)')
    bpiece('R-B-716551-4339800', s_b2, s_bw, 'Cincinnati-Dayton: east of ORR X2 and the Dayton line (2026-10-25)')
    r = RER['R-B-721053-4347000']; c = FN.at(np.arange(s_bw, FN.s[-1] + 1e-6, 4.0), 22.5)[::-1]; r['c'] = r1(simp(c, 0.3)); r['k'] = {}; r.pop('curves', None)
    r['sub'] = 'Cincinnati-Dayton, outside the plan window: beside the APEx Southwest Chief line (KMZ line as drawn, set 22.5 m east of it, 2026-10-25)'
    for t, k in zip(trk('R-B-721053-4347000'), (0, 1)): t['c'] = r1(simp(FN.at(np.arange(s_bw, FN.s[-1] + 1e-6, 4.0), (20.25, 24.75)[k])[::-1], 0.3))
    # D: the trunk part from the junction (climbing, over southbound B, then over ORR at 174.3 m) to the Indianapolis curve; west of it unchanged
    d = RER['R-D-710306-4337028']
    def d_join(c, fn):              # c west -> junction
        c = np.asarray(c, float); keep = [q for q in c if s_of(q) >= G.S_C - 60 or G.NTL.distance(Point(q)) > 60]
        keep = np.array(keep); i = int(np.argmin([abs(s_of(q) - (G.S_C - 60)) if G.NTL.distance(Point(q)) < 60 else 1e9 for q in keep]))
        ss = ss_(P.S_J, G.S_C - 60)[::-1]; top = nt_at(ss, fn(ss))                         # north -> south
        return np.vstack([keep[:i + 1], top[1:]])
    dd = M._dense(d['c'], d.get('k') or {}) if d.get('k') else np.array(d['c'], float)
    dc = lambda s: (P.o_d(0)(s) + P.o_d(1)(s)) / 2
    d['c'] = r1(simp(d_join(dd, dc))); d['k'] = {}; d.pop('curves', None)
    d['sub'] = 'D with the Indianapolis pair; flying junction north of Camp Washington: climbs 2.5% from the junction, over southbound B and ORR (2026-10-25)'
    tt = trk('R-D-710306-4337028')
    def d_off(t): q = np.array(t['c']); s = np.array([s_of(x) for x in q]); i = int(np.argmin(np.abs(s - 3880))); return float((q[i] - nt_at(s[i])[0]) @ nt_e(s[i]))
    for t in tt:
        k = 0 if d_off(t) < 18.0 else 1
        t['c'] = r1(simp(d_join(t['c'], P.o_d(k)), 0.02))
    # platforms
    PL = {p.get('st'): p for p in C['plats'] if p['sys'] == 'rer' and p.get('pid') in ('R-BD-712316-4334957', 'R-B-712689-4336858', 'R-B-715612-4338596', 'R-B-716551-4339800')}
    def setplat(st, F, s0, s1, lo, hi, pid=None):
        p = PL[st]; ring = band(F, s0, s1, lo, hi); p['c'] = r1(ring)
        if pid: p['pid'] = pid
        cxy = Polygon(ring).centroid; return [round(cxy.x, 1), round(cxy.y, 1)]
    stp = {}
    stp['Camp Washington'] = setplat('Camp Washington', NTF, G.S_CW0, G.S_CW1, 31.0, 42.0)
    stp['Arlington'] = setplat('Arlington', NTF, P.S_AR0, P.S_AR1, 31.0, 42.0)
    stp['Northside / Spring Grove'] = setplat('Northside / Spring Grove', FN, P.S_NS0, P.S_NS1, 22.0, 33.0)
    stp['Mitchell Ave / WINTON PLACE'] = setplat('Mitchell Ave / WINTON PLACE', FN, P.S_MI0, P.S_MI1, 22.0, 33.0)
    stp['Ivorydale'] = setplat('Ivorydale', FN, P.S_IV0, P.S_IV1, 22.0, 33.0)
    for s in C['rer_stations']:
        if s['name'] in stp: s['p'] = stp[s['name']]
    rep['stations'] = stp
    # structures (RER layer: viaduct dashed, fill dotted)
    keep = [r for r in C['rer_struct'] if r['line'] not in ('B', 'B/D', 'D (with the Indianapolis pair)')]
    def cl(fn, s0, s1, F=FN): return trunk_line(fn, s0, s1, F)
    bdc = lambda s: (P.o_bd(0)(s) + P.o_bd(1)(s)) / 2
    bdline = np.asarray(bd['c'], float)[::-1]                 # south -> north
    sb = np.array([s_of(q) for q in bdline])
    def seg(a, b): return bdline[(sb >= a) & (sb <= b)]
    new_s = [dict(line='B/D', state='tunnel', c=r1(seg(G.S_SCUT, 2594))), dict(line='B/D', state='ramp', c=r1(seg(2594, G.S_CW0))),
             dict(line='B/D', state='viaduct', c=r1(seg(G.S_CW0, P.S_J)))]
    S_LUD2 = G.S_LUD + 25
    new_s += [dict(line='B', state='viaduct', c=r1(cl(bcen, P.S_J, S_LUD2))), dict(line='B', state='embankment', c=r1(cl(bcen, S_LUD2, P.S_FILL1))),
              dict(line='B', state='embankment', c=r1(cl(bcen, P.S_BU, P.S_BX0 - 40))), dict(line='B', state='viaduct', c=r1(cl(bcen, P.S_BX0 - 40, P.S_BX1 + 40))),
              dict(line='B', state='embankment', c=r1(cl(bcen, P.S_BX1 + 40, P.S_BD)))]
    dline = np.asarray(d['c'], float)[::-1]                   # junction -> west
    Ld = np.r_[0, np.cumsum(np.hypot(*np.diff(dline, axis=0).T))]
    old_d = [r for r in C['rer_struct'] if r['line'] == 'D (with the Indianapolis pair)']
    Lold = float(np.sum(np.hypot(*np.diff(np.asarray(old_d[0]['c']), axis=0).T))) if old_d else 2450.0
    s_join = float(LineString(dline).project(Point(nt_at(G.S_C - 60, 18.0)[0])))
    old_join = float(LineString(np.asarray(old_d[0]['c'])).project(Point(nt_at(G.S_C - 60, 18.0)[0]))) if old_d else 600.0
    Lnew = s_join + (Lold - old_join)
    new_s.append(dict(line='D (with the Indianapolis pair)', state='viaduct', c=r1(dline[Ld <= Lnew])))
    for r in new_s:
        c = np.asarray(r['c']); r['s0'] = 0; r['s1'] = int(round(float(np.sum(np.hypot(*np.diff(c, axis=0).T))))) if len(c) > 1 else 0
    C['rer_struct'] = keep + [r for r in new_s if len(r['c']) > 1]
    # marks
    def rm(prefix): C['rer_marks'] = [m for m in C['rer_marks'] if not m['label'].startswith(prefix)]
    for pfx in ('Camp Washington (B, D) on the viaduct', 'B/D 3.3% down from', 'D leaves B: flyover', 'Arlington (B) on the viaduct', 'B over Ludlow,', 'B over Millvale Boulevard',
                'Northside / Spring Grove (B) on the fill'):
        rm(pfx)
    def mark(xy, label, anchor='right'): C['rer_marks'].append(dict(p=[round(float(xy[0]), 1), round(float(xy[1]), 1)], label=label, anchor=anchor))
    mark(NTF.at(G.S_CWC, 47.0)[0], f'Camp Washington (B, D) on the viaduct, {G.band(G.S_CWC):.1f} m, east of ORR')
    mark(NTF.at(G.S_SEP, 37.0)[0], f'B/D 3.3% down from {G.band(G.S_CW0):.1f} m; 6.8 m under the viaduct from here (it passes under ORR in the box)')
    mark(NTF.at(P.S_J + 40, 48.0)[0], f'B/D junction: D climbs 2.5% from s {P.S_J:,.0f}; northbound D over southbound B by s 3,500 ({P.d_z(3500) - G.band(3500):.1f} m), over ORR at {G.Z_TOP:.1f} m')
    mark(NTF.at(G.S_ARC, 48.0)[0], f'Arlington (B) on the viaduct, {G.Z_AR:.1f} m, east edge')
    mark(fpt(FN, G.S_LUD, 36.0), f'B over Ludlow, {G.Z_LUD:.1f} m; Northside / Spring Grove island on the fill (level), the corridor bent {P.D_WEST:.0f} m west to clear OH-75')
    mark(fpt(FN, P.S_NS0 + 120, 40.0), f'Northside / Spring Grove (B) on the fill, {G.Z_LUD:.1f} m')
    mark(fpt(FN, P.S_MI, 40.0), 'Mitchell Ave / Winton Place (B) at ground, east edge')
    mark(fpt(FN, P.S_BU + 60, 42.0), f'B and ORR X2 climb {100 * P.G_UP:.1f}% from s {P.S_BU:,.0f}')
    mark(fpt(FN, (P.S_BX0 + P.S_BX1) / 2, 30.0), f'B and X2 {P.CLR_APX:.1f} m over the Norwood tracks (APEx, ORR, Transvalley)')
    mark(fpt(FN, P.S_BD, 30.0), f'B and X2 back at ground, s {P.S_BD:,.0f}')
    # B over Millvale Boulevard (recomputed on the new line)
    HW = json.load(open(SP + 'hwy/data.json')); HO = HW['origin']
    mv = LineString([(x_ + HO[0], y_ + HO[1]) for x_, y_ in next(q for q in HW['segs'] if q['r'] == 'OH-75' and q['a'] == 19.4 and q['t'] == 'Boulevard')['c']])
    xb = LineString(RER['R-B-712689-4336858']['c']).intersection(mv)
    if not xb.is_empty:
        xb = xb if xb.geom_type == 'Point' else list(xb.geoms)[0]; zb = G.band(s_of((xb.x, xb.y)))
        mark((xb.x, xb.y), f'B over Millvale Boulevard, rail about {zb:.1f} m (ground {P.ground((xb.x, xb.y)):.1f} m)', 'left')
    rep['s'] = dict(S_J=P.S_J, S_MI=round(P.S_MI), S_IV=round(P.S_IV), S_X0=round(P.S_X0), S_BU=P.S_BU, S_BD=P.S_BD, S_FILL1=P.S_FILL1, s_win=round(s_win))
    return rep

def edit_fix(e):
    """Ben's live edit of the B/D piece (deck/layout transit): the same change north of s 2,460 (his edit matches the drawn piece there)"""
    dense = M._dense(e['c'], e.get('k') or {}) if e.get('k') else np.array(e['c'], float)
    s = np.array([s_of(q) for q in dense]); south_i = np.where(s < G.S_SCUT)[0]
    cen = lambda s: (P.o_bd(0)(s) + P.o_bd(1)(s)) / 2
    # keep his vertices (and curves) south of s 2,460 untouched; redraw north of it as a polyline
    V = np.asarray(e['c'], float); sv = np.array([s_of(q) for q in V]); first = int(np.argmax(sv < G.S_SCUT))
    north_part = dense[s >= G.S_SCUT]
    def bd_shift(Q):
        out = Q.copy()
        for i, q in enumerate(Q):
            sq = s_of(q); w = float(bl(sq, G.S_SCUT, G.S_SEP, 0, 1)); ee = nt_e(sq); out[i] = q + ee * w * 11.25
        return out
    sn = np.array([s_of(q) for q in north_part])
    ss = ss_(G.S_SEP, P.S_J)[::-1]; top = nt_at(ss, cen(ss)); mid = bd_shift(north_part[sn < G.S_SEP])
    newnorth = simp(np.vstack([top, mid]), 0.05)
    k = {str(int(i) - first + len(newnorth)): v for i, v in (e.get('k') or {}).items() if int(i) >= first}
    return dict(e, c=r1(newnorth) + [list(map(float, q)) for q in V[first:].tolist()], k=k)
