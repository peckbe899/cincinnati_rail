"""Metro and RER for the Mill Creek Deck page over the deck and the basin: alignments, stations, tracks and platforms.
Sources: Metro line files (Profile_Analyzer_Handoff page/lines, Ben's KMZ alignments and stations); RER pieces and stations
from Cincinnati Rail.kmz; Fountain Square RER platform lines from Ben's 'New RER A-D Platform' / 'New RER B Platform' KMZs.
Canon used: Metro platforms 400 ft (121.92 m) (Ben, 2026-10-23; was 500 ft from 2026-10-05), RER 670 ft (204.2 m) (Ben, 2026-10-05); Metro Lines 1-7 twin single-track
tubes about 8 m apart with island-platform station boxes, Lines 8-14 one double-track bore about 3.9 m track centres with
side platforms (log 10j.4). Drawing values (not canon): Metro island 8 m, side platforms 4 m, rail-to-platform-edge 1.45 m;
RER tunnel track centres 4.5 m, island 11 m, rail-to-edge 1.75 m (as the CUT lower level); 40 m tapers."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, re, collections, numpy as np
from pyproj import Transformer
from shapely.geometry import LineString, Point, box, Polygon
from shapely.ops import substring, unary_union
SP = _ws.DATA
T = Transformer.from_crs(4326, 26916, always_xy=True)
WIN = box(710300, 4329650, 716800, 4339800)   # 2026-10-13: north to Northside / South Cumminsville (was N 4335800, E 711300)
REG = box(699000, 4320800, 736900, 4347000)   # 2026-10-15 (Ben): RER out to Erlanger, CVG, Eastgate and Aviation (west edge 699,000 since 16 October: all of CVG); Metro stays in WIN
OUTER = REG.difference(WIN)
MPL, RPL = 121.92, 204.2
MET_TWIN = dict(h0=4.0, island=8.0, edge=1.45)           # tunnel half-spacing, island width, rail to edge
MET_BORE = dict(h0=1.95, side=4.0, edge=1.45)
RER = dict(h0=2.25, island=11.0, edge=1.75)
TAPER = 40.0
LETTER = {'RER-1': 'A', 'RER-2': 'B', 'RER-3': 'C', 'RER-4': 'D', 'RER-5': 'E'}
def r1(p): return [round(p[0], 1), round(p[1], 1)]
def clip(g):
    x = g.intersection(WIN)
    return [p for p in getattr(x, 'geoms', [x]) if p.geom_type == 'LineString' and p.length > 30]
# ---------------------------------------------------------------- Metro
metro, mstations = [], []
for it in json.load(open(SP + 'handoff/page/lines/index.json')):
    d = json.load(open(SP + f"handoff/page/lines/{it['id']}.json"))
    num = int(re.sub(r'\D', '', d['line']) or 0); era = 'twin' if num <= 7 else 'bore'
    g = LineString([T.transform(lon, lat) for _, lon, lat in d['path']])
    for part in clip(g): metro.append(dict(name=d['line'], era=era, g=part))
    for s in d['stations']:
        p = Point(T.transform(s['lon'], s['lat']))
        if WIN.contains(p): mstations.append(dict(name=s['name'].strip(), line=d['line'], p=p))
# ---------------------------------------------------------------- RER: pieces deduplicated (shared trunks drawn once)
pieces = []
raw = []
for line, sub, coords in json.load(open(SP + 'kmz/rer_lines.json')):
    g = LineString([T.transform(lon, lat) for lon, lat in coords])
    for part in clip(g): raw.append((LETTER[line], sub, part))
raw.sort(key=lambda t: -t[2].length)
_d = []
for let, sub, part in raw:                       # the same line drawn twice under two names (RER-1a / RER-1b)
    if any(l2 == let and part.hausdorff_distance(p2) < 5 for l2, _, p2 in _d): continue
    _d.append((let, sub, part))
raw = _d
for let, sub, part in raw:
    # a trunk drawn again under another line (same KMZ name) is the same track: split the existing piece where they coincide
    rest = part
    for q in list(pieces):
        if sub not in q['subs']: continue
        shared = q['g'].intersection(part.buffer(60))
        if shared.length < 30: continue
        pieces.remove(q)
        for g_, ls in ((shared, q['lines'] | {let}), (q['g'].difference(part.buffer(60)), q['lines'])):
            for r_ in getattr(g_, 'geoms', [g_]):
                if r_.geom_type == 'LineString' and r_.length > 100: pieces.append(dict(g=r_, lines=set(ls), subs=set(q['subs'])))
        rest = rest.difference(q['g'].buffer(60))
    for r_ in getattr(rest, 'geoms', [rest]):
        if r_.geom_type == 'LineString' and r_.length > 100: pieces.append(dict(g=r_, lines={let}, subs={sub}))
# B/D: at grade to Camp Washington, dug tunnel on the KMZ trunk to Straight, bored to Union Terminal on the best line
# (Ben, 2026-10-12): see ut_box.bd_route. The KMZ trunk is kept to the start of its bend into Straight.
import sys as _sys0; _sys0.path.insert(0, _ws.CODE + 'transit')
import ut_box as _ut0
KMZ_ST = {'Straight': (712754.5, 4334139.1)}
for q in list(pieces):
    if q['lines'] == {'B', 'D'} and 'RER-2 Trunk' in q['subs']: pieces.remove(q)
for q in pieces:
    if q['lines'] == {'B', 'D'} and 'RER Mill Creek Trunk' in q['subs']:
        g = q['g']
        pa = np.array(g.interpolate(g.project(Point(712550, 4334601))).coords[0]); pb = np.array(g.interpolate(g.project(Point(712650, 4334454))).coords[0])
        _BDR, BD_META = _ut0.bd_route(pa, float(np.arctan2(*(pb - pa)[::-1])), KMZ_ST['Straight'])
        d1 = g.project(Point(_BDR[0])); head = list(substring(g, 0, d1).coords)[:-1]
        q['g'] = LineString(head + _BDR); q['subs'] = {'RER Mill Creek Trunk', 'B/D bored section (2026-10-12)'}
        BD_G = q['g']; BD_META['kmz_kept_to_m'] = round(d1)
# ---------------------------------------------------------------- v27 north trunk (Ben, 2026-10-14; log 10za.30-10za.33, nv/geom27.py):
# B/D on the shared viaduct from Ludlow to Camp Washington (elevated), diving 3.3% south of it to Straight (box, dug), bored
# from Straight; D leaves B north of Camp Washington by a flyover (southbound D west of B, northbound D east of it and over B
# as it climbs with the Indianapolis pair) and runs with the Indianapolis pair on one deck west on the KMZ curve; Arlington (B)
# on the viaduct, centred on the KMZ point. North of Ludlow (at grade) the layout is not set: B is shown on its KMZ line.
import sys as _s27; _s27.path.insert(0, _ws.CODE + 'nv')
import geom27 as G27
from shapely.geometry import Point as _P27
_SCUT = 2460.0                                    # past Straight's north platform end (2,403) and its 40 m taper
_d = BD_G.project(_P27(G27.C.interpolate(_SCUT).coords[0]))
_bd_south = substring(BD_G, _d, BD_G.length)      # Straight and south (north -> south), drawn as before
def _cent(s): return (18.0 + np.asarray(G27.bd_track(1)(s))) / 2
def _sth(s0, s1):                                 # B/D south of s 2,758: blended from the KMZ line onto the viaduct offset
    out = []
    for s in np.arange(s0, s1 + 0.1, 3.0):
        p = np.array(BD_G.interpolate(BD_G.project(_P27(G27.C.interpolate(s).coords[0]))).coords[0]); q = np.array(G27.nt_point(s, 20.25))
        w = float(G27.blend(s, _SCUT, G27.S_SEP, 0, 1)); out.append(tuple(p * (1 - w) + q * w))
    return out
_bd_n = G27.nt_line(_cent, G27.S_SEP, G27.S_JCT) + _sth(_SCUT, G27.S_SEP)[::-1][1:]
_bd_n = G27.smooth(_bd_n, it=2, step=3.0)
BD_NEW = LineString(_bd_n + list(_bd_south.coords)[1:])
EXPL = []                                         # explicit tracks and platforms for the new north pieces
def _offline(c, d):                               # offset a north -> south centre line d m east
    g = LineString(c).offset_curve(d, quad_segs=8); cc = list(g.coords)
    return cc if Point(cc[0]).distance(Point(c[0])) < Point(cc[-1]).distance(Point(c[0])) else cc[::-1]
_sthc = G27.smooth(_sth(_SCUT, G27.S_SEP)[::-1], it=2, step=3.0)
for k, nm in ((0, 'RER B/D southbound (Straight, CUT)'), (1, 'RER B/D northbound (Camp Washington)')):
    north = G27.nt_line(G27.bd_track(k), G27.S_SEP, G27.S_JCT)
    south = _offline(_sthc, (-2.25, 2.25)[k])
    EXPL.append(dict(sys='rer', line='B D', name=nm, c=G27.smooth(north + south[1:], it=2, step=3.0)))
# B: from the split to Ludlow (s 5,300)
B_N = G27.nt_line(lambda s: (np.asarray(G27.b_track(0)(s)) + np.asarray(G27.b_track(1)(s))) / 2, G27.S_JCT, 5300.0)
for k, nm in ((0, 'RER B southbound'), (1, 'RER B northbound')):
    EXPL.append(dict(sys='rer', line='B', name=nm, c=G27.nt_line(G27.b_track(k), G27.S_JCT, 5300.0)))
# D: southbound west of B, northbound east of it, then with the Indianapolis pair
def _dtrack(d_group, d_trunk, d_start, s_settle):
    g = G27.group_track(d_group, d_trunk)
    keep = [q for q in g if G27.C.project(_P27(q)) >= s_settle or G27.NTL.distance(_P27(q)) > 60]
    pre = G27.nt_line(lambda s: G27.blend(s, G27.S_JCT, s_settle, d_start, d_trunk), G27.S_JCT, s_settle, south_first=True)
    return G27.smooth(pre + keep, it=2, step=3.0)
D_SB = _dtrack(15.75, 15.75, 18.0, 3400.0); D_NB = _dtrack(20.25, 33.75, 32.5, 3350.0); D_CL = _dtrack(18.0, 18.0, 25.25, 3400.0)
EXPL.append(dict(sys='rer', line='D', name='RER D southbound (west of B, then with the Indianapolis pair)', c=D_SB[::-1]))
EXPL.append(dict(sys='rer', line='D', name='RER D northbound (east of B, over it by s 3,924)', c=D_NB[::-1]))
def _band(c, d0, d1, s0, s1):                     # platform polygon between offsets d0..d1, chainage s0..s1
    a = G27.nt_line(lambda s: np.full(np.shape(s), d0), s0, s1); b = G27.nt_line(lambda s: np.full(np.shape(s), d1), s0, s1)
    return Polygon(a + b[::-1])
PL_NEW = [('B D', _band(None, 19.75, 30.75, G27.S_CW0, G27.S_CW1)), ('B', _band(None, 19.75, 30.75, G27.S_AR0, G27.S_AR1))]
ST_NEW = {('Camp Washington', 'B'): _P27(G27.nt_point(G27.S_CWC, 25.25)), ('Camp Washington', 'D'): _P27(G27.nt_point(G27.S_CWC, 25.25)),
          ('Arlington', 'B'): _P27(G27.nt_point(G27.S_ARC, 25.25))}
for q in list(pieces):
    if q['lines'] == {'B', 'D'} and 'RER Mill Creek Trunk' in q['subs']:
        q['g'] = BD_NEW; q['subs'] = {'B/D: viaduct to Camp Washington, dive to Straight (2026-10-14)', 'B/D bored section (2026-10-12)'}; q['split_at'] = _SCUT
    elif q['lines'] == {'B'} and 'RER Mill Creek Trunk' in q['subs']:
        g = q['g']; c = list(g.coords); c = c if c[0][1] > c[-1][1] else c[::-1]          # north -> south
        g = LineString(c); dd = g.project(_P27(G27.C.interpolate(5300.0).coords[0]))
        q['g'] = substring(g, 0, dd); q['subs'] = {'RER Mill Creek Trunk (north of Ludlow, KMZ line; at-grade layout not set)'}
    elif q['lines'] == {'D'} and 'Greensburg-CUT TRIMET' in q['subs']:
        pieces.remove(q)
pieces.append(dict(g=LineString(B_N), lines={'B'}, subs={'B on the viaduct, Camp Washington junction to Ludlow (2026-10-14)'}, explicit=True))
pieces.append(dict(g=LineString(D_CL[::-1]), lines={'D'}, subs={'D with the Indianapolis pair, flyover junction north of Camp Washington (2026-10-14)'}, explicit=True))
BD_STRUCT = [('B/D', 'tunnel', _SCUT, 2594.0), ('B/D', 'ramp', 2594.0, G27.S_CW0), ('B/D', 'viaduct', G27.S_CW0, G27.S_JCT), ('B', 'viaduct', G27.S_JCT, 5300.0)]
# RER A as designed (rera/rera.py; Ben, 2026-10-13): the KMZ trunk and Northside branch (RER-1a) with their long section, and
# the Westwood branch from its fork north of the deck edge on a 200 m curve to the platform at ground (RER-1c west of it)
RA = json.load(open(SP + 'rera/rera.json'))
pieces = [q for q in pieces if not (q['lines'] == {'A'} and q['subs'] & {'RER-1a [3:LineString]', 'RER-1a [2:LineString]', 'RER-1c'})]
for key, sub in (('A', 'RER-1a: trunk and Northside branch (long section 2026-10-13)'), ('westwood', 'Westwood branch (2026-10-13; RER-1c west of the platform)')):
    for part in clip(LineString(RA['lines'][key])): pieces.append(dict(g=part, lines={'A'}, subs={sub}))
# ---------------------------------------------------------------- 2026-10-15: outside the plan window, the KMZ RER pieces as drawn
# (shared trunks once, as above), with their stations, tracks and platforms; inside it everything stays as designed.
def _dedupe(raw_):
    raw_ = sorted(raw_, key=lambda t: -t[2].length); dd_ = []
    for let, sub, part in raw_:
        if any(l2 == let and part.hausdorff_distance(p2) < 5 for l2, _, p2 in dd_): continue
        dd_.append((let, sub, part))
    out_ = []
    for let, sub, part in dd_:
        rest = part
        for q in list(out_):
            shared = q['g'].intersection(part.buffer(60))
            if shared.length < 30: continue
            out_.remove(q)
            for g_, ls in ((shared, q['lines'] | {let}), (q['g'].difference(part.buffer(60)), q['lines'])):
                for r_ in getattr(g_, 'geoms', [g_]):
                    if r_.geom_type == 'LineString' and r_.length > 100: out_.append(dict(g=r_, lines=set(ls), subs=set(q['subs']) | ({sub} if g_ is shared else set())))
            rest = rest.difference(q['g'].buffer(60))
        for r_ in getattr(rest, 'geoms', [rest]):
            if r_.geom_type == 'LineString' and r_.length > 100: out_.append(dict(g=r_, lines={let}, subs={sub}))
    return out_
_raw_o = []
for line, sub, coords in json.load(open(SP + 'kmz/rer_lines.json')):
    g = LineString([T.transform(lon, lat) for lon, lat in coords])
    x = g.intersection(OUTER)
    for part in getattr(x, 'geoms', [x]):
        if part.geom_type == 'LineString' and part.length > 30: _raw_o.append((LETTER[line], sub, part))
OUTER_PIECES = _dedupe(_raw_o)
for q in OUTER_PIECES: q['subs'] = q['subs'] | {'outside the plan window: KMZ line as drawn'}; q['outer'] = True
pieces += OUTER_PIECES
RER_STRUCT = []
for r in RA['struct']:
    if r['state'] == 'unprofiled': continue
    for part in clip(LineString(r['c'])) if LineString(r['c']).length > 30 else []:
        RER_STRUCT.append(dict(line='A' if r['line'] == 'A' else 'A (Westwood)', state=r['state'], s0=r['s0'], s1=r['s1'], c=[r1(p) for p in part.simplify(0.5).coords]))
RER_MARKS = [m for m in RA['marks'] if WIN.contains(Point(m['p']))]
for ln_, st_, s0_, s1_ in BD_STRUCT:
    gg = BD_NEW if ln_ == 'B/D' else LineString(B_N)
    a_, b_ = gg.project(_P27(G27.C.interpolate(s0_).coords[0])), gg.project(_P27(G27.C.interpolate(s1_).coords[0]))
    seg = substring(gg, min(a_, b_), max(a_, b_))
    if seg.length > 20: RER_STRUCT.append(dict(line=ln_, state=st_, s0=round(s0_), s1=round(s1_), c=[r1(p) for p in seg.simplify(0.5).coords]))
_dg = LineString(D_CL)
RER_STRUCT.append(dict(line='D (with the Indianapolis pair)', state='viaduct', s0=round(G27.S_JCT), s1=None, c=[r1(p) for p in _dg.simplify(0.5).coords]))
def _mk(s, o, label, anchor='right'):
    return dict(p=r1(G27.nt_point(s, o)), label=label, anchor=anchor)
RER_MARKS += [_mk(G27.S_CW1, 33, 'Camp Washington (B, D) on the viaduct, %.1f m' % G27.band(G27.S_CWC)),
              _mk(G27.S_SEP + 40, 22, 'B/D 3.3%% down from %.1f m; 6.8 m under the viaduct from here' % G27.Z_CWS),
              _mk(2594, 18, 'B/D in a box from here (5.2 m cover); %.2f m from s %.0f to Straight' % (G27.Z_STR, G27.S_BOT)),
              _mk(G27.S_JCT + 60, 34, 'D leaves B: flyover (northbound D east of B, over it by s %.0f)' % G27.S_C),
              _mk(G27.S_ARC, 33, 'Arlington (B) on the viaduct, %.1f m' % G27.Z_AR),
              _mk(5300, 14, 'B at ground at Ludlow, %.1f m; north of here not laid out (B on its KMZ line)' % G27.Z_LUD)]
rst = []
for line, sts in json.load(open(SP + 'rer_stations.json')).items():
    for name, lon, lat, z in sts:
        p = Point(T.transform(lon, lat))
        if REG.contains(p): rst.append(dict(name=name.strip(), line=LETTER[line], p=p))
# Fountain Square: platform centres from Ben's KMZs
FS_PLAT = {'AD': LineString([(714918, 4330992), (715118, 4331038)]), 'B': LineString([(715137, 4331260), (715182, 4331060)])}
for s in rst:
    if s['name'] == 'Fountain Square':
        s['p'] = FS_PLAT['B'].interpolate(0.5, normalized=True) if s['line'] == 'B' else FS_PLAT['AD'].interpolate(0.5, normalized=True)
# B/D stations: Camp Washington and Straight stay at the KMZ points (at grade and dug sections); Western moves onto the bore,
# between Dolph and Western (entrances at both cross streets)
_DK = {f['properties']['name']: LineString(f['geometry']['coordinates']) for f in json.load(open(SP + 'deckpage/deck.json'))['features']
       if f['properties'].get('layer') == 'street' and f['geometry']['type'] == 'LineString'}
def _mid(a, b):
    ca, cb = BD_G.project(BD_G.intersection(_DK[a])), BD_G.project(BD_G.intersection(_DK[b])); return BD_G.interpolate((ca + cb) / 2)
BD_ST = {'Western': _mid('Dolph', 'Western')}
for s in rst:
    if s['line'] in 'BD' and s['name'] in BD_ST: s['p'] = BD_ST[s['name']]
    if (s['name'], s['line']) in ST_NEW: s['p'] = ST_NEW[(s['name'], s['line'])]
def merge(sts, key, rad=150):
    out = []
    for s in sts:
        for o in out:
            if o['name'] == s['name'] and o['p'].distance(s['p']) < rad: o['lines'].add(s[key]); break
        else: out.append(dict(name=s['name'], p=s['p'], lines={s[key]}))
    return out
# ---------------------------------------------------------------- 2026-10-15 (Ben): every curve at constant radius from the line's own points
# (arcs/fitarcs.py). Metro lines and the KMZ RER pieces; the designed B/D pieces (v27) are already drawn on arcs and are left alone.
# Tracks and platforms below follow the fitted lines; the page gets each line as its points plus a control point per curved piece.
import sys as _sfa; _sfa.path.insert(0, _ws.CODE + "arcs"); import fitarcs as FA
def _fit_line(o):
    r = FA.fit(list(o['g'].coords))
    if r.get('skipped'): return
    o['fit'] = r; o['g0'] = o['g']; o['g'] = LineString(FA.dense(r['verts'], r['k'], step=2.0))   # ids stay on the drawn line (g0)
for m in metro: _fit_line(m)
for q in pieces:
    if not (q.get('explicit') or q.get('split_at')): _fit_line(q)
_A = [q['g'] for q in pieces if q['lines'] == {'A'}]
for r_ in RER_STRUCT:                               # RER A's structure bands follow the fitted line
    if not _A: break
    a_, b_ = Point(r_['c'][0]), Point(r_['c'][-1]); g_ = min(_A, key=lambda g: g.distance(a_) + g.distance(b_))
    s0_, s1_ = sorted((g_.project(a_), g_.project(b_)))
    if s1_ - s0_ > 5: sub_ = substring(g_, s0_, s1_); sub_ = sub_ if g_.project(a_) <= g_.project(b_) else LineString(list(sub_.coords)[::-1]); r_['c'] = [r1(p) for p in sub_.simplify(0.3).coords]
FIT_SUMMARY = dict(lines=sum(1 for o in metro + pieces if o.get('fit')), curves=sum(len(o['fit']['curves']) for o in metro + pieces if o.get('fit')))
print('fitted', FIT_SUMMARY)
# ---------------------------------------------------------------- tracks and platforms
def offset_curves(g, st_ch, cfg, kind, L):
    """kind: 'island' or 'side'. st_ch: station chainages on g. Returns (tracks[2], platforms[])"""
    n = max(2, int(g.length / 2.0)); ds = np.linspace(0, g.length, n + 1)
    P = np.array([g.interpolate(d).coords[0] for d in ds])
    tang = np.gradient(P, axis=0); tang /= np.hypot(tang[:, 0], tang[:, 1])[:, None] + 1e-9
    for _ in range(3): tang[1:-1] = (tang[:-2] + 2 * tang[1:-1] + tang[2:]) / 4
    tang /= np.hypot(tang[:, 0], tang[:, 1])[:, None] + 1e-9; nrm = np.c_[-tang[:, 1], tang[:, 0]]
    h = np.full(len(ds), cfg['h0'])
    if kind == 'island':
        hs = cfg['island'] / 2 + cfg['edge']
        for c in st_ch:
            dd = np.abs(ds - c) - L / 2
            w = np.clip(1 - dd / TAPER, 0, 1); h = np.maximum(h, cfg['h0'] + (hs - cfg['h0']) * w)
    tracks = [LineString(P + nrm * h[:, None] * s).simplify(0.2) for s in (1, -1)]
    plats = []
    for c in st_ch:
        a, b = max(0, c - L / 2), min(g.length, c + L / 2)
        if b - a < L * 0.6: continue
        sel = (ds >= a) & (ds <= b); Q = P[sel]; N_ = nrm[sel]
        if len(Q) < 2: continue
        if kind == 'island':
            hw = cfg['island'] / 2; ring = np.r_[Q + N_ * hw, (Q - N_ * hw)[::-1]]; plats.append(Polygon(ring).simplify(0.2))
        else:
            for s_ in (1, -1):
                i0 = cfg['h0'] + cfg['edge']; o0 = i0 + cfg['side']
                ring = np.r_[Q + N_ * i0 * s_, (Q + N_ * o0 * s_)[::-1]]; plats.append(Polygon(ring).simplify(0.2))
    return tracks, plats
TRK, PLT = [], []
# 2026-10-14: stable ids so the page can edit centre lines and platforms (Ben); tracks and platforms carry their piece id (pid)
def _pid(prefix, label, g):
    x0, y0 = g.simplify(1.0).coords[0] if prefix == 'R' else g.coords[0]
    return '%s-%s-%d-%d' % (prefix, label.replace('Line ', 'L').replace(' ', ''), round(x0), round(y0))
for m in metro: m['id'] = _pid('M', m['name'], m.get('g0', m['g']))
_seen_ids = {}
for m in metro:                                    # two pieces of one line can start at the same window edge point
    if m['id'] in _seen_ids: m['id'] += '-%d' % round(m.get('g0', m['g']).length)
    _seen_ids[m['id']] = 1
for q in pieces: q['id'] = _pid('R', ''.join(sorted(q['lines'])), q.get('g0', q['g']))
for m in metro:
    sts = [s for s in mstations if s['line'] == m['name'] and m['g'].distance(s['p']) < 60]
    ch = sorted(m['g'].project(s['p']) for s in sts)
    cfg = MET_TWIN if m['era'] == 'twin' else MET_BORE
    tr, pl = offset_curves(m['g'], ch, cfg, 'island' if m['era'] == 'twin' else 'side', MPL)
    for t in tr: TRK.append(dict(sys='metro', line=m['name'], pid=m['id'], c=[r1(q) for q in t.coords]))
    for p_ in pl: PLT.append(dict(sys='metro', line=m['name'], pid=m['id'], c=[r1(q) for q in p_.exterior.coords]))
for q in pieces:
    if q.get('explicit'): continue
    if q.get('split_at'):                            # the new B/D piece: tracks south of the cut from offset_curves, north of it explicit
        g_ = q['g']; dd = g_.project(_P27(G27.C.interpolate(q['split_at']).coords[0])); gsub = substring(g_, dd, g_.length)
        q = dict(q, g=gsub)
    # Union Terminal A/B/D is drawn as its own box (ut_box.py)
    sts = [s for s in rst if s['line'] in q['lines'] and q['g'].distance(s['p']) < 80 and not (s['name'] == 'Union Terminal' and s['line'] in 'ABD')]
    ch = sorted({round(q['g'].project(s['p'])) for s in sts})
    ch = [c for i, c in enumerate(ch) if i == 0 or c - ch[i - 1] > 60]
    tr, pl = offset_curves(q['g'], ch, RER, 'island', RPL)
    lines = ' '.join(sorted(q['lines']))
    for t in tr: TRK.append(dict(sys='rer', line=lines, pid=q['id'], c=[r1(p) for p in t.coords]))
    for p_ in pl: PLT.append(dict(sys='rer', line=lines, pid=q['id'], c=[r1(p) for p in p_.exterior.coords]))
_PID = {key: [q['id'] for q in pieces if q['lines'] == ls and (q.get('explicit') or q.get('split_at')) or (key == 'B D' and q['lines'] == ls and q.get('split_at'))]
        for key, ls in (('B D', {'B', 'D'}), ('B', {'B'}), ('D', {'D'}))}
_PID = {k: ([i for i in v] or [None])[0] for k, v in _PID.items()}
for e in EXPL: TRK.append(dict(sys=e['sys'], line=e['line'], name=e['name'], pid=_PID.get(e['line']), c=[r1(p) for p in LineString(e['c']).simplify(0.2).coords]))
for ln_, pg in PL_NEW: PLT.append(dict(sys='rer', line=ln_, pid=_PID.get(ln_), c=[r1(p) for p in pg.simplify(0.2).exterior.coords]))
# Union Terminal TRI box: Chatelet-type, two tracks per island, D on A's islands (Ben, 2026-10-11)
import sys as _sys; _sys.path.insert(0, _ws.CODE + 'transit')
import ut_box
UT_MARKS, UT_META = ut_box.build(TRK, PLT, r1)
# platform ids and their nearest station (for the page's selection panel)
_mst = merge(mstations, 'line'); _rst = merge(rst, 'line')
for i, p_ in enumerate(PLT):
    pg = Polygon(p_['c']); cx, cy = pg.centroid.x, pg.centroid.y
    pool = _mst if p_['sys'] == 'metro' else _rst
    near = min(pool, key=lambda s: s['p'].distance(pg.centroid)) if pool else None
    p_['st'] = near['name'] if near is not None and near['p'].distance(pg.centroid) < 400 else ''
    p_['id'] = 'P-%s-%s-%d-%d' % (p_['sys'][0].upper(), p_['line'].replace('Line ', 'L').replace(' ', ''), round(cx), round(cy))
print('Union Terminal box', UT_META, 'crossings', UT_MARKS)
def _cfit(o, simp):
    if o.get('fit'): return dict(c=o['fit']['verts'], k=o['fit']['k'], curves=[[c['R'], c['mid'][0], c['mid'][1]] for c in o['fit']['curves']])
    return dict(c=[r1(p) for p in (o['g'].simplify(1.0) if simp else o['g']).coords])
ctx = dict(
    metro=[dict(id=m['id'], name=m['name'], era=m['era'], **_cfit(m, False)) for m in metro],
    rer=[dict(id=q['id'], name='RER ' + ' '.join(sorted(q['lines'])), lines=sorted(q['lines']), sub=', '.join(sorted(q['subs'])), **_cfit(q, True)) for q in pieces],
    stations=[dict(name=s['name'], line=' '.join(sorted(s['lines'], key=lambda x: int(re.sub(r'\D', '', x) or 0))), p=r1(s['p'].coords[0])) for s in merge(mstations, 'line')],
    rer_stations=[dict(name=s['name'], lines=sorted(s['lines']), p=r1(s['p'].coords[0])) for s in merge(rst, 'line')],
    tracks=TRK, plats=PLT, marks=UT_MARKS, rer_struct=RER_STRUCT, rer_marks=RER_MARKS,
    meta=dict(north_trunk='v27 (2026-10-14): B/D on the viaduct from Ludlow to Camp Washington, dive to Straight; D flyover; Arlington on the viaduct (log 10za.30-10za.33)', fitted=FIT_SUMMARY, metro_platform_m=MPL, rer_platform_m=RPL, metro_twin=MET_TWIN, metro_bore=MET_BORE, rer=RER, taper_m=TAPER, ut_box=UT_META, bd_approach=BD_META,
              note='Platform lengths are canon (Ben, 2026-10-05); track centres and platform widths are drawing values, not canon.'))
json.dump(ctx, open(SP + 'transit/context.json', 'w'), separators=(',', ':'))
print('metro', len(ctx['metro']), 'stations', len(ctx['stations']), '| rer pieces', len(ctx['rer']), 'stations', len(ctx['rer_stations']), '| tracks', len(TRK), 'platforms', len(PLT))
print(collections.Counter(p['sys'] for p in PLT))
