"""West side of the valley (Ben, 2026-10-13): streets and blocks east of State Avenue and Beekman Street, from Hopkins to
Ralston Avenue, on the deck and off it. Called from deck_gen.py with its globals; returns the new and changed streets, the
land to cut blocks from, the open rail corridors (no blocks), the 1904 boundary streets for the basin layer and the cuts.

Zone 1, Hopkins to Harrison (the 1913 Exposition grounds): the West End streets cross Exposition Boulevard on the deck grid
and run to State Avenue, or north of Liberty to Wallace, the street along the foot of the hill (the 1904 Wallace carried
north along the hill foot to State at Ernst); Summer, Berlin and Evans are carried north and a new street runs midway
between Evans and the boulevard.
Zone 2, Harrison to Hopple: west of RER A the 1904 cross streets of Beekman (Queen City, Tremont, Waverly, Knox) are carried
east; north of the Palace grounds the streets follow Camp Washington's own lines: Alfred, Straight, Marshall, Township and
Willow Lane carried west to Beekman on their 1904/1922 bearings, one new street midway between Marshall and Township, and
Johnson, Rawson and Meeker carried south on Garrard's bearing, with parallels to Johnson every 100 m towards Beekman.
Zone 3, Hopple to Ralston (Millvale bottoms): Camp Washington's east-west streets carried west to Beekman and South
Cumminsville's north-south streets carried south (the grid of the 2026-10-13 sketch).
Rail lines that cross at or near street level cut the streets (5.8 m clear + 1.0 m structure; 6.5 m under the APEx viaduct
as ruled for it; the portal rule for RER boxes).
2026-10-14 (page version 27, log 10za.30-10za.33): the north trunk is one viaduct from Ludlow to CUT (APEx, ORR, Transvalley/R5,
and TRI B/D from Camp Washington north), so its streets pass under; TRI B/D dive 3.3% south of Camp Washington to Straight,
and streets crossing the dive are re-graded where 3 m or less does it (as 10l.28, 10l.30), otherwise they end at it."""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, math, numpy as np, rasterio
from shapely.geometry import LineString, Point, Polygon, MultiPolygon, box, shape
from shapely.ops import unary_union, substring
SP = _ws.DATA
FT = 0.3048
DEM = rasterio.open(SP + 'handoff/out/map3_profile_dem_dm.vrt')
def gz(e, n):
    v = list(DEM.sample([(e, n)]))[0][0]; return None if v == -32768 else v / 10
def decklvl(n): return 151.8 + (n - 4330700) / 4840 * 8.2
def unit(b): r = math.radians(b); return np.array([math.sin(r), math.cos(r)])
def brg(p, q): return math.degrees(math.atan2(q[0] - p[0], q[1] - p[1])) % 360
PK = {}
for s, a, b, e, n, side, d in json.load(open(SP + 'lph/wb_picks.json')): PK.setdefault((a, b), (float(e), float(n)))
def pk(a, b): return PK.get((a, b)) or PK[(b, a)]
def ray(p, d, L=3000.0): p = np.asarray(p, float); return LineString([tuple(p), tuple(p + np.asarray(d, float) * L)])
def hit(p, d, target, L=3000.0, skip=0.5):
    g = ray(p, d, L).intersection(target)
    pts = []
    for q in getattr(g, 'geoms', [g]):
        if q.is_empty: continue
        pts += [Point(c) for c in (q.coords if q.geom_type != 'Point' else [q.coords[0]])]
    pts = [q for q in pts if q.distance(Point(p)) > skip]
    if not pts: return None
    return np.array(min(pts, key=lambda r: r.distance(Point(p))).coords[0])
def ext(a, b, over=0.3):
    a, b = np.asarray(a, float), np.asarray(b, float); d = (b - a) / np.linalg.norm(b - a); return tuple(b + d * over)
def parts(g, minl=1.0):
    return [q for q in getattr(g, 'geoms', [g]) if q.geom_type == 'LineString' and q.length >= minl]
def ln(*pts): return LineString([tuple(map(float, p)) for p in pts])

# ---------------------------------------------------------------- rail lines that can cut streets
class Bar:
    def __init__(s, name, line, hw, zf=None, clr=6.8, box_rule=False, s_deck=None, regrade=0.0):
        s.name, s.line, s.hw, s.zf, s.clr, s.box, s.s_deck, s.regrade = name, line, hw, zf, clr, box_rule, s_deck, regrade
        s.poly = line.buffer(hw, cap_style=2)
def street_level(q, DECK):
    return decklvl(q.y) if DECK.buffer(0.5).contains(q) else gz(q.x, q.y)
def verdict(b, q, DECK):
    """'pass' or 'cut' (and rail, street, diff) for a street crossing barrier b at q"""
    s = b.line.project(q); zr = b.zf(s) if b.zf else None
    zs = street_level(q, DECK)
    if zr is None: return 'cut', None, zs, None
    if zs is None: return 'pass', zr, None, None
    d = zr - zs
    if b.s_deck is not None and s <= b.s_deck and zr <= decklvl(q.y) - 6.8 + 0.05: return 'pass', zr, zs, d
    if d >= b.clr - 0.05 or d <= -max(b.clr, 6.8): return 'pass', zr, zs, d
    if b.box and d <= -4.6: return 'pass', zr, zs, d             # over the box (5.2 m and more) or on its roof (4.6-5.2 m)
    return 'cut', zr, zs, d
COVER_BOX = 5.2                                   # street over a box: 5.2 m rail depth or more (10j.7)
def profile_fn(prof):
    a = np.array([(s, z if z is not None else np.nan) for s, z, *_ in prof], float)
    def f(s):
        if s < a[0, 0] or s > a[-1, 0]: return None
        v = float(np.interp(s, a[:, 0], a[:, 1])); return None if math.isnan(v) else v
    return f

def build(g):
    ux, uy = g['ux'], g['uy']; U = np.array([ux, uy])
    TH_W = g['TH_W']; WE = unit(TH_W)                     # east on the boulevard's square
    DECK, EDGE_W, EDGE_E = g['DECK'], g['EDGE_W'], g['EDGE_E']
    T_ST, NS, THRU, RADIALS = g['T_ST'], g['NS'], g['THRU'], g['RADIALS']
    PALACE, FORECOURT, RBC, PRECINCT = g['PALACE'], g['FORECOURT'], g['RBC'], g['PRECINCT']
    BASIN = json.load(open(SP + 'sbg/fit/basin_sanborn.json'))['features']
    BST = [f for f in BASIN if f['properties']['layer'] == 'street' and f['properties'].get('set') != 'wv']
    BBLK = [shape(f['geometry']) for f in BASIN if f['properties']['layer'] == 'block' and f['properties'].get('set') != 'wv']
    def bline(name, near, maxd=60):
        best = None
        for f in BST:
            if f['properties']['name'] != name: continue
            l = LineString(f['geometry']['coordinates']); d = l.distance(Point(near))
            if d < maxd and (best is None or d < best[0]): best = (d, l)
        return best[1] if best else None
    def bwidth(name, near):
        best = None
        for f in BST:
            if f['properties']['name'] != name: continue
            d = LineString(f['geometry']['coordinates']).distance(Point(near))
            if best is None or d < best[0]: best = (d, f['properties'].get('width_m', 60 * FT))
        return best[1] if best and best[0] < 60 else 60 * FT
    def west_end(name, near):
        l = bline(name, near); c = np.array(l.coords); return c[np.argmin(c[:, 0])]
    def south_end(name, near):
        l = bline(name, near); c = np.array(l.coords); return c[np.argmin(c[:, 1])]
    O = json.load(open(SP + 'lph/osm_north.geojson'))['features']
    osm = lambda nm: unary_union([shape(f['geometry']) for f in O if f['properties'].get('name') == nm and shape(f['geometry']).geom_type == 'LineString'])
    R = json.load(open(SP + 'rera/rera.json'))
    RA, RW = LineString(R['lines']['A']), LineString(R['lines']['westwood'])
    new, cuts, notes = [], [], []          # new: dict(name, kind, w, line, side, zone, src)
    def add(name, line, zone, w=60 * FT, kind='WV', src='new'):
        new.append(dict(name=name, kind=kind, w=w, line=line, side='WV', zone=zone, src=src))
    # ======================================================== 1904 boundary streets (State, Beekman, Cummings): basin layer
    gest = [l for n, l, w in THRU if n == 'Gest'][0]
    STATE_N = ln(gest.coords[0], pk('State Avenue', 'Wilder Avenue'), pk('State Avenue', 'Maxwell Place'), pk('State Avenue', 'Mistletoe'),
                 pk('State Avenue', 'Wallace'), pk('State Avenue', 'West Liberty Street'), pk('State Avenue', 'Saratoga'), pk('State Avenue', 'Oscar'),
                 pk('Lehman Road', 'State Avenue'), pk('Ernst Street', 'State Avenue'), pk('Harrison Avenue', 'State Avenue'))
    BK = [('Harrison Avenue', 'Beekman Street'), ('Beekman Street', 'Brighton Street'), ('Beekman Street', 'Queen City Avenue'), ('Beekman Street', 'Tremont Street'),
          ('Beekman Street', 'Waverly Avenue'), ('Beekman Street', 'Knox Street'), ('Beekman Street', 'Fairmount Avenue'), ('Western Avenue', 'Cummings Street'),
          ('Western Avenue', 'Vinton Street'), ('Western Avenue', 'Dempsey Street'), ('Baltimore Avenue', 'Western Avenue'), ('Carll Street', 'Western Avenue'),
          ('Holliday Street', 'Western Avenue'), ('Denham Street', 'Western Avenue'), ('Pulte Street', 'Western Avenue'), ('South Hopple Street', 'Western Avenue'),
          ('Hopple Street', 'Western Avenue')]
    BEEK = ln(*[pk(*k) for k in BK])
    # north of Hopple: OSM Beekman (the line survives), from the 1904 Hopple corner to Ralston
    bo = osm('Beekman Street'); bo = [q for q in parts(bo) if q.bounds[3] > 4335000]
    bo = unary_union(bo)
    from shapely.ops import linemerge
    bo = linemerge(bo) if bo.geom_type == 'MultiLineString' else bo
    bo = max(parts(bo), key=lambda q: q.length)
    bc = list(bo.coords); bc = bc if bc[0][1] < bc[-1][1] else bc[::-1]
    bc = [q for q in bc if 4334960 < q[1] < 4336560]
    BEEK_N = ln(BEEK.coords[-1], *bc)
    CUMM = ln(pk('Western Avenue', 'Cummings Street'), pk('Cummings Street', 'Vinton Street'), pk('Dempsey Street', 'Cummings Street'),
              pk('Carll Street', 'Cummings Street'), pk('Denham Street', 'Cummings Street'))
    VINT = ln(pk('Western Avenue', 'Vinton Street'), pk('Cummings Street', 'Vinton Street'))
    DENH = ln(pk('Denham Street', 'Western Avenue'), pk('Denham Street', 'Cummings Street'))
    B1904 = [('State Avenue', STATE_N, 60, 'Sanborn 1904', 'vol. 5 sheets 491-495 (crossings picked), Gest to Harrison'),
             ('Beekman Street', BEEK, 60, 'Sanborn 1904', 'vol. 5 sheets 504-505, 511-514, 519-522 (crossings picked); "Western Avenue" north of Fairmount on the 1904 sheets'),
             ('Beekman Street', BEEK_N, 60, 'OSM', 'north of Hopple on the surviving line (OSM)'),
             ('Cummings Street', CUMM, 50, 'Sanborn 1904', 'vol. 5 sheets 513-514, 519-520'),
             ('Harrison Avenue', ln(pk('Harrison Avenue', 'State Avenue'), pk('Harrison Avenue', 'Hiawatha Street'), pk('Harrison Avenue', 'Beekman Street')), 70, 'Sanborn 1904', 'the 1904 line, State to Beekman (vol. 5 sheets 491, 504-505)'),
             ('Vinton Street', VINT, 50, 'Sanborn 1904', 'Beekman to Cummings'), ('Denham Street', DENH, 50, 'Sanborn 1904', 'Beekman to Cummings')]
    # ======================================================== zone 1: Hopkins to Harrison
    WALLACE = ln(pk('State Avenue', 'Wallace'), pk('Wallace', 'Saratoga'), (712205.0, 4332805.0), (712255.0, 4332905.0), (712293.0, 4333010.0),
                 pk('Ernst Street', 'State Avenue'))
    WB1 = unary_union([STATE_N, WALLACE])
    add('Wallace Street', WALLACE, '1', src='the 1904 Wallace (State to Saratoga), carried north along the foot of the hill to State at Ernst')
    TL = {}
    for t in T_ST:
        if t['side'] in ('E', 'LPH'): TL.setdefault(t['name'], []).append(t)
    Z1_EW = ('Kenner', 'Courtland', 'Flint', 'Wade', 'Wilstach', 'Sherman', 'Poplar', 'Findlay', 'York', 'Exeter', 'Dayton', 'Bank', 'Dolph', 'McRoberts')
    for nm in Z1_EW:
        for t in TL.get(nm, []):
            c = list(t['line'].coords)
            if Point(c[-1]).distance(EDGE_E) > 1.0: continue           # only the piece that reaches the boulevard
            d = np.array(c[-1]) - np.array(c[-2]); d /= np.linalg.norm(d)
            e = hit(c[-1], d, WB1)
            if e is None: continue
            t['orig'] = dict(line=t['line'], kind=t['kind'], side=t['side'])
            t['line'] = LineString(c + [ext(c[-1], e)]); t['kind'] = 'through'; t['side'] = 'WV'; t['zone'] = '1'; t['wv'] = True
    hop = TL['Hopkins'][0]; c = list(hop.line.coords) if hasattr(hop, 'line') else list(hop['line'].coords)
    e = hit(c[-1], np.array(c[-1]) - np.array(c[-2]), STATE_N)
    if e is not None: hop['line'] = LineString(c + [ext(c[-1], e)]); hop['wv'] = True; notes.append('Hopkins carried from Summer to State')
    # W Liberty to State
    for i, (n, l, w) in enumerate(THRU):
        if n == 'W Liberty':
            c = list(l.coords); e = hit(c[0], np.array(c[0]) - np.array(c[1]), STATE_N, L=60)
            if e is not None: THRU[i] = (n, LineString([ext(c[1], e)] + c), w)
    # Summer, Berlin, Evans carried north; a new street midway between Evans and the boulevard
    for s_ in NS:
        if s_['name'] in ('Summer', 'Berlin', 'Evans') and s_.get('side') == 'LPH':
            c = list(s_['line'].coords); e = hit(c[-1], U, WB1)
            if e is not None: s_['line'] = LineString([c[0], ext(c[0], e)]); s_['wv'] = True; s_['zone'] = '1'
    hopl = hop['line']
    ev = [s_ for s_ in NS if s_['name'] == 'Evans'][0]['line']
    p_ev = hopl.intersection(ev); p_ev = np.array(p_ev.coords[0]) if p_ev.geom_type == 'Point' else np.array(list(p_ev.geoms)[0].coords[0])
    p_bw = hit(p_ev, WE, EDGE_W); mid = (p_ev + p_bw) / 2
    m0 = hit(mid - U * 60, U, hopl, L=120); e = hit(m0, U, WB1)
    add('New street W', ln(ext(e, m0, 0.3), ext(m0, e)), '1')
    # ======================================================== zone 2: Harrison to Hopple
    # radials carried to Beekman: Queen City (west) to its 1904 corner, Harrison (west) to the 1904 Harrison corner
    for i, (n, l, w) in enumerate(RADIALS):
        c = list(l.coords)
        if n.startswith('Queen City Avenue (west)'): RADIALS[i] = (n, LineString(c + [ext(c[-1], pk('Beekman Street', 'Queen City Avenue'))]), w)
        if n.startswith('Harrison Avenue (west'): RADIALS[i] = (n, LineString(c + [ext(c[-1], pk('Harrison Avenue', 'Beekman Street'))]), w)
    QCW = [l for n, l, w in RADIALS if n.startswith('Queen City Avenue (west)')][0]
    HAW = [l for n, l, w in RADIALS if n.startswith('Harrison Avenue (west')][0]
    TN = math.degrees(math.atan2(g['bg'], 1.0))          # Garrard's bearing
    uN = unit(TN); wN = np.array([uN[1], -uN[0]])        # north on Garrard; east square to it
    def ns_line(p, s0=-1600, s1=1600): p = np.array(p, float); return ln(p + uN * s0, p + uN * s1)
    J0 = np.array(south_end('Johnson Street', (712382, 4334884)))
    GL = [s_['line'] for s_ in NS if s_['name'] == 'Garrard line']
    GLL = ns_line((g['ag'] + g['bg'] * (4334000 - 4332000), 4334000.0))
    # Camp Washington's east-west streets, from their 1904/1922 west ends on their own bearings
    CW = {}
    for nm, bn, near in (('Alfred', 'Alfred Street', (712772, 4333981)), ('Straight', 'Straight Street', (712804, 4334170)), ('Marshall', 'Marshall Avenue', (712752, 4334368)),
                         ('Township', 'Township Street', (712559, 4334664)), ('Willow Lane', 'Willow Street', (712534, 4334706))):
        l = bline(bn, near); c = np.array(l.coords); c = c[np.argsort(c[:, 0])]
        p0 = c[0]; b0 = brg(c[0], c[-1])
        if nm == 'Willow Lane':                                      # 1922: Willow Lane reaches Rawson
            p0 = np.array([712497.0, 4334712.0]); b0 = brg(p0, c[-1])
        CW[nm] = (p0, b0, bwidth(bn, near))
    pM, bM, _ = CW['Marshall']; pT, bT, _ = CW['Township']
    xm = 712450.0
    yM = pM[1] + (pM[0] - xm) * math.tan(math.radians(bM - 90)); yT = pT[1] + (pT[0] - xm) * math.tan(math.radians(bT - 90))
    CW['New street N'] = (np.array([xm, (yM + yT) / 2]), (bM + bT) / 2, 60 * FT)
    Z2W = unary_union([BEEK, CUMM])
    for nm, (p0, b0, wd) in CW.items():
        dW = -unit(b0)
        if nm == 'New street N':                                   # from the Garrard line (the APEx ramp then cuts it)
            q = ray(p0, -dW, 600).intersection(GLL); p0 = np.array(q.coords[0])
        e = hit(p0, dW, BEEK)
        # east end: Alfred, Straight and Marshall from the Garrard line (the deck streets east of it stay), the rest from their 1904 end
        if nm in ('Alfred', 'Straight', 'Marshall'):
            s0 = hit(p0, -dW, unary_union(GL + [GLL]), L=300) if False else None
            q = ray(p0, dW, 2000).intersection(GLL); q = np.array(q.coords[0])
            # replace the deck's north-side T street with one continuous street on Camp Washington's line
            for t in list(T_ST):
                if t['name'] == nm and t['side'] == 'N': T_ST.remove(t)
            # east of Garrard: from the deck's east edge (as the T street had it) on the same line
            east = hit(q, -dW, DECK.boundary, L=400)
            pts = [tuple(east) if east is not None else tuple(p0), tuple(q), ext(q, e)]
            add(nm, ln(*pts), '2', w=wd, src='Camp Washington line (1904 bearing %.2f deg)' % b0)
        else:
            add(nm if nm == 'New street N' else nm + ' (carried west)', ln(p0, ext(p0, e)), '2', w=wd, src='Camp Washington line (bearing %.2f deg)' % b0)
    # Johnson, Rawson and Meeker carried south on Garrard's bearing; Johnson from Harrison, the other two from Alfred
    alf = [s_['line'] for s_ in new if s_['name'] == 'Alfred'][0]
    for nm, p in (('Johnson Street (carried south)', J0), ('Rawson Street (carried south)', south_end('Rawson Street', (712500, 4334739))),
                  ('Meeker Street (carried south)', (712559.0, 4334767.0))):
        tgt = HAW if nm.startswith('Johnson') else alf
        s = hit(p, -uN, tgt)
        wd = 50 * FT if nm.startswith('Johnson') else bwidth(nm.replace(' (carried south)', ''), p)
        add(nm, ln(ext(p, s), p), '2', w=wd, src='Camp Washington line on Garrard\'s bearing %.2f deg' % TN)
    HOPV0 = [LineString(f['geometry']['coordinates']) for f in BST if f['properties']['name'] == 'Hopple Street' and f['properties'].get('set') == '1922'][0]
    # parallels to Johnson towards Beekman, every 100 m
    for k in (1, 2, 3, 4):
        p = J0 - wN * 100 * k
        L_ = ns_line(p).intersection(Polygon(list(BEEK.coords) + [(713000, 4334920), (713000, 4333400)]).buffer(0))
        L_ = L_.intersection(box(711500, 4334010, 713000, 4335000))
        for q in parts(L_, 60):
            c = list(q.coords); c = c if c[0][1] < c[-1][1] else c[::-1]
            if np.mean([BEEK.distance(q.interpolate(t, normalized=True)) for t in np.linspace(0, 1, 9)]) < 80: continue
            if c[-1][1] > 4334870:
                h_ = hit(c[0], uN, unary_union([BEEK, HOPV0]))
                if h_ is not None: c[-1] = ext(c[0], h_)
            add('New street J%d' % k, LineString(c), '2')
    # Queen City's west-bank cross streets carried east from Beekman to Johnson
    JL = [s_['line'] for s_ in new if s_['name'].startswith('Johnson')][0]
    for nm, wn in (('Tremont Street', 'Lawnway'), ('Waverly Avenue', 'Lawnway'), ('Knox Street', 'Bloom Street')):
        b0 = pk('Beekman Street', nm)
        try: a0 = pk(wn, nm)
        except KeyError: a0 = None
        d = (np.array(b0) - np.array(a0)) / np.linalg.norm(np.array(b0) - np.array(a0)) if a0 else WE
        e = hit(b0, d, JL)
        if e is not None: add(nm.split()[0] + ' (carried east)', ln(b0, ext(b0, e)), '2', src='1904 line carried east')
    # ======================================================== zone 3: Hopple to Ralston
    HOPV = [LineString(f['geometry']['coordinates']) for f in BST if f['properties']['name'] == 'Hopple Street' and f['properties'].get('set') == '1922'][0]
    RAL = bline('Ralston Avenue', (711900, 4336475))
    Z3T = unary_union([BEEK_N, BEEK])
    for nm, near in (('Stock Avenue', (712386, 4335144)), ('Ethan Avenue', (712455, 4335241)), ('Bates Avenue', (712454, 4335316)), ('Alabama Avenue', (712382, 4335399)),
                     ('Monmouth Avenue', (712460, 4335571)), ('Sassafras Street', (712466, 4335729)), ('Arlington Street', (712468, 4335803)), ('Marquis Avenue', (712380, 4335884)),
                     ('Adelaide Street', (712363, 4335972)), ('Brashears Street', (712458, 4336082)), ('Earl Avenue', (712442, 4336218)), ('Whiteley Street', (712431, 4336300))):
        w = west_end(nm, near); e = hit(w, -unit(93.6), Z3T)
        if e is not None: add(nm.split()[0] + ' (carried west)', ln(w, ext(w, e)), '3', w=bwidth(nm, near), src='Camp Washington street carried west on 93.6 deg')
    for nm, near, b in (('Follett Avenue', (712070, 4336465), 2.7), ('Roll Avenue', (711993, 4336469), 3.2), ('Dawson Avenue', (711913, 4336474), 3.1), ('Borden Street', (711807, 4336370), 3.1)):
        s = south_end(nm, near); e = hit(s, -unit(b), unary_union([HOPV, BEEK_N]))
        if e is not None: add(nm.split()[0] + ' (carried south)', ln(s, ext(s, e)), '3', w=bwidth(nm, near), src='South Cumminsville street carried south on its own bearing')
    # ======================================================== rail lines that cut streets
    prof = R['profiles']
    S_EDGE = R['s_edge']
    import sys as _s27; _s27.path.insert(0, _ws.CODE + 'nv')
    import geom27 as G27
    T = json.load(open(SP + 'deckpage/tracks.json'))['features']
    app = [LineString(f['geometry']['coordinates']) for f in T if f['properties'].get('layer') == 'apex' and 'north approach' in str(f['properties'].get('name', ''))
           and f['properties']['name'][-6:-5] in '1234']                     # the Dayton/Norwood tracks (the Indianapolis pair climbs away)
    app = [q if q.coords[0][1] > q.coords[-1][1] else LineString(q.coords[::-1]) for q in app]
    appL = sorted(app, key=lambda q: q.coords[-1][0])[len(app) // 2]       # a middle track
    lowp = [LineString(f['geometry']['coordinates']) for f in T if f['properties'].get('layer') == 'lower' and f['geometry']['type'] == 'LineString'
            and max(c[1] for c in f['geometry']['coordinates']) > 4334300 and 'R5' not in f['properties'].get('name', '')]
    tip = Point(appL.coords[0])
    def apex_z(s):                                                  # the viaduct band (nv/geom27.py): deck + 6.5 m to the tip, 0.79% down to Ludlow
        return G27.band(G27.C.project(appL.interpolate(s)))
    apx_env = unary_union([q.buffer(2.6) for q in app + lowp]).intersection(box(711500, 4334300, 713200, 4337000))
    TC, TZ = G27.tri_centre(); TRL = LineString(TC)
    _ts = np.r_[0, np.cumsum(np.hypot(*np.diff(np.array(TC), axis=0).T))]
    TRZ = lambda q, a=np.array(TZ), s=_ts: float(np.interp(q, s, a))
    DC, DZ = G27.d_centre(); GRL = LineString(DC)
    _ds = np.r_[0, np.cumsum(np.hypot(*np.diff(np.array(DC), axis=0).T))]
    GRZ = lambda q, a=np.array(DZ), s=_ds: float(np.interp(q, s, a))
    r5 = [LineString(f['geometry']['coordinates']) for f in T if 'R5 to the Cumminsville Spur (west' in str(f['properties'].get('name', ''))]
    R5L = r5[0] if r5 else LineString([(0, 0), (1, 1)])
    R5Z = lambda q: G27.band(4150.0) - 0.004 * q                   # indicative: down about 0.4% to pass under RER A (167.0 m) at 160 m or less
    NORTH = box(711400, 4334100, 713200, 4337200)
    AK = []
    import re as _re
    for fn in ('kmz_apex/doc.kml',):
        s_ = open(SP + fn, encoding='utf-8', errors='ignore').read()
        from pyproj import Transformer
        T4 = Transformer.from_crs(4326, 26916, always_xy=True)
        for pm in _re.findall(r'<Placemark>(.*?)</Placemark>', s_, _re.S):
            nmm = _re.search(r'<name>(.*?)</name>', pm); nmm = nmm.group(1) if nmm else ''
            if nmm not in ('Vandalia-Cincinnati', 'Cincinnati-Norwood'): continue
            for co in _re.findall(r'<coordinates>(.*?)</coordinates>', pm, _re.S):
                pts = [tuple(map(float, c.split(',')[:2])) for c in co.split() if c.count(',') >= 1]
                AK.append(LineString([T4.transform(*p) for p in pts]))
    Y_LUD = G27.C.interpolate(5368.0).y                              # the APEx lines are at grade only north of Ludlow now
    APXN = unary_union([q.buffer(13, cap_style=2) for q in AK]).intersection(box(711500, Y_LUD, 713200, 4337200))
    clipW = box(711400, 4331700, 713000, 4336700)
    BARS = [Bar('RER A', RA, 6.0, profile_fn(prof['A']), 6.8, True, S_EDGE), Bar('RER A (Westwood)', RW, 6.0, profile_fn(prof['westwood']), 6.8, True),
            Bar('North trunk viaduct (APEx, ORR, Transvalley)', appL, 0.0, apex_z, 6.5), Bar('TRI B/D (dive south of Camp Washington)', TRL, 6.0, TRZ, 6.5, True, regrade=3.0),
            Bar('Indianapolis + TRI D viaduct', GRL, 6.0, GRZ, 6.5), Bar('R5 (Cumminsville Spur)', R5L, 6.0, R5Z, 6.8)]
    for b in BARS[3:]: b.poly = b.poly.intersection(NORTH)
    BARS[2].poly = apx_env
    APXN_BAR = Bar('APEx north of Ludlow (Vandalia and Norwood lines, at grade)', LineString([(0, 0), (1, 1)]), 0.0, None)
    APXN_BAR.poly = APXN
    regrades = []
    def crossings(line, b):
        out = []
        x = line.intersection(b.line) if b.poly is not APXN else line.intersection(APXN.boundary)
        for q in getattr(x, 'geoms', [x]):
            if q.is_empty: continue
            if q.geom_type != 'Point': q = Point(q.coords[0])
            out.append(q)
        if b is BARS[2]:                                        # APEx envelope: test where the street meets the middle track
            x = line.intersection(appL); out = [q if q.geom_type == 'Point' else Point(q.coords[0]) for q in getattr(x, 'geoms', [x]) if not q.is_empty]
            if not out and line.intersects(b.poly):
                q = line.intersection(b.poly); out = [Point(list(parts(q, 0.1))[0].interpolate(0.5, normalized=True).coords[0])] if parts(q, 0.1) else []
        pb = b.poly.buffer(1.0)
        return [q for q in out if pb.contains(q)]
    def apply_cuts(name, line, zone, w=60 * FT):
        """returns the pieces of line left after the rail cuts, and records each cut"""
        keep = line
        for b in BARS + [APXN_BAR]:
            if not keep.intersects(b.poly): continue
            if b is APXN_BAR:
                cutp = APXN.buffer(1.0)
                cuts.append(dict(street=name, bar=b.name, p=list(Point(keep.intersection(APXN).representative_point()).coords[0]) if not keep.intersection(APXN).is_empty else None, rail=None, street_z=None, diff=None))
                keep = keep.difference(cutp); continue
            for q in crossings(keep, b):
                v, zr, zs, d = verdict(b, q, DECK)
                if v == 'pass': continue
                if b.regrade and d is not None:                     # re-grade the street where 3 m or less does it (10l.28, 10l.30)
                    # worst rail level under the street's width across both tracks (half-window along the line)
                    sq = b.line.project(q); a1 = np.array(b.line.interpolate(max(0, sq - 2)).coords[0]); a2 = np.array(b.line.interpolate(sq + 2).coords[0])
                    ti = a2 - a1; ti /= np.linalg.norm(ti)
                    sp_ = keep.interpolate(keep.project(q)); s1_ = np.array(keep.interpolate(max(0, keep.project(q) - 2)).coords[0]); s2_ = np.array(keep.interpolate(keep.project(q) + 2).coords[0])
                    tj = s2_ - s1_; tj /= np.linalg.norm(tj); sn = max(0.2, abs(ti[0] * tj[1] - ti[1] * tj[0]))
                    W_ = (w / 2) / sn + 2.25 * math.sqrt(max(0.0, 1 - sn * sn)) / sn
                    zz = [b.zf(x) for x in np.linspace(sq - W_, sq + W_, 13) if b.zf(x) is not None]
                    if d >= 0: need, how = b.clr - (min(zz) - zs), 'lowered'
                    else: need, how = COVER_BOX + (max(zz) - zs), 'raised'
                    if need <= b.regrade + 0.05:
                        regrades.append(dict(street=name, bar=b.name, p=[round(q.x, 1), round(q.y, 1)], rail=round(zr, 1), street_z=round(zs, 1), diff=round(d, 1),
                                             need=round(need, 1), how=how)); continue
                cutp = b.poly.buffer(1.0).intersection(q.buffer(max(60, b.hw * 12)))
                if b is BARS[2]: cutp = b.poly.buffer(1.0).intersection(q.buffer(60))
                cuts.append(dict(street=name, bar=b.name, p=[round(q.x, 1), round(q.y, 1)], rail=zr and round(zr, 1), street_z=zs and round(zs, 1), diff=d if d is None else round(d, 1)))
                keep = keep.difference(cutp)
        return [p for p in parts(keep, 1.0)]
    # apply to the new streets, the zone 1 streets carried west, Summer/Berlin/Evans, and the Garrard line north of Marshall
    out_new = []
    for s_ in new:
        ps = apply_cuts(s_['name'], s_['line'], s_['zone'], s_.get('w', 60 * FT))
        for p in ps:
            if p.length >= 40: out_new.append(dict(s_, line=p, cut=('rail' if len(ps) > 1 or p.length < s_['line'].length - 2 else None)))
    def cut_list(lst, key='name'):
        res = []
        for t in lst:
            if not t.get('wv') and t.get('name') != 'Garrard line': res.append(t); continue
            ps = apply_cuts(t['name'], t['line'], t.get('zone', ''), t.get('w', 60 * FT))
            whole = sum(p.length for p in ps) > t['line'].length - 2
            if whole: res.append(dict(t, cut=None)); continue
            # a piece cut off by the rail is kept only if it is long enough to front buildings (60 m); a zone 1 street whose
            # piece west of the rail is dropped goes back to its T at the boulevard, and one that keeps it stops at the
            # boulevard on the east side (the strip between the boulevard and the ramp has nothing to serve)
            ps = [p for p in ps if p.length >= 60]
            if t.get('orig'):
                o = t['orig']; oend = Point(o['line'].coords[-1])
                west = [p for p in ps if p.distance(oend) > 1.0 and not p.buffer(0.5).contains(oend)]
                if west: res.append(dict(t, line=o['line'], kind=o['kind'], side=o['side'], cut='rail (piece west of the rail kept)'))
                else: res.append(dict(t, line=o['line'], kind=o['kind'], side=o['side'], cut='rail (no piece west of the rail)')); continue
                for p in west: res.append(dict(t, line=p, cut='rail', name=t['name']))
                continue
            for p in ps: res.append(dict(t, line=p, cut='rail'))
        return res
    T_ST[:] = cut_list(T_ST); NS[:] = cut_list(NS)
    ga = south_end('Garrard Avenue', (712672, 4334576))
    for s_ in NS:
        if s_['name'] != 'Garrard line': continue
        c = list(s_['line'].coords); top = max(range(len(c)), key=lambda i: c[i][1])
        if Point(c[top]).distance(Point(ga)) < 40:
            c2 = c if top == len(c) - 1 else c[::-1]
            s_['line'] = LineString(c2[:-1] + [ext(c2[-2], ga)]); notes.append('Garrard line runs on into the 1904 Garrard Avenue (%.1f m off its line)' % (LineString(c2[-2:]).distance(Point(ga))))
    # drop short west-of-boulevard stubs (under 60 m) that the rail leaves between the boulevard and the hill
    # ======================================================== land for blocks (off the deck), and open rail corridors
    BW_ = [(711700.0, 4331760.0)] + list(STATE_N.coords)[1:] if False else None
    z1 = Polygon(list(STATE_N.coords) + [(712400, 4333244), (712400, 4331700), (711600, 4331700)]).buffer(0)
    z1 = z1.difference(Polygon(list(WALLACE.coords) + [(711700, 4333300), (711700, 4332186)]).buffer(0))
    z1 = z1.intersection(box(711550, hopl.bounds[1] - 40, 712500, 4333300))
    z2 = Polygon(list(BEEK.coords) + [(713000, 4334930), (713000, 4333244), pk('Harrison Avenue', 'State Avenue'), pk('Harrison Avenue', 'Hiawatha Street')]).buffer(0).intersection(box(711800, 4333200, 712620, 4334930))
    rc = sorted(RAL.coords, key=lambda q: q[0])
    z3 = Polygon([q for q in BEEK_N.coords if q[1] < rc[0][1]] + [rc[0], rc[-1], (712420, rc[-1][1]), (712420, 4334880)]).buffer(0)
    taken = unary_union([b.buffer(0.5) for b in BBLK] + [LineString(f['geometry']['coordinates']).buffer(f['properties'].get('width_m', 10) / 2 + 0.5, cap_style=2) for f in BST])
    WV_AREA = unary_union([z1, z2, z3]).difference(taken).buffer(0)
    # open corridors: RER A where it is open (ramp, trough, at grade), the APEx approach where it is neither under nor over the
    # deck with street clearance, the rail corridor north of the deck tip, and the Greensburg line / TRIMET trunk where open
    vo = []
    for r in R['struct']:
        if r['state'] == 'ramp': vo.append(LineString(r['c']).buffer(7.5, cap_style=2))      # 1.5 m past the street ends
    # 2026-10-14: the north trunk is a viaduct (no open corridor in the lobe or north of the tip); TRI B/D's open trough and
    # ramp south of Camp Washington (s 2,594-2,964) are the only open rail there; Hopple is at deck level (no viaduct void)
    for c_ in G27.bd_tracks(2594.0, G27.S_CW0):
        if len(c_) > 1: vo.append(LineString(c_).buffer(3.5, cap_style=2))
    vo.append(APXN.buffer(1.5))
    VOIDS = unary_union([v for v in vo if not v.is_empty]).buffer(0)
    return dict(new=out_new, WV_AREA=WV_AREA, VOIDS=VOIDS, B1904=B1904, cuts=cuts, regrades=regrades, notes=notes, WB1=WB1, BEEK=BEEK, BEEK_N=BEEK_N,
                zones=dict(z1=z1, z2=z2, z3=z3))
