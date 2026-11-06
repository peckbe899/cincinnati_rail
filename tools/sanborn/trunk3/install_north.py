try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Push of the north extension (Ben, 26 October 2026): from the end of the Mitchell step-outs (s 8,080) to the borders.
# Base: the published v127 data (deckpage/*_v127.json). Writes deckpage/tracks.json, context.json, basin.json.
import json, sys, copy, numpy as np
from shapely.geometry import LineString, Point, Polygon
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'trunk3')
import build as B, north as N, tv_profile as TP
Q = N.Q; FR = N.FR; G = N.G
T = json.load(open(SP + 'deckpage/tracks_v127.json')); C = json.load(open(SP + 'deckpage/context_v127.json')); BJ = json.load(open(SP + 'deckpage/basin_v127.json'))
L = B.build('B'); META = L['_meta']; FB = L['_FB']
F = T['features']; rep = {}
def r1(a): return [[round(float(x), 1), round(float(y), 1)] for x, y in np.asarray(a)[:, :2]]
def r2(a): return [[round(float(x), 2), round(float(y), 2)] for x, y in np.asarray(a)[:, :2]]
def dedup(a):
    a = np.asarray(a, float)[:, :2]; return a[np.r_[True, np.hypot(*np.diff(a, axis=0).T) > 0.05]]
def simp(a, tol=0.02): return np.asarray(LineString(np.asarray(a)[:, :2]).simplify(tol).coords)
def byname(n): return [i for i, f in enumerate(F) if (f['properties'].get('name') or '') == n]
def feat(layer, c, **p): return dict(type='Feature', properties=dict(layer=layer, **p), geometry=dict(type='LineString', coordinates=r2(dedup(c))))
def ptf(xy, **p): return dict(type='Feature', properties=dict(layer='marker', **p), geometry=dict(type='Point', coordinates=[round(float(xy[0]), 1), round(float(xy[1]), 1)]))
def south_part(c):
    """the installed line up to s 8,080 (south -> north order)"""
    c = np.asarray(c)[:, :2]; s = np.array([Q.TR.proj(q) for q in c]); near = np.array([LineString(Q.TR.P).distance(Point(q)) < 60 for q in c])
    return c[(s < N.S0 - 0.5) & near]
def join(a, b):
    b = np.asarray(b)
    return np.vstack([a, b[1:] if np.hypot(*(a[-1] - b[0])) < 0.3 else b])
lvl = 'fill from Ludlow (162.5 m to the Northside / Spring Grove platform end, 1.5% down to ground at about s 6,265), then at ground'
# ------------------------------------------------------------------ APEx Dayton: to the border on the ORR APEx alignment
for k in (1, 2):
    i = byname(f'APEx Dayton (Southwest Chief), track {k} of 2')[0]
    F[i]['geometry']['coordinates'] = r2(dedup(join(south_part(F[i]['geometry']['coordinates']), L[f'Dayton {k}']['c'])))
    F[i]['properties']['level'] = 'fill'
    F[i]['properties']['note'] = ('APEx Dayton (Southwest Chief); ' + lvl + '. Leaves the trunk with X2 and RER B on one %.0f m curve left from s %.0f (the end of the Mitchell step-outs) onto the '
                                  'Southwest Chief straight, then on the ORR APEx alignment (APX-4a, St Bernard-Middletown), which takes its own line through Lockland, to the border (N 4,347,000). '
                                  'Push of 26 October 2026' % (N.R_D, N.S0))
drop = set(byname('APEx Southwest Chief (1 of 2)') + byname('APEx Southwest Chief (2 of 2)'))     # the APEx Routes line through Lockland: replaced by the ORR APEx alignment
rep['sw_dropped'] = len(drop)
# ------------------------------------------------------------------ APEx Norwood: to Norwood Central's through tracks (T7, T6)
for k in (1, 2):
    i = byname(f'APEx Norwood (Transcontinental), track {k} of 2')[0]
    F[i]['geometry']['coordinates'] = r2(dedup(join(south_part(F[i]['geometry']['coordinates']), L[f'Norwood {k}']['c'])))
    F[i]['properties']['level'] = 'fill'
    F[i]['properties']['note'] = ('APEx Norwood (Transcontinental); ' + lvl + '. Straight on at the split to s %.0f, one %.0f m curve onto the Norwood Central axis (it touches the Transcontinental '
                                  'KMZ line\'s middle straight), then on the axis to the west throat (T%d). Into the trench from the TV junction east of Reading Road: 2%% down to %.1f m under the '
                                  'Transvalley crossing, then %.2f%% up to the platforms (about %.0f m). Push of 26 October 2026' % (N.S_NC0, N.R_N, (7, 6)[k - 1], 0, 0, N.Z_ST))
# Transcontinental east of Norwood Central: from the station's through tracks (east end, frame s 5,298, o +/-2.25 on the axis) one curve left
# onto the KMZ line's next straight (the KMZ pair sat 2.25 m north of the station's axis and ran through the station)
S_E = 5298.0
TA_, TB_ = [np.asarray(F[byname(f'APEx Transcontinental Limited ({k} of 2)')[0]]['geometry']['coordinates'])[:, :2] for k in (1, 2)]
KM = np.array(FR._mid(TA_.tolist(), TB_.tolist(), n=20000)); KMS = np.array([FR.nw_so(q)[0] for q in KM]); KML = LineString(KM)
i_a = int(np.argmin(np.abs(KMS - 5850))); i_b = int(np.argmin(np.abs(KMS - 6500)))
pK = KM[i_a]; uK = KM[i_b] - KM[i_a]; uK /= np.hypot(*uK)
pE = FR.nw_P(S_E); uE = FR.NTV
R_E, O_E, T_E = N.tangent_R(pE, uE, pK, uK, 'L')
arcE = N.arc(O_E, R_E, pE, T_E, 1.0)
dT = KML.project(Point(T_E)); s_join = dT + 150.0
rep['east'] = dict(R=round(R_E), tangent=r1([T_E])[0])
for k, side in ((1, -1), (2, 1)):           # (1 of 2) is the south track, (2 of 2) the north track
    i = byname(f'APEx Transcontinental Limited ({k} of 2)')[0]; c = np.asarray(F[i]['geometry']['coordinates'])[:, :2]
    g = LineString(c); qj = np.asarray(g.interpolate(g.project(Point(KML.interpolate(s_join).coords[0]))).coords[0])
    dj = g.project(Point(qj)); dd = np.r_[0, np.cumsum(np.hypot(*np.diff(c, axis=0).T))]
    o = 2.25 * side                         # + north = left of the eastward direction
    lane = np.array([q + (q - O_E) / np.hypot(*(q - O_E)) * (-o) for q in arcE])                 # left (north) track is the inner one
    straight = np.array([T_E + uK * x + np.array([-uK[1], uK[0]]) * o for x in np.arange(2.0, s_join - dT, 2.0)])
    newc = np.vstack([FR.nw_P(S_E, o), lane[1:], straight, qj, c[dd > dj + 0.5]])
    F[i]['geometry']['coordinates'] = r2(dedup(newc))
    F[i]['properties']['note'] = (F[i]['properties'].get('note') or '') + (' From the east end of Norwood Central\'s APEx through tracks (T%d), one %.0f m curve onto the KMZ line\'s straight (push of 26 October 2026).' % ((6, 7)[k - 1], R_E))
# ------------------------------------------------------------------ ORR / TV pairs
for k in (1, 2):
    i = byname(f'Lower-level pair W, track {k}, on the fill')[0]
    F[i]['geometry']['coordinates'] = r2(dedup(join(south_part(F[i]['geometry']['coordinates']), L[f'X2 {k}']['c'])))
    F[i]['properties']['note'] = ('ORR / Transvalley west pair (ORR X2; R5 has left it): on the trunk fill and at ground past Mitchell Ave, then with RER B and APEx Dayton on one curve left onto the '
                                  'Southwest Chief straight, west of RER B; steps out round the RER B island at Ivorydale as at Mitchell. Drawn to the plan window edge (N 4,339,800). Push of 26 October 2026')
    i = byname(f'Lower-level pair E, track {k}, on the fill')[0]
    F[i]['geometry']['coordinates'] = r2(dedup(join(south_part(F[i]['geometry']['coordinates']), L[f'ORR {k}']['c'])))
    F[i]['properties']['note'] = ('ORR / Transvalley east pair (shared): on the trunk fill and at ground past Mitchell Ave, then south of APEx Norwood on the Norwood branch (4.5 m, compact) to the TV '
                                  'junction east of Reading Road (Aloysius); ORR on from there into the trench with APEx, under the Transvalley crossing, then one S out to the station\'s 8.25 m gap '
                                  '(Norwood Central T%s). Push of 26 October 2026' % ('4' if k == 1 else '2'))
z = TP.profiles('B', np.arange(2900, 4201, 5.0))
for k, nm in ((1, 'TV 1 (inbound, T10)'), (2, 'TV 2 (outbound, T9)')):
    F.append(feat('lower', L[nm]['c'], name=f'Transvalley, track {k} of 2 (Aloysius to Norwood Central)', level='ground', state='surface',
                  note=('Transvalley off the shared ORR / TV pair east of Reading Road (Aloysius), to the south (' + ('the inbound track crosses ORR outbound on the level; ' if k == 1 else '') +
                        'south of ORR, then over ORR and APEx at ground on one pair of %.0f m curves (7.3 m or more over them, s %.0f-%.0f on the Norwood frame), landing north of APEx onto '
                        'Norwood Central %s. It stays on the railway formation (about %.1f m at Section Avenue, which has to rise about 4 m over it), then comes down to the platforms. '
                        'Push of 26 October 2026') % (B.TV['B']['R'], z['xa'], z['xb'], 'T10' if k == 1 else 'T9', float(np.interp(3939, np.arange(2900, 4201, 5.0), z['tv'])))))
for i in byname('APEx Norwood (Transcontinental), track 1 of 2') + byname('APEx Norwood (Transcontinental), track 2 of 2'):
    n = F[i]['properties']['note']; F[i]['properties']['note'] = n.replace('to 0.0 m', 'to %.1f m' % z['z_low']).replace('then 0.00% up', 'then %.2f%% up' % z['g_up'])
# ------------------------------------------------------------------ markers
drop |= set(byname('North trunk drawn to here'))
def NP(s, o): return FR.nw_P(s, o)
F += [ptf(N.FD.at(N.S0 + 300, -40)[0], kind='level', anchor='left', name='West group leaves', label='ORR X2, RER B and APEx Dayton: one curve left (Dayton %.0f m) onto the Southwest Chief' % N.R_D),
      ptf(N.FW.at(N.S_NC0, 30)[0], kind='level', anchor='right', name='Norwood branch curve', label='APEx Norwood and ORR / TV: one %.0f m curve onto the Norwood axis' % N.R_N),
      ptf(NP(3150, -30), kind='flag', anchor='left', name='TV junction', label='TV off the shared pair to the south; TV inbound crosses ORR outbound on the level'),
      ptf(NP(3260, 22), kind='level', anchor='right', name='Norwood trench', label='ORR and APEx into the trench: 2%% down to %.1f m, %.2f%% up to the platforms' % (z['z_low'], 100 * z['g_up'])),
      ptf(NP((z['xa'] + z['xb']) / 2, 26), kind='level', anchor='right', name='TV over ORR and APEx', label='Transvalley over ORR and APEx at ground, 7.3 m or more'),
      ptf(N.FD.at(N.S_DT + 500, 25)[0], kind='flag', anchor='right', name='X2 drawn to here', label='ORR X2 drawn to the plan window edge')]
T['features'] = [f for i, f in enumerate(F) if i not in drop]
# ------------------------------------------------------------------ context: RER B
RER = {r['id']: r for r in C['rer']}
def trk(pid): return [t for t in C['tracks'] if t.get('pid') == pid]
def side_sort(tt, ref):
    g = LineString(ref)
    def o(t):
        q = np.asarray(t['c'])[len(t['c']) // 2]; d = g.project(Point(q)); a = np.array(g.interpolate(d).coords[0]); b = np.array(g.interpolate(min(d + 2, g.length)).coords[0]); u = (b - a) / np.hypot(*(b - a))
        return float((q - a) @ np.array([u[1], -u[0]]))
    return sorted(tt, key=o)
bc = L['B centre']['c']; bsb, bnb = L['B SB']['c'], L['B NB']['c']
def cut_y(c, y0, y1):
    c = np.asarray(c); g = LineString(c)
    def at_y(y):
        for a, b in zip(c[:-1], c[1:]):
            if (a[1] - y) * (b[1] - y) <= 0 and a[1] != b[1]: t = (y - a[1]) / (b[1] - a[1]); return a + (b - a) * t
        return None
    pa = c[0] if y0 is None else at_y(y0); pb = c[-1] if y1 is None else at_y(y1)
    pa = c[0] if pa is None else pa; pb = c[-1] if pb is None else pb
    da, db = g.project(Point(pa)), g.project(Point(pb)); d = np.r_[0, np.cumsum(np.hypot(*np.diff(c, axis=0).T))]
    return np.vstack([pa, c[(d > da + 0.05) & (d < db - 0.05)], pb])
# 1. R-B-715612 (Ludlow -> split): ends at s 8,080
r = RER['R-B-715612-4338596']; old = np.asarray(r['c'])[::-1]                   # south -> north
keep = old[np.array([Q.TR.proj(q) for q in old]) < N.S0 - 0.5]
r['c'] = r1(simp(np.vstack([keep, bc[0]]), 0.05)[::-1]); r['k'] = {}; r.pop('curves', None)
r['sub'] = 'RER Mill Creek trunk north of Ludlow: Northside / Spring Grove at the viaduct end, fill, Mitchell Ave at ground, to the split (s 8,080) (push of 26 October 2026)'
tt = side_sort(trk('R-B-715612-4338596'), keep)
for t, src in zip(tt, (bsb, bnb)):
    o = np.asarray(t['c'])[::-1]; o = o[np.array([Q.TR.proj(q) for q in o]) < N.S0 - 0.5]; t['c'] = r1(simp(np.vstack([o, src[0]]), 0.02)[::-1])
# 2. R-B-716551 (split -> plan window edge) and 3. R-B-721053 (window edge -> border)
for pid, y0, y1, sub in (('R-B-716551-4339800', None, N.Y_WIN, 'Cincinnati-Dayton: west of APEx Dayton from the split (one curve with X2 and Dayton), Ivorydale island (push of 26 October 2026)'),
                         ('R-B-721053-4347000', N.Y_WIN, 4347000.0, 'Cincinnati-Dayton, outside the plan window: west of APEx Dayton by Elmwood Place and Paddock, over APEx between Paddock and '
                          'Fairgrounds, then on its own line by Fairgrounds, Arlington Heights and Lockland/Reading while APEx takes the ORR alignment, east of APEx from about N 4,345,900 (push of 26 October 2026)')):
    r = RER[pid]; cc = cut_y(bc, y0, y1); r['c'] = r1(simp(cc, 0.05)[::-1]); r['k'] = {}; r.pop('curves', None); r['sub'] = sub
    tt = side_sort(trk(pid), cc)
    for t, src in zip(tt, (bsb, bnb)): t['c'] = r1(simp(cut_y(src, y0, y1), 0.02)[::-1])
# platforms and station points
cent = {}
pid_of = lambda nm: 'R-B-716551-4339800' if nm == 'Ivorydale' else 'R-B-721053-4347000'
for nm, sb, mode, od, ring in L['_bst']:
    for p in C['plats']:
        if p.get('st') == nm and p.get('line') == 'B':
            rg = np.asarray(Polygon(ring).simplify(0.1).exterior.coords); p['c'] = r1(rg); p['pid'] = pid_of(nm)
            cx = Polygon(rg).centroid; cent[nm] = [round(cx.x, 1), round(cx.y, 1)]
for s in C['rer_stations']:
    if 'B' in s['lines'] and s['name'] in cent and s['lines'] == ['B']: s['p'] = cent[s['name']]
rep['b_stations'] = cent
# B flyover over APEx between Paddock and Fairgrounds
gB = LineString(bc); X = gB.intersection(LineString(N.FD.P))
xp = X if X.geom_type == 'Point' else list(X.geoms)[0]; dx = gB.project(xp)
seg = np.array([gB.interpolate(d).coords[0] for d in np.arange(dx - 360, dx + 361, 4.0)])
C['rer_struct'] = [r_ for r_ in C['rer_struct'] if not (r_['line'] == 'B' and r_.get('note') == 'flyover')]
C['rer_struct'].append(dict(line='B', state='viaduct', note='flyover', c=r1(seg), s0=0, s1=720))
C['rer_marks'] = [m for m in C['rer_marks'] if not m['label'].startswith(('B over APEx Dayton', 'Ivorydale (B)'))]
C['rer_marks'].append(dict(p=[round(xp.x + 30, 1), round(xp.y, 1)], label='B over APEx Dayton (7.3 m or more), between Paddock and Fairgrounds; east of APEx from here', anchor='right'))
C['rer_marks'].append(dict(p=r1([N.FD.at(N.S_IV, -45)[0]])[0], label='Ivorydale (B) at ground, island west of APEx Dayton; X2 steps out round it', anchor='left'))
rep['b_flyover'] = [round(xp.x), round(xp.y)]
C['meta']['north_trunk'] = (C['meta'].get('north_trunk', '') + '; extension of 26 October 2026: split at s 8,080 without crossings (X2, RER B, Dayton left; Norwood, ORR/TV straight on), '
                            'Dayton on the ORR APEx alignment to the border, RER B over APEx between Paddock and Fairgrounds, Norwood branch with the TV peel and crossing to Norwood Central')
# ------------------------------------------------------------------ basin: Spring Grove Avenue west at Ivorydale
SH = json.load(open(SP + 'wh/street_shifts.json'))
for f in BJ['features']:
    if f['properties'].get('id') == 'SZ0326' and f['properties'].get('name') == SH['name']:
        f['geometry']['coordinates'] = SH['coords']; f['properties']['note'] = 'moved up to 12.5 m west through Ivorydale to clear ORR X2 round the RER B island (Ben, 26 October 2026)'; rep['street'] = 'SZ0326 moved'
json.dump(T, open(SP + 'deckpage/tracks.json', 'w'), separators=(',', ':'))
json.dump(C, open(SP + 'deckpage/context.json', 'w'), separators=(',', ':'))
json.dump(BJ, open(SP + 'deckpage/basin.json', 'w'), separators=(',', ':'))
print(json.dumps(rep, indent=1, default=str))
