try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Push of the north viaduct plan (Ben, 26 October 2026): writes deckpage/tracks.json and deckpage/context.json from the v126 copies
# (push/*_v126.json) and trunk2/geo4.py. Structures are rebuilt afterwards by cut/structures.py.
import json, sys, copy, numpy as np
from shapely.geometry import LineString, Point, Polygon
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'trunk2'); sys.path.insert(0, _ws.CODE + 'rer1023'); sys.path.insert(0, _ws.CODE + 'nv')
import geo4 as Q
from metro400 import _dense
G = Q.G
T = json.load(open(SP + 'trunk2/push/tracks_v126.json')); C = json.load(open(SP + 'trunk2/push/context_v126.json'))
DB = json.load(open(SP + 'dblive8/deck/layout.json'))
L = Q.build()
F = T['features']
def r1(a): return [[round(float(x), 1), round(float(y), 1)] for x, y in np.asarray(a)[:, :2]]
def r2(a): return [[round(float(x), 2), round(float(y), 2)] for x, y in np.asarray(a)[:, :2]]
def simp(a, tol=0.02): return np.asarray(LineString(np.asarray(a)[:, :2]).simplify(tol).coords)
def dedup(a):
    a = np.asarray(a, float); keep = np.r_[True, np.hypot(*np.diff(a, axis=0).T) > 0.05]; return a[keep]
def S(q): return Q.TR.proj(q)
def clip(c, s0, s1):
    c = np.asarray(c); s = np.array([S(q) for q in c]); near = np.array([LineString(Q.TR.P).distance(Point(q)) < 80 for q in c])
    return c[((s >= s0) & (s <= s1)) | ~near] if False else c[(s >= s0) & (s <= s1)]
def byname(n): return [i for i, f in enumerate(F) if (f['properties'].get('name') or '') == n]
def feat(layer, c, **p): return dict(type='Feature', properties=dict(layer=layer, **p), geometry=dict(type='LineString', coordinates=r2(dedup(c))))
def ptf(xy, **p): return dict(type='Feature', properties=dict(layer='marker', **p), geometry=dict(type='Point', coordinates=[round(float(xy[0]), 1), round(float(xy[1]), 1)]))
def P(s, o): return Q.TR.at(s, o)[0]
S_END = 8100.0                                  # the plan's layout is drawn to here (past Mitchell); beyond it, the split is still to be laid out
S_TIP = 8600.0                                  # end of the trunk frame
p86 = Q.TR.at(S_TIP)[0]; u86 = Q.TR.tan(S_TIP); n86 = np.array([u86[1], -u86[0]])
def PX(s, o):                                   # the frame, carried straight on past its end
    s = float(s); return P(s, o) if s <= S_TIP else p86 + u86 * (s - S_TIP) + n86 * o
def bl(s, s0, s1, a, b): t = np.clip((s - s0) / (s1 - s0), 0, 1); return a + (b - a) * (1 - np.cos(np.pi * t)) / 2
def loc(q): q = np.asarray(q[:2], float); return float((q - p86) @ u86) + S_TIP, float((q - p86) @ n86)
rep = {}

# ================================================================ tracks.json
# --- APEx approach 1-6: CUT ends kept (south of s 1,100); 1-2 Indianapolis (west), 3-4 Dayton, 5-6 Norwood
ROUTE = {1: ('APEx Indy 1', 'APEx Indianapolis (Cardinal, Floridian), track 1 of 2'), 2: ('APEx Indy 2', 'APEx Indianapolis (Cardinal, Floridian), track 2 of 2'),
         3: ('APEx Dayton 1', 'APEx Dayton (Southwest Chief), track 1 of 2'), 4: ('APEx Dayton 2', 'APEx Dayton (Southwest Chief), track 2 of 2'),
         5: ('APEx Norwood 1', 'APEx Norwood (Transcontinental), track 1 of 2'), 6: ('APEx Norwood 2', 'APEx Norwood (Transcontinental), track 2 of 2')}
for j in range(1, 7):
    i = byname(f'APEx north approach {j} of 6')[0]; old = np.asarray(F[i]['geometry']['coordinates'])[:, :2]
    s_old = np.array([S(q) for q in old]); near = np.array([LineString(Q.TR.P).distance(Point(q)) < 30 for q in old])
    south = old[(s_old < 1100) & near]                          # old runs north -> south; keep its CUT end
    k, rn = ROUTE[j]; new = L[k]['c']
    if j <= 2:
        north = new[1:].copy(); cs = np.asarray(F[byname('APEx Cardinal, Floridian (%d of 2)' % j)[0]]['geometry']['coordinates'][0][:2])
        jn = int(np.argmin(np.hypot(*(north - cs).T))); north = np.vstack([north[:jn], cs])
    else: north = new[(np.array([S(q) for q in new]) > 1100) & (np.array([S(q) for q in new]) <= Q.S_NS1)]
    north = north[::-1]                                            # north -> south
    c = np.vstack([north, south]) if np.hypot(*(north[-1] - south[0])) > 0.05 else np.vstack([north, south[1:]])
    F[i]['geometry']['coordinates'] = r2(dedup(c))
    F[i]['properties']['note'] = (rn + '. ' + ('On the north viaduct beside the RER B/D tracks to s %.0f, climbing 2.5%% from s 3,644; then the upper level of the west viaduct '
                                  '(one %.0f m curve, D on its south side, R5 under it) onto the Cardinal / Floridian line at the plan window edge' % (Q.S_TC, Q.R_DEP - 2.25 if j == 1 else Q.R_DEP + 2.25)
                                  if j <= 2 else 'On the north viaduct to the Northside / Spring Grove platform end (s 5,570), then on the fill') + '. Track spacing 4.5 m (drawing value); push of 26 October 2026')
# --- north of the viaduct: Dayton and Norwood on the fill and at ground, tied into the existing lines at the split
old_reg = {k: np.asarray(F[byname(f'APEx Southwest Chief, Transcontinental Limited ({k} of 4)')[0]]['geometry']['coordinates'])[:, :2] for k in (1, 2, 3, 4)}
def on_line_at(c, s):                                       # where line c crosses the frame normal at s
    p = PX(s, 0); X = LineString(c).intersection(LineString([p - n86 * 0 + (Q.TR.at(s, -80)[0] - p) if s <= S_TIP else p - n86 * 80, (Q.TR.at(s, 80)[0]) if s <= S_TIP else p + n86 * 80]))
    if X.is_empty: return None
    return np.asarray(X.coords[0] if X.geom_type == 'Point' else list(X.geoms)[0].coords[0])
new_feats = []
SB0, SB1 = S_END, 8450.0
lvl_fill = ('fill from Ludlow: 162.5 m to the Northside / Spring Grove platform end (s 5,570), then 1.5% down to ground at about s 6,265; at ground beyond')
for j, (k, src) in enumerate((('APEx Dayton 1', 3), ('APEx Dayton 2', 2))):
    c = L[k]['c']; s = np.array([S(q) for q in c]); a = c[(s >= Q.S_NS1) & (s <= SB0)]
    o0 = (-2.25, 2.25)[j]; mid = []
    for sv in np.arange(SB0 + 5, SB1, 5.0):
        q = on_line_at(old_reg[src], sv); w = bl(sv, SB0, SB1, 0, 1); mid.append((1 - w) * P(sv, o0) + w * q)
    oc = old_reg[src]; so = np.array([loc(q)[0] for q in oc]); rest = oc[so >= SB1]
    cc = np.vstack([a, np.array(mid), rest])
    new_feats.append(feat('apex', cc, name=f'APEx Dayton (Southwest Chief), track {j + 1} of 2', kind='region', level='fill',
                          note='West pair of the APEx Dayton / Norwood tracks; ' + lvl_fill + '. From s 8,100 it joins the existing split to the Southwest Chief line (the split is still to be laid out); push of 26 October 2026'))
TRC = {1: np.asarray(F[byname('APEx Transcontinental Limited (2 of 2)')[0]]['geometry']['coordinates'])[:, :2], 2: np.asarray(F[byname('APEx Transcontinental Limited (1 of 2)')[0]]['geometry']['coordinates'])[:, :2]}
for j, k in enumerate(('APEx Norwood 1', 'APEx Norwood 2')):
    c = L[k]['c']; s = np.array([S(q) for q in c]); a = c[(s >= Q.S_NS1) & (s <= SB0)]
    o0 = (6.75, 11.25)[j]; tgt = TRC[j + 1][0]; s_t, o_t = loc(tgt)
    mid = [PX(sv, bl(sv, SB0, s_t, o0, o_t)) for sv in np.arange(SB0 + 5, s_t, 5.0)] + [tgt]
    new_feats.append(feat('apex', np.vstack([a, np.array(mid)]), name=f'APEx Norwood (Transcontinental), track {j + 1} of 2', kind='region', level='fill',
                          note='East pair of the APEx Dayton / Norwood tracks; ' + lvl_fill + '. From s 8,100 it runs on to the Transcontinental line (the split is still to be laid out); push of 26 October 2026'))
rep['tie'] = dict(norwood_targets=[[round(x, 1) for x in loc(TRC[j][0])] for j in (1, 2)])
# --- ORR / Transvalley pairs (lower pairs W, E)
for side, nm0 in (('west', 'W'), ('east', 'E')):
    for k in (1, 2):
        i = byname(f'Lower-level pair {nm0}, track {k}, on the viaduct')[0]; c = L[f'ORR/TV {side} {k}']['c']; s = np.array([S(q) for q in c])
        via = c[(s >= 1098) & (s <= Q.S_NS1)][::-1]
        old = np.asarray(F[i]['geometry']['coordinates'])[:, :2]
        if np.hypot(*(via[-1] - old[-1])) > 0.3: via = np.vstack([via, old[-1]])
        F[i]['geometry']['coordinates'] = r2(dedup(via))
        F[i]['properties']['note'] = (('ORR / Transvalley west pair (ORR X2 and R5): tight against the APEx Indianapolis pair over the RER B/D bores and the Straight box, then out on one 620 m curve (s 2,235-2,550) beside RER B; R5 leaves it at s %.0f. '
                                       'After Arlington it moves 9 m east on one curve, holds the constant-width viaduct to the Northside / Spring Grove platform end, then comes back in on one curve' % L['R5 1']['s_on'])
                                      if side == 'west' else 'ORR / Transvalley east pair: 4.5 m east of the APEx Norwood pair from CUT to the Northside / Spring Grove platform end') + '. Push of 26 October 2026'
        fil = c[(s >= Q.S_NS1) & (s <= S_END)]
        new_feats.append(feat('lower', fil, name=f'Lower-level pair {nm0}, track {k}, on the fill', level='fill', state='surface',
                              note='ORR / Transvalley ' + side + ' pair on the trunk fill and at ground past Mitchell Ave; drawn to s 8,100, where the split is still to be laid out. Push of 26 October 2026'))
# --- R5: from the west pair under the deck (lower level), off it on one 212 m curve, single track into the South Cumminsville centre track
i_w, i_e = byname('R5 to the Cumminsville Spur (west track)')[0], byname('R5 to the Cumminsville Spur (east track)')[0]
v5 = np.asarray(F[i_w]['geometry']['coordinates'])[:, :2]; E5 = v5[-1]; u2 = v5[-1] - v5[-4]; u2 /= np.hypot(*u2); nE = np.array([u2[1], -u2[0]])
arc5, tail5 = Q.dep_path(4.5); cen5 = np.vstack([arc5, tail5]); d5 = np.r_[0, np.cumsum(np.hypot(*np.diff(cen5, axis=0).T))]
R5R = 212.0; i0 = None; bestf = 1e9
for i in range(10, len(cen5) - 10):
    p = cen5[i]; t = cen5[i + 3] - cen5[i - 3]; t /= np.hypot(*t); nr = np.array([t[1], -t[0]]); O = p + nr * R5R
    f = abs((O - E5) @ nE - R5R)
    if f < 1.0 and ((O - nE * R5R) - E5) @ u2 <= 0 and f < bestf: bestf = f; i0 = i; O5 = O
rep_r5f = bestf
B5 = O5 - nE * R5R; arcR5 = Q._arc(O5, R5R, cen5[i0], B5)
single = np.vstack([arcR5, np.array([B5 + u2 * x for x in np.arange(2.0, float((E5 - B5) @ u2), 2.0)] + [E5])])
CONV = 80.0                                    # the two tracks come together over 80 m before the curve (turnout)
for nm_, key, dk in (('west', 'R5 1', 6.75), ('east', 'R5 2', 2.25)):
    c = L[key]['c']; g = LineString(c); dc = np.r_[0, np.cumsum(np.hypot(*np.diff(c, axis=0).T))]
    # this track's own path up to CONV before the curve start, then blend onto the centre path
    pj = cen5[i0]; sj = g.project(Point(pj)); a = c[dc < sj - CONV]
    blend = []
    for x in np.arange(sj - CONV, sj, 2.0):
        q = np.asarray(g.interpolate(x).coords[0]); qc = cen5[int(np.argmin(np.hypot(*(cen5 - q).T)))]; w = bl(x, sj - CONV, sj, 0, 1); blend.append((1 - w) * q + w * qc)
    cc = np.vstack([a, np.array(blend), single])
    i_ = i_w if nm_ == 'west' else i_e
    F[i_]['geometry']['coordinates'] = r2(dedup(cc))
    F[i_]['properties']['level'] = '167.0 m on the RER A viaduct at South Cumminsville; leaves the west pair at %.1f m' % G.band(L[key]['s_on'])
    F[i_]['properties']['note'] = ('ORR R5 leaves the ORR / Transvalley west pair at s %.0f on a 600 m curve (the northbound track crosses the west pair\'s southbound track on the level), and runs on the lower level under the '
                                   'Indianapolis + D deck across the Millvale grid. Where the deck crosses RER A it comes together to single track and leaves the deck on a %.0f m curve, crosses the northbound RER A track at grade '
                                   'and joins the centre (passing) track at South Cumminsville; north of the station it runs on the RER-1b tracks (Northside-Northgate) in the gaps between RER A trains. Push of 26 October 2026' % (L[key]['s_on'], R5R))
rep['r5'] = dict(leave_deck_x=round(float(cen5[i0][0])), R=R5R)
# --- crossovers: the two north-trunk crossovers, now on the Dayton pair (1:46, 160 km/h), and their turnouts
drop = set(byname('Crossover 1:46 (north trunk, Ludlow to the Southwest Chief / Transcontinental split)') + byname('turnout (north trunk, Ludlow to the Southwest Chief / Transcontinental split)'))
drop |= set(byname(f'APEx Southwest Chief, Transcontinental Limited ({k} of 4)')[0] for k in (1, 2, 3, 4))
for s0, s1, oa, ob in ((6952.0, 7160.0, -2.25, 2.25), (7200.0, 7408.0, 2.25, -2.25)):
    ss = np.arange(s0, s1 + 0.1, 4.0); cx = Q.TR.at(ss, bl(ss, s0, s1, oa, ob))
    new_feats.append(feat('apex', cx, name='Crossover 1:46 (north trunk, APEx Dayton pair)', kind='crossover', num=46, kmh=160, level='0'))
    for q in (cx[0], cx[-1]): new_feats.append(ptf(q, kind='switch', sw='turnout', num=46, kmh=160, name='turnout (north trunk, APEx Dayton pair)', label=''))
# --- markers and labels
def setpt(name_, xy, **upd):
    for i in byname(name_): F[i]["geometry"]["coordinates"] = [round(float(xy[0]), 1), round(float(xy[1]), 1)]; F[i]['properties'].update(upd)
z_r5 = G.band(L['R5 1']['s_on'])
setpt('R5 leaves the west pair', P(L['R5 1']['s_on'], -44.0), label='R5 leaves the west pair, %.1f m; northbound R5 crosses the southbound track on the level' % z_r5, anchor='left')
setpt('Indianapolis + D leave the viaduct level, 2.5% up', P(G.S_A, 2.0), label='Indianapolis up 2.5% from here; D up 2.5% from s 3,250 (between the B tracks)')
z_tc = min(G.Z_TOP, G.sh_z(Q.S_TC))
s_top = G.S_A + (G.Z_TOP - G.band(G.S_A)) / G.G_SH
setpt('Indianapolis + D 173.1 m (6.6 m over the viaduct), west on the KMZ curve; 174.3 m from s 3,971', P(Q.S_TC, 4.0),
      name='Indianapolis + D west on one curve', label='Indianapolis + D west on one %.0f m curve from s %.0f (%.1f m); %.1f m from s %.0f; D on the south side' % (Q.R_DEP, Q.S_TC, z_tc, G.Z_TOP, s_top), anchor='right')
setpt('Ludlow: rails 162.5 m over Ludlow Avenue (at ground on its 1914 line); viaduct south to CUT, fill north', P(G.S_LUD, -40.0),
      name='Ludlow', label='Ludlow: rails 162.5 m over Ludlow Avenue (at ground on its 1914 line); the viaduct ends at the Northside / Spring Grove platform end, fill north', anchor='left')
# trunk back at ground: where the 1.5% fill meets the ground on the new line
sys.path.insert(0, _ws.CODE + 'cut'); import importlib
DMJ = json.load(open(SP + 'topo/dem2m.json')); DEM = np.load(SP + 'topo/dem2m.npy', mmap_mode='r')
def ground(p):
    r = int((DMJ['y1'] - p[1]) / 2); c_ = int((p[0] - DMJ['x0']) / 2); v = DEM[r, c_]; return None if v == DMJ['nodata'] else float(v) / 10.0
S_FILL1 = next(float(x) for x in np.arange(G.S_NSP1, 7200, 5.0) if G.north_z(x) <= (ground(P(x, 0)) or 0))
setpt('trunk fill ends', P(S_FILL1, 30.0), label='trunk back at ground, %.1f m (fill from the Northside / Spring Grove platform end)' % G.north_z(S_FILL1))
rep['S_FILL1'] = S_FILL1
for f in F:
    if f['properties'].get('layer') == 'label' and f['properties'].get('text') == 'Viaduct: Transvalley/R5, APEx 4, TRI B, ORR E':
        f['properties']['text'] = 'Viaduct: ORR/TV 2, RER B 2, APEx 4, ORR/TV 2'
    if f['properties'].get('layer') == 'label' and f['properties'].get('text') == 'Viaduct: Transvalley/R5, APEx 6, TRI B/D, ORR E (12)':
        f['properties']['text'] = 'Viaduct: ORR/TV 2, RER B/D 2, APEx 6, ORR/TV 2 (12)'
new_feats.append(ptf(P(Q.S_NS1, 34.0), kind='level', name='North viaduct ends', label='north viaduct ends at the Northside / Spring Grove platform end (s 5,570); fill north', anchor='right'))
new_feats.append(ptf(P(S_END, 30.0), kind='flag', name='North trunk drawn to here', label='ORR / Transvalley drawn to here; the split north of Mitchell Ave is still to be laid out', anchor='right'))
new_feats.append(ptf(P(2400.0, -46.0), kind='level', name='West pair over the B/D box', label='ORR / Transvalley west pair out on one 620 m curve, over the B/D box', anchor='left'))
T['features'] = [f for i, f in enumerate(F) if i not in drop] + new_feats
rep['tracks'] = dict(dropped=len(drop), added=len(new_feats))

# ================================================================ context.json
RER = {r['id']: r for r in C['rer']}
def trk(pid): return [t for t in C['tracks'] if t.get('pid') == pid]
def mid(a, b):
    a = np.asarray(a); b = np.asarray(b); gb = LineString(b); return np.array([(q + np.asarray(gb.interpolate(gb.project(Point(q))).coords[0])) / 2 for q in a])
# --- B/D: Ben's line south of the bores (his live edit, curves included, 26 October), the twin bores, the box, the ramp, Camp Washington, to the junction
e = DB['transit']['R-BD-712316-4334957']; dense = _dense(e['c'], e.get('k') or {})
BDA, BDB = Q.BD_A, Q.BD_B
# the part of his line south of the bores' start (the long straight past Western, then his curve to CUT), south -> north order reversed later
ds = np.array([LineString(dense).project(Point(q)) for q in dense]); g_e = LineString(dense)
s_bd_a = g_e.project(Point(BDA))                               # his vertex 11: the south end of the straight
bsb, bnb = L['RER B SB']['c'], L['RER B NB']['c']               # bores then trunk-parallel (north order)
t_sb0, t_nb0 = bsb[0], bnb[0]                                  # where geo4 starts the bores (on the straight, s ~1,300)
cen_north = mid(bsb[np.array([S(q) for q in bsb]) <= Q.S_J0], bnb)  # B/D centre, bores start -> junction
s0_e = g_e.project(Point(cen_north[0]))                        # on his line
south_e = np.array([np.asarray(g_e.interpolate(x).coords[0]) for x in np.arange(s0_e + 2.0, g_e.length, 2.0)] + [dense[-1]])
cen_bd = np.vstack([cen_north[::-1], south_e])                  # north -> south (junction first)
bd = RER['R-BD-712316-4334957']; bd['c'] = r1(simp(cen_bd, 0.05)); bd['k'] = {}; bd.pop('curves', None)
bd['sub'] = ('B/D: Western-Straight twin bores (one curve each, about 4,550 m), Straight in the box under the west side, open ramp, Camp Washington on the viaduct, '
             'D peels off between the B tracks north of it (push of 26 October 2026)')
# tracks: south of the bores the pair at 4.5 m on Ben's line, opened to the Western island (slid 102 m north, his station setting, 26 October) with 40 m tapers
uBD, nBD = Q.uBD, Q.nBD
st_w = [s for s in C['rer_stations'] if s['name'] == 'Western'][0]
pW0 = np.asarray(st_w['p'], float); cW = pW0 + uBD * 102.0                 # the platform centre after his slide
gS = LineString(south_e); sW = gS.project(Point(cW)); L_PL = 204.2; TAPER = 40.0
def half(x):                                                     # half spacing x m south of the bores' start (the island spacing there), 40 m taper to the 4.5 m pair
    return 2.25 + (7.2 - 2.25) * max(0.0, 1 - x / TAPER)
def south_track(sign):                                          # sign -1 = west (SB), +1 = east (NB), relative to the northward direction
    out = []
    for x in np.arange(0.0, gS.length, 2.0):
        q = np.asarray(gS.interpolate(x).coords[0]); qa = np.asarray(gS.interpolate(max(0, x - 2)).coords[0]); qb = np.asarray(gS.interpolate(min(gS.length, x + 2)).coords[0])
        t = qa - qb; t /= np.hypot(*t) + 1e-9                      # northward tangent
        n = np.array([t[1], -t[0]]); out.append(q + n * sign * half(x))
    return np.array(out)
bdt = trk('R-BD-712316-4334957'); tmpl = copy.deepcopy(bdt[0]); tmpl.pop('name', None)
newbd = []
for sign, src, nm_ in ((-1, bsb, 'RER B/D southbound (Camp Washington, Straight, Western, CUT)'), (1, bnb, 'RER B/D northbound (CUT, Western, Straight, Camp Washington)')):
    north = src[np.array([S(q) for q in src]) <= Q.S_J0][::-1]
    so = south_track(sign)
    gap = np.hypot(*(north[-1] - so[0]))
    rep.setdefault('bd_join_gap', []).append(round(float(gap), 2))
    t = dict(tmpl); t['name'] = nm_; t['c'] = r1(simp(np.vstack([north, so]), 0.02)); newbd.append(t)
C['tracks'] = [t for t in C['tracks'] if t.get('pid') != 'R-BD-712316-4334957'] + newbd
# --- B: junction -> Ludlow piece, Ludlow -> split piece (B centre between its tracks)
s_lud_piece = S(RER['R-B-712689-4336858']['c'][0])
def side_sort(tt):
    def o(t):
        q = np.asarray(t['c'])[len(t['c']) // 2]; sq = S(q); p = Q.TR.at(sq)[0]; e = Q.TR.at(sq, 1.0)[0] - p; return float((q - p) @ e)
    return sorted(tt, key=o)                                    # west (southbound) first
def b_piece(pid, s0, s1, sub=None):
    sb = bsb[(np.array([S(q) for q in bsb]) >= s0) & (np.array([S(q) for q in bsb]) <= s1)]
    nb = bnb[(np.array([S(q) for q in bnb]) >= s0) & (np.array([S(q) for q in bnb]) <= s1)]
    cen = mid(sb, nb)
    r = RER[pid]; r['c'] = r1(simp(cen[::-1], 0.05)); r['k'] = {}; r.pop('curves', None)
    if sub: r['sub'] = sub
    tt = side_sort(trk(pid)); tt[0]['c'] = r1(simp(sb[::-1], 0.02)); tt[1]['c'] = r1(simp(nb[::-1], 0.02))
# north tie: B from s 8,100 to the start of the Cincinnati-Dayton piece (its existing start, beside the split)
tb = [np.asarray(t['c'])[::-1][0] for t in trk('R-B-716551-4339800')]; cb0 = np.asarray(RER['R-B-716551-4339800']['c'])[::-1][0]
s_tb, o_tb = loc(cb0)
def tie(o0, tgt):
    s_t, o_t = loc(tgt); return np.array([PX(sv, bl(sv, S_END, s_t, o0, o_t)) for sv in np.arange(S_END + 5, s_t, 5.0)] + [tgt])
# which existing Cincinnati-Dayton track is west
tbw, tbe = sorted(tb, key=lambda q: loc(q)[1])
ex_sb = tie(-11.25, tbw); ex_nb = tie(-6.75, tbe); ex_c = tie(-9.0, cb0)
b_piece('R-B-712689-4336858', Q.S_J0, s_lud_piece, sub='B on the viaduct from the B/D junction (north of Camp Washington) to Ludlow: Arlington island on the KMZ point, then one curve east and the constant-width viaduct (push of 26 October 2026)')
sb2 = bsb[np.array([S(q) for q in bsb]) >= s_lud_piece]; nb2 = bnb[np.array([S(q) for q in bnb]) >= s_lud_piece]
sb2 = np.vstack([sb2[np.array([S(q) for q in sb2]) <= S_END], ex_sb]); nb2 = np.vstack([nb2[np.array([S(q) for q in nb2]) <= S_END], ex_nb])
cen2 = np.vstack([mid(sb2[:-len(ex_sb)], nb2[:-len(ex_nb)]), ex_c])
r = RER['R-B-715612-4338596']; r['c'] = r1(simp(cen2[::-1], 0.05)); r['k'] = {}; r.pop('curves', None)
r['sub'] = 'RER Mill Creek trunk north of Ludlow: Northside / Spring Grove at the viaduct end, fill, Mitchell Ave at ground; from s 8,100 to the existing split (still to be laid out) (push of 26 October 2026)'
tt = side_sort(trk('R-B-715612-4338596')); tt[0]['c'] = r1(simp(sb2[::-1], 0.02)); tt[1]['c'] = r1(simp(nb2[::-1], 0.02))
# --- D: junction -> between the B tracks -> one 700 m curve onto the deck curve, south of Indy -> the window edge on the KMZ line
dsb, dnb = L['RER D SB']['c'], L['RER D NB']['c']                 # junction first
cen_d = mid(dsb, dnb)
d = RER['R-D-710306-4337028']; d['c'] = r1(simp(cen_d[::-1], 0.05)); d['k'] = {}; d.pop('curves', None)
d['sub'] = 'D peels off between the B tracks north of Camp Washington, climbs 2.5% from s 3,250, joins the Indianapolis deck curve on one 700 m curve on its south side (push of 26 October 2026)'
dt = trk('R-D-710306-4337028')
def wend(t): return np.asarray(t['c'])[0]
# assign by side at the window edge: the southern (left of westward) old track becomes SB? keep order: west end first
dt.sort(key=lambda t: wend(t)[1])                              # southern first
dt[0]['c'] = r1(simp(dsb[::-1], 0.02)); dt[1]['c'] = r1(simp(dnb[::-1], 0.02))
# --- D west of the window: mirrored to the south side of the Indianapolis (Cardinal / Floridian) pair
ca, cb_ = [np.asarray(F2['geometry']['coordinates'])[:, :2] for F2 in [f for f in T['features'] if (f['properties'].get('name') or '').startswith('APEx Cardinal, Floridian (')]]
cfc = LineString(mid(ca, cb_))
def mirror(c):
    c = np.asarray(c, float); out = []
    for q in c:
        foot = np.asarray(cfc.interpolate(cfc.project(Point(q))).coords[0]); out.append(2 * foot - q)
    return np.array(out)
west_ids = ['R-D-700348-4341340', 'R-AD-700206-4341384', 'R-D-699000-4341758']
moved_ends = {}
for pid in west_ids:
    if pid not in RER: continue
    r = RER[pid]; old_c = np.asarray(r['c'], float)
    dd = [cfc.distance(Point(q)) for q in old_c]
    r['c'] = r1(mirror(old_c)); r['k'] = {}; r.pop('curves', None)
    r['sub'] = (r.get('sub') or '') + '; on the south side of the Indianapolis pair, as inside the window (push of 26 October 2026)'
    for t in trk(pid): t['c'] = r1(mirror(t['c']))
    moved_ends[pid] = (old_c[0], old_c[-1], np.asarray(r['c'][0]), np.asarray(r['c'][-1]))
    rep.setdefault('west_mirror_dist', {})[pid] = [round(min(dd), 1), round(max(dd), 1)]
# the D piece's west end and the moved piece's east end must meet: snap
d_w = np.asarray(d['c'][0]); r7 = RER['R-D-700348-4341340']; e7 = np.asarray(r7['c'][-1]); rep['d_window_gap'] = round(float(np.hypot(*(d_w - e7))), 2)
r7['c'][-1] = d['c'][0]
for t7 in trk('R-D-700348-4341340'):
    q = np.asarray(t7['c'][-1]); j = int(np.argmin([np.hypot(*(q - wend(t))) for t in dt])); t7['c'][-1] = dt[j]['c'][0]
# RER A pieces that met the moved A/D piece: move their touching vertex to its new end
for pid, (o0, o1, n0, n1) in moved_ends.items():
    for r in C['rer']:
        if r['id'] in west_ids: continue
        for ix in (0, -1):
            q = np.asarray(r['c'][ix], float)
            for oe, ne in ((o0, n0), (o1, n1)):
                if np.hypot(*(q - oe)) < 1.0: r['c'][ix] = [round(float(ne[0]), 1), round(float(ne[1]), 1)]; rep.setdefault('rer_end_moved', []).append(r['id'])
        for t in trk(r['id']):
            for ix in (0, -1):
                q = np.asarray(t['c'][ix], float)
                for oe, ne in ((o0, n0), (o1, n1)):
                    if np.hypot(*(q - oe)) < 6.0: t['c'][ix] = [round(float(ne[0] + (q - oe)[0]), 1), round(float(ne[1] + (q - oe)[1]), 1)]
# --- platforms and station points
def band_ring(s0, s1, lo, hi):
    ss = np.arange(s0, s1 + 1e-6, 2.0); lo = lo(ss) if callable(lo) else np.full(ss.shape, lo); hi = hi(ss) if callable(hi) else np.full(ss.shape, hi)
    ring = np.vstack([Q.TR.at(ss, lo), Q.TR.at(ss, hi)[::-1]]); return np.asarray(Polygon(ring).simplify(0.1).exterior.coords)
E_ = 1.75
bS, bN = Q.o_b(0), Q.o_b(1)
def blo(ss): return np.array([np.interp(S(P(s, 0)), [0, 1e9], [0, 0]) for s in ss])
def b_off(track, ss):
    g = LineString(track); out = []
    for s in ss:
        p = Q.TR.at(s)[0]; e = Q.TR.at(s, 1.0)[0] - p; X = g.intersection(LineString([p - e * 80, p + e * 80]))
        out.append(float((np.asarray(X.coords[0] if X.geom_type == 'Point' else list(X.geoms)[0].coords[0]) - p) @ e))
    return np.array(out)
PLAT = {'Straight': (Q.S_ST0, Q.S_ST1), 'Camp Washington': (Q.S_CW0, Q.S_CW1), 'Arlington': (Q.S_AR0, Q.S_AR1),
        'Northside / Spring Grove': (Q.S_NS0, Q.S_NS1), 'Mitchell Ave / WINTON PLACE': (Q.S_MI0, Q.S_MI1)}
pidof = {'Straight': 'R-BD-712316-4334957', 'Camp Washington': 'R-BD-712316-4334957', 'Arlington': 'R-B-712689-4336858',
         'Northside / Spring Grove': 'R-B-715612-4338596', 'Mitchell Ave / WINTON PLACE': 'R-B-715612-4338596'}
cent = {}
for p in C['plats']:
    st = p.get('st')
    if p['sys'] == 'rer' and st in PLAT:
        s0, s1 = PLAT[st]
        lo = lambda ss: b_off(bsb, ss) + E_; hi = lambda ss: b_off(bnb, ss) - E_
        ring = band_ring(s0, s1, lo, hi); p['c'] = r1(ring); p['pid'] = pidof[st]
        cxy = Polygon(ring).centroid; cent[st] = [round(cxy.x, 1), round(cxy.y, 1)]
    if p['sys'] == 'rer' and st == 'Western':
        ring = np.array([cW + uBD * a + nBD * b for a, b in ((-L_PL / 2, -(7.2 - E_)), (L_PL / 2, -(7.2 - E_)), (L_PL / 2, 7.2 - E_), (-L_PL / 2, 7.2 - E_), (-L_PL / 2, -(7.2 - E_)))])
        p['c'] = r1(ring); cent[st] = [round(float(cW[0]), 1), round(float(cW[1]), 1)]
for s in C['rer_stations']:
    if s['name'] in cent: s['p'] = cent[s['name']]
rep['stations'] = cent
# --- RER structures (long-section layer)
keep = [r for r in C['rer_struct'] if r['line'] not in ('B/D', 'B', 'D (with the Indianapolis pair)')]
def seg_c(c, s0, s1): c = np.asarray(c); s = np.array([S(q) for q in c]); return c[(s >= s0) & (s <= s1)]
bdc = cen_bd[::-1]                                               # south -> north
s_wn = S(cW + uBD * L_PL / 2)                                    # Western's north platform end on the frame
news = [dict(line='B/D', state='tunnel', c=seg_c(bdc[np.array([LineString(Q.TR.P).distance(Point(q)) < 120 for q in bdc])], s_wn, G.S_BOT)),
        dict(line='B/D', state='ramp', c=seg_c(bdc, G.S_BOT, G.S_CW0)), dict(line='B/D', state='viaduct', c=seg_c(bdc, G.S_CW0, Q.S_J0))]
cb_all = np.vstack([mid(bsb[(np.array([S(q) for q in bsb]) >= Q.S_J0) & (np.array([S(q) for q in bsb]) <= S_END)], bnb)])
news += [dict(line='B', state='viaduct', c=seg_c(cb_all, Q.S_J0, Q.S_NS1)), dict(line='B', state='embankment', c=seg_c(cb_all, Q.S_NS1, S_FILL1))]
news += [dict(line='D (with the Indianapolis pair)', state='viaduct', c=cen_d)]
for r in news:
    c = np.asarray(r['c']); r['c'] = r1(simp(c, 0.1)); r['s0'] = 0; r['s1'] = int(round(float(np.sum(np.hypot(*np.diff(c, axis=0).T))))) if len(c) > 1 else 0
C['rer_struct'] = keep + [r for r in news if len(r['c']) > 1]
# --- RER marks (labels)
gone = ('Camp Washington (B, D) on the viaduct', 'B/D 3.3% down from', 'B/D in a box from here', 'D leaves B: flyover', 'Arlington (B) on the viaduct', 'B over Ludlow,', 'B over Millvale Boulevard', 'Northside / Spring Grove (B) on the fill')
C['rer_marks'] = [m for m in C['rer_marks'] if not m['label'].startswith(gone)]
def mark(xy, label, anchor='right'): C['rer_marks'].append(dict(p=[round(float(xy[0]), 1), round(float(xy[1]), 1)], label=label, anchor=anchor))
mark(P(G.S_CWC, -50.0), 'Camp Washington (B, D) on the viaduct, %.1f m, west of APEx Indianapolis' % G.band(G.S_CWC), 'left')
mark(P(G.S_BOT + 60, -50.0), 'B/D 3.3%% up from the box (s %.0f, %.2f m) to the viaduct at Camp Washington; under the viaduct to s %.0f' % (G.S_BOT, G.Z_STR, G.S_SEP), 'left')
mark(P(Q.S_ST0 - 40, -50.0), 'B/D twin bores from Western, then the Straight box (%.2f m) under the west side' % G.Z_STR, 'left')
mark(P(Q.S_J0 + 60, -50.0), 'D peels off between the B tracks (no crossing) and climbs 2.5%% from s 3,250; %.1f m from s %.0f' % (G.Z_TOP, 3250 + (G.Z_TOP - G.band(3250)) / 0.025), 'left')
mark(P(G.S_ARC, 30.0), 'Arlington (B) on the viaduct, %.1f m; the Indianapolis + D deck passes over its south end' % G.Z_AR, 'right')
mark(P(G.S_LUD, -48.0), 'B over Ludlow, %.1f m; Northside / Spring Grove island at the viaduct end' % G.Z_LUD, 'left')
mark(P(Q.S_NS0 + 100, -50.0), 'Northside / Spring Grove (B) on the viaduct, %.1f m' % G.Z_LUD, 'left')
C['meta']['north_trunk'] = ('push of 26 October 2026 (claude/North_Viaduct_Plan.md): RER B/D west of APEx Indianapolis; twin bores from Western; D peels off between the B tracks; '
                            'Indianapolis + D west on one curve (D south side, R5 under); straights and single curves north of Arlington; viaduct ends at the Northside / Spring Grove platform end')
json.dump(T, open(SP + 'deckpage/tracks.json', 'w'), separators=(',', ':'))
json.dump(C, open(SP + 'deckpage/context.json', 'w'), separators=(',', ':'))
print(json.dumps(rep, indent=1, default=float))
