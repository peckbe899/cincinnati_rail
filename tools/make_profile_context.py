"""Context for the Rail Profiles page and railsim.metro_profile: the Mill Creek Deck's structures at
CUT and Norwood Central projected onto every Profiles line, and its street re-grades and open cuts
as ground runs. Writes data/profile/context/lines.json.

    python tools/make_profile_context.py

Inputs: data/deck/*.json (a snapshot of the Deck's published files: tracks, structures, deck,
norwood, context; refresh it from the Deck artifact when the Deck changes), data/profile lines and
the map 3 ground (data/profile/dem). Needs shapely, pyproj and rasterio.

Rulings (Ben, 2026-10-26): blocks drawn and checked, not editable; lower-pair levels rebuilt from the
Deck's dive figures until the Deck publishes a level per point; Norwood ORR, Transvalley and APEx
tracks fixed (levels approximate, from the ground data); viaduct arches to the street, no footing
check; the Deck's street re-grades are finished ground. Drawing values: the W 8th ramp ends and the
60 m ramps on Bank and Findlay.
"""
# --- shared helpers (paths, projections, chainage on a Profiles line path, the map 3 ground) ---
import json, math, sys
from pathlib import Path
import numpy as np
from pyproj import Transformer
from shapely.geometry import LineString, Point
import rasterio
from rasterio.windows import Window
ROOT = Path(__file__).resolve().parent.parent
SITE, DECK = str(ROOT / "data" / "profile"), str(ROOT / "data" / "deck")
ORIG = SITE
VRT = str(ROOT / "data" / "profile" / "dem" / "map3_profile_dem_dm.vrt")
TO_UTM = Transformer.from_crs(4326, 26916, always_xy=True)
TO_LL = Transformer.from_crs(26916, 4326, always_xy=True)
def jload(p): return json.load(open(p, encoding='utf8'))
def jsave(p, d, indent=None):
    with open(p, 'w', encoding='utf8') as f: json.dump(d, f, ensure_ascii=False, indent=indent, separators=(',', ':') if indent is None else None)
class Path:
    """A Profiles line path: vertices [c, lon, lat] -> UTM polyline with chainage mapping."""
    def __init__(self, path):
        self.cv = np.array([p[0] for p in path], float)
        self.xy = np.array([TO_UTM.transform(p[1], p[2]) for p in path])
        self.L = LineString(self.xy)
        seg = np.hypot(*np.diff(self.xy, axis=0).T); self.dv = np.concatenate([[0], np.cumsum(seg)])
    def c_of_d(self, d): return float(np.interp(d, self.dv, self.cv))
    def d_of_c(self, c): return float(np.interp(c, self.cv, self.dv))
    def chain(self, pt): return self.c_of_d(self.L.project(Point(pt)))
    def at(self, c): p = self.L.interpolate(self.d_of_c(c)); return (p.x, p.y)

_ds = rasterio.open(VRT)
def sample(xy, mode='bilinear'):
    """xy: array (n,2) UTM 16N (EPSG:26916). Returns metres (NaN for nodata)."""
    xy = np.asarray(xy, float)
    col = (xy[:, 0] - 695000.0) / 2.0 - 0.5; row = (4350000.0 - xy[:, 1]) / 2.0 - 0.5
    c0, r0 = int(np.floor(col.min())) - 2, int(np.floor(row.min())) - 2
    c1, r1 = int(np.ceil(col.max())) + 3, int(np.ceil(row.max())) + 3
    a = _ds.read(1, window=Window(c0, r0, c1 - c0, r1 - r0)).astype(float)
    a[a == -32768] = np.nan
    cc, rr = col - c0, row - r0
    if mode == 'nearest':
        return a[np.round(rr).astype(int), np.round(cc).astype(int)] / 10
    i, j = np.floor(rr).astype(int), np.floor(cc).astype(int); fr, fc = rr - i, cc - j
    v = (a[i, j] * (1 - fr) * (1 - fc) + a[i, j + 1] * (1 - fr) * fc + a[i + 1, j] * fr * (1 - fc) + a[i + 1, j + 1] * fr * fc)
    return v / 10

import glob, datetime
from shapely.geometry import shape, box, Polygon
from shapely.ops import unary_union, substring
def build():
    """the Deck's CUT and Norwood structures (S) and street re-grades (REG), in Deck UTM metres"""
    T = jload(DECK + '/tracks.json'); ST = jload(DECK + '/structures.json'); DK = jload(DECK + '/deck.json'); NW = jload(DECK + '/norwood.json')
    SUM = T['summary']; DV = SUM['dive']
    feat = lambda layer: [f for f in T['features'] if f['properties'].get('layer') == layer]
    stru = {f['properties']['name']: shape(f['geometry']) for f in ST['features'] if f['properties'].get('name')}
    RER_BOX, TROUGH, VIA = (1.0, 6.6), (0.8, 5.8), (1.6, 5.8)
    S = []
    def add(name, kind, geom, z, hb, src, short, plats=(), excl=(), cut=False):
        S.append(dict(name=name, kind=kind, geom=geom, z=z, below=hb[0], top=hb[1], open=kind not in ('box', 'tunnel'), plats=list(plats), src=src, short=short, excl=set(excl), cut=cut))
    # ---- CUT lower level (-2) ----
    lp = [shape(f['geometry']) for f in feat('lower_plat')]
    lt = [LineString(f['geometry']['coordinates']) for f in feat('lower') if f['properties'].get('kind') == 'platform']
    b = unary_union(lp + [l.buffer(2.5) for l in lt]).bounds
    add('CUT lower level (-2): eight through tracks, four islands', 'box', box(b[0] - 1, b[1], b[2] + 1, b[3]), lambda x, y: 144.0, RER_BOX,
        'Deck: lower platforms 305 m at rail 144.0 m, centred under the APEx field (log 10l.19, 10l.25); box drawn with the RER sizes', 'CUT lower level', plats=[(p, 144.0) for p in lp])
    def dive_z(y):
        n0, n1, z0, z1, g = DV['n0'], DV['portal'], DV['z0'], DV['z1'], DV['g'] / 100
        if y >= n1: return z0 - (n0 - min(y, n0)) * g
        zt = z1 - (n1 - y) * g
        if zt >= DV['z_sherman']: return zt
        ys = n1 - (z1 - DV['z_sherman']) / g
        return max(144.0, DV['z_sherman'] - (ys - y) * DV['g_tun'] / 100)
    named = lambda *keys: [LineString(f['geometry']['coordinates']) for f in feat('lower') if any(k in (f['properties'].get('name') or '') for k in keys)]
    north = unary_union([l.buffer(4.2) for l in named('Lower north fan', 'under the deck')]).intersection(box(712600, 4332042, 712950, DV['portal']))
    add('CUT lower pairs: tunnel from the Findlay portals to the lower platforms', 'box', north, lambda x, y: dive_z(y), RER_BOX,
        f"Deck: portals under Findlay {DV['z1']} m, {DV['g']}% to {DV['z_sherman']} m at Sherman, {DV['g_tun']}% to 144.0 m ({DV['L_cover']} m covered; log 10l.30, 10r.6)", 'CUT lower pairs (tunnel)')
    cutpoly = [shape(f['geometry']) for f in DK['features'] if f['properties'].get('name', '').startswith('Lower-pair dive, open cut')][0]
    add('CUT lower pairs: open cut, Bank to Findlay', 'trough', cutpoly, lambda x, y: dive_z(y), TROUGH,
        f"Deck: {DV['z0']} m over Bank (lowered 2.0 m), {DV['g']}% down over {DV['L']} m to {DV['z1']} m under Findlay (raised 2.0 m); Dayton, Exeter and York end at the cut walls (log 10l.30, 10r.5)", 'CUT lower pairs (open cut)', cut=True)
    south = unary_union([l.buffer(4.2) for l in named('to CS pair', 'to C&O pair')]).intersection(box(712600, 4331617, 712950, 4331738))
    add('CUT lower level: south throats to the CS and C&O pairs', 'box', south, lambda x, y: 144.0, RER_BOX, 'Deck: lower tracks A-D to the CS pair and E-H to the C&O pair, level at 144.0 m', 'CUT lower throats')
    def prof_z(c3):
        line = LineString([(x, y) for x, y, z in c3]); zs = np.array([z for x, y, z in c3])
        dd = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(np.array([(x, y) for x, y, z in c3]), axis=0).T))])
        return line, dd, (lambda x, y: float(np.interp(line.project(Point(x, y)), dd, zs)))
    icl, icd, icz = prof_z(SUM['prof']['intercity']['c'])
    ps = SUM['prof']['intercity']['portal_s']
    add('Intercity (CS) pair: tunnel to the W 8th portal', 'box', substring(icl, 0, ps).buffer(6.45, cap_style=2), icz, RER_BOX,
        f"Deck: from 144.0 m, 145.2 m under Gest, {SUM['cs_z8']} m under W 8th (street humped {SUM['cs_hump']} m), portal in the W 8th south wall {SUM['cs_portal']['z']} m (log 10l.21)", 'Intercity pair (tunnel)')
    add('Intercity (CS) pair: trough', 'trough', stru['Intercity pair: trough'], icz, TROUGH, 'Deck structures: open between retaining walls, rail 151.4 to 152.9 m', 'Intercity pair (trough)', cut=True)
    add('Intercity (CS) pair: viaduct to the CS bridge', 'viaduct', stru['Intercity pair: viaduct'], icz, VIA, 'Deck structures: on fill or viaduct, rail 152.9 to 163.9 m; CS bridge 164.0 m', 'Intercity pair (viaduct)')
    col, cod, coz = prof_z(SUM['prof']['co']['c'])
    tr = stru['C&O pair: trough']
    d_tr = min(col.project(Point(q)) for q in tr.exterior.coords)
    add('C&O pair: tunnel under Gest, W 8th and W 6th', 'box', substring(col, 0, d_tr).buffer(6.45, cap_style=2).difference(tr), coz, RER_BOX, 'Deck: level at 144.0 m under Gest, W 8th and W 6th (log 10l.21)', 'C&O pair (tunnel)')
    add('C&O pair: trough', 'trough', tr, coz, TROUGH, 'Deck structures: open between retaining walls, rail 144.6 to 148.2 m', 'C&O pair (trough)', cut=True)
    add('C&O pair: viaduct', 'viaduct', stru['C&O pair: viaduct'], coz, VIA, f"Deck structures: rail 148.2 to 160.3 m; {SUM['co_g']}% onto the TRIMET C&O viaduct (160.4 m)", 'C&O pair (viaduct)')
    add('C&O viaduct (TRIMET line, to the C&O bridge)', 'viaduct', stru['C&O viaduct (TRIMET line, to the C&O bridge)'], lambda x, y: SUM['co_merge_z'], VIA, 'Deck: the C&O pair on the TRIMET approach viaduct, 160.4 m (level held, not published further)', 'C&O viaduct (TRIMET)')
    # ---- APEx arch viaduct: rail = deck + 6.5 m (4.9 m street clearance + 1.6 m arch crown, fill and track) ----
    marks = sorted([(4330691, 164.0), (4330777, 163.4), (4331225, 161.7), (4331549, 160.3), (4332134, 160.3), (4332332, 161.1), (4334346, 164.5), (4335532, 166.6), (4336948, 162.5)])
    apex_z = lambda x, y: float(np.interp(y, [m[0] for m in marks], [m[1] for m in marks]))
    ap = [shape(f['geometry']) for f in feat('apex_plat')]
    add('CUT platform deck: APEx 1-14 and platform M on the arch viaduct', 'viaduct', stru['CUT platform deck'], lambda x, y: 160.3, VIA,
        'Deck: APEx platforms 160.3 m, level with the rotunda (10l.19, 10l.24); arches drawn to the street, no footing check (Ben, 26 October)', 'CUT platform deck', plats=[(p, 160.3) for p in ap], excl=('CVG_Express',))
    add('CUT approach viaduct (south)', 'viaduct', stru['CUT approach viaduct (south)'], apex_z, VIA, 'Deck: APEx 160.3 m at CUT, 161.7 m over W 8th, 163.4 m over W 6th, 164.0 m at the bridge', 'CUT approach viaduct', excl=('CVG_Express',))
    add('North arch viaduct', 'viaduct', stru['North arch viaduct'], apex_z, VIA,
        'Deck: one level, APEx 161.1 m over W Liberty, 164.5 m over Marshall, 166.6 m at the deck tip, 162.5 m at Ludlow (North Viaduct Plan); the upper level (Indianapolis and D, to 174.3 m) is not drawn', 'North arch viaduct', excl=('RER_2', 'RER_4'))
    fa, fb = (712678.0, 4336948.0, 162.5), (713475.0, 4337351.0, 152.0)
    def fill_z(x, y):
        t = ((x - fa[0]) * (fb[0] - fa[0]) + (y - fa[1]) * (fb[1] - fa[1])) / ((fb[0] - fa[0]) ** 2 + (fb[1] - fa[1]) ** 2)
        return fa[2] + clamp01(t) * (fb[2] - fa[2])
    clamp01 = lambda t: max(0.0, min(1.0, t))
    add('North trunk fill (Northside / Spring Grove to ground)', 'fill', stru['North trunk fill (Northside / Spring Grove to ground)'], fill_z, VIA, 'Deck: fill from the viaduct end (162.5 m at Ludlow) back to ground, 152.0 m', 'North trunk fill', excl=('RER_2', 'RER_4'))
    # ---- Norwood Central: surface tracks in a cut and the ORR / APEx trench ----
    nwf = {f['properties'].get('name'): f for f in NW['features'] if f['properties'].get('name')}
    T7 = LineString(nwf['APEx through track (north)']['geometry']['coordinates'])
    apx = [LineString(f['geometry']['coordinates']) for f in T['features'] if (f['properties'].get('name') or '').startswith('APEx Norwood (Transcontinental), track 1')][0]
    t7s = Point(T7.coords[0]); d_t7 = apx.project(t7s)
    west = substring(apx, 0, d_t7) if apx.project(Point(apx.coords[0])) < d_t7 else None
    REF = LineString(list(west.coords) + list(T7.coords)) if west is not None and west.length > 100 else None
    if REF is None:   # track runs the other way
        rv = LineString(apx.coords[::-1]); d2 = rv.project(t7s); REF = LineString(list(substring(rv, 0, d2).coords) + list(T7.coords))
    d_ref0 = REF.project(t7s)
    frame_s = lambda x, y: 4150.0 + REF.project(Point(x, y)) - d_ref0
    # the trench starts at the ground at s 3,220, falls 2% to 170.0 m, climbs 1.39% to 178.0 m and runs level
    # through the station (North Viaduct Plan; Deck marker)
    Z_3220 = round(float(sample([REF.interpolate(d_ref0 + 3220 - 4150).coords[0]])[0]), 1)
    S_LOW = 3220 + (Z_3220 - 170.0) / 0.02
    S_TOP = S_LOW + (178.0 - 170.0) / 0.0139
    def nw_z(x, y):
        s = frame_s(x, y)
        if s >= S_TOP: return 178.0
        if s >= S_LOW: return 170.0 + 0.0139 * (s - S_LOW)
        return min(Z_3220, 170.0 + 0.02 * (S_LOW - s))
    mk = [f for f in T['features'] if (f['properties'].get('name') or '') == 'Norwood trench'][0]['geometry']['coordinates']
    print(f'Norwood frame: trench marker at s {frame_s(*mk):.0f}; profile from the ground {Z_3220} m at s 3,220, 2% to 170.0 m at s {S_LOW:.0f}, 1.39% to 178.0 m at s {S_TOP:.0f}, level on')
    surf = [LineString(f['geometry']['coordinates']) for f in NW['features'] if f['properties'].get('layer') == 'nw_track' and not f['properties'].get('tunnel') and f['properties'].get('track') not in ('W1', 'W2')]
    npl = [(shape(f['geometry']), f['properties'].get('label')) for f in NW['features'] if f['properties'].get('layer') == 'nw_plat']
    trench = [l for l in [LineString(f['geometry']['coordinates']) for f in T['features'] if (f['properties'].get('name') or '').startswith(('APEx Norwood (Transcontinental)', 'Lower-level pair E, track'))]]
    tz = []
    for l in trench:
        keep = [q for q in l.coords if 3220 <= frame_s(*q) <= 4160 and Point(q).distance(REF) < 80]
        if len(keep) > 1: tz.append(LineString(keep))
    field = unary_union([l.buffer(4.2) for l in surf] + [p.buffer(0.5) for p, _ in npl] + [l.buffer(4.2) for l in tz]).buffer(10).buffer(-10)   # one cut across the track field
    add('Norwood Central: ORR, APEx and Transvalley tracks in the cut, with the trench', 'atgrade', field, nw_z, TROUGH,
        f'Deck sketch v13 and North Viaduct Plan: ORR and APEx from the ground at s 3,220 ({Z_3220} m), 2% down to about 170.0 m at s {S_LOW:.0f}, 1.39% up to 178.0 m at s {S_TOP:.0f}, level through the station; platforms about 178 m, roofs at street level (levels approximate, from the ground data); not editable here (Ben, 26 October)',
        'Norwood Central tracks', plats=[(p, 178.0) for p, _ in npl], cut=True)
    # ---- street re-grades over the dive and the W 8th hump ----
    streets = {}
    for f in DK['features']:
        p = f['properties']
        if f['geometry']['type'] == 'LineString' and p.get('name'): streets.setdefault(p['name'], []).append((LineString(f['geometry']['coordinates']), p.get('width_m') or 18.3))
    REG = []
    def street_reg(name, dz_of, src, pick=lambda l: True):
        for l, w in streets[name]:
            if pick(l): REG.append(dict(name=name, band=l.buffer(w / 2, cap_style=2), dz=dz_of, src=src))
    w8 = [(712500, 0.0), (712600, 5.0), (712671, 5.0), (712806, 2.5), (712941, 0.0)]
    street_reg('W 8th (viaduct line)', lambda x, y: float(np.interp(x, [a for a, _ in w8], [b for _, b in w8], left=0, right=0)),
               'Deck: W 8th raised 5 m over the intercity pair (150.9 m), 2.5 m at the APEx; ramps: 100 m west of Horne as on Horne, east at the same grade to zero (drawing values)')
    hl = [l for l, w in streets['Horne line']][0]; h0 = hl.project(hl.intersection(streets['W 8th (viaduct line)'][0][0]))
    street_reg('Horne line', lambda x, y: max(0.0, 5.0 * (1 - abs(hl.project(Point(x, y)) - h0) / 100.0)), 'Deck: Horne raised 5 m at W 8th, ramps about 100 m', pick=lambda l: l.distance(Point(712654, 4331230)) < 30)
    def across(dz):
        return lambda x, y: dz * max(0.0, min(1.0, 1 - (max(712733 - x, x - 712787, 0)) / 60.0))
    street_reg('Findlay', across(2.0), 'Deck: Findlay raised 2.0 m over the lower pairs (ramps 60 m, drawing value)')
    street_reg('Bank', across(-2.0), 'Deck: Bank lowered 2.0 m under the lower pairs (ramps 60 m, drawing value)', pick=lambda l: l.bounds[2] > 712700)
    structure_types(S, streets, icl, icz, col, coz)
    return dict(S=S, REG=REG, T=T, NW=NW, DK=DK, stru=stru, apex_z=apex_z, nw_z=nw_z, frame_s=frame_s, streets=streets)


# ---- structure types at CUT (Ben, 26 October) ----
# - the fan from W 9th to W Liberty (the CUT platform deck and its throats): an embankment, with a bridge over each
#   street (as at Amsterdam Centraal);
# - the wide multi-track structures, the south approach from W 9th to the Cardinal crossing (where the CVG Express
#   crosses the Cardinal pair and the tracks split) and the north trunk: arch viaducts, each arch spanning a street,
#   the piers along the street edges; solid between the streets (drawing rule);
# - south of the Cardinal crossing, the intercity and C&O viaducts and the TRIMET C&O viaduct: normal viaducts on
#   piers; the intercity and C&O descents, where the rail is less than 6.5 m above the ground (4.9 m street clearance
#   + 1.6 m), are embankments with blind arches on the faces (drawing rule for where a descent ends).
# Each structure keeps its kind for the Rail Profiles page ('fill' for an embankment, 'viaduct' for either viaduct) and
# gains st (embankment, arch, viaduct) and gaps (the street openings: bridges or arches). Levels are unchanged.
FAN_STREETS = ('W 9th', 'Richmond', 'Court', 'Gest', 'Oehler', 'Clark', 'Courtland', 'Flint', 'Wade', 'Wilstach', 'W Liberty')
CARDINAL_X = (712795.0, 4331005.0)   # the CVG Express across the Cardinal pair (Deck tracks), about
STREET_CLEAR = 6.5                   # rail above the ground below which a descent is an embankment


def _extend(line, d=600.0):
    c = list(line.coords)
    (x0, y0), (x1, y1) = c[0], c[1]
    (xa, ya), (xb, yb) = c[-2], c[-1]
    u0, u1 = math.hypot(x0 - x1, y0 - y1) or 1, math.hypot(xb - xa, yb - ya) or 1
    return LineString([(x0 + (x0 - x1) / u0 * d, y0 + (y0 - y1) / u0 * d)] + c + [(xb + (xb - xa) / u1 * d, yb + (yb - ya) / u1 * d)])


def _side(poly, line, north=True):
    """the part of poly on the north (larger y) side of an extended line"""
    from shapely.ops import split
    out = []
    for g in getattr(poly, 'geoms', [poly]):
        for piece in split(g, line).geoms:
            q = piece.representative_point()
            d = line.project(q); p0 = line.interpolate(d)
            if (q.y > p0.y) == north:
                out.append(piece)
    return unary_union(out) if out else Polygon()


def structure_types(S, streets, icl, icz, col, coz):
    by = {st['short']: st for st in S}
    band = lambda nm: unary_union([l.buffer(w / 2, cap_style=2) for l, w in streets.get(nm, [])])
    def we(line):   # west to east, so that a positive offset is the north side
        return line if line.coords[0][0] < line.coords[-1][0] else LineString(line.coords[::-1])
    def edge(nm, north):   # a street's north or south edge, extended
        l = we(max([l for l, w in streets[nm]], key=lambda l: l.length))
        return we(_extend(l.offset_curve((1 if north else -1) * max(w for _, w in streets[nm]) / 2)))
    w9s, wln = edge('W 9th', False), edge('W Liberty', True)
    w8 = max([l for l, w in streets['W 8th (viaduct line)']], key=lambda l: l.length)
    d8 = w8.project(Point(CARDINAL_X)); p8 = w8.interpolate(d8)   # the Cardinal cut: parallel to W 8th, through the crossing
    card = _extend(LineString([(x + CARDINAL_X[0] - p8.x, y + CARDINAL_X[1] - p8.y) for x, y in w8.coords]))
    all_bands = {nm: band(nm) for nm in streets}
    def gaps(geom, names=None):
        out = []
        for nm, b in all_bands.items():
            if names and nm not in names:
                continue
            g = geom.intersection(b)
            if g.area > 20:
                out.append((nm, g))
        return out
    deck, appr, north = by['CUT platform deck'], by['CUT approach viaduct'], by['North arch viaduct']
    fan_geom = unary_union([deck['geom'], _side(appr['geom'], w9s, True), _side(north['geom'], wln, False)]).buffer(0.01).buffer(-0.01)
    arch_s = _side(_side(appr['geom'], w9s, False), card, True)
    norm_s = _side(appr['geom'], card, False)
    north_arch = _side(north['geom'], wln, True)
    deck.update(name='CUT fan, W 9th to W Liberty: APEx 1-14, platform M and the throats on an embankment', short='CUT fan (embankment)',
                kind='fill', st='embankment', geom=fan_geom, z=appr['z'], gaps=gaps(fan_geom, FAN_STREETS),
                src='Deck: APEx platforms 160.3 m, level with the rotunda (10l.19, 10l.24); an embankment with a bridge over each street, W 9th to W Liberty, as at Amsterdam Centraal (Ben, 26 October)')
    appr.update(name='CUT south approach: arch viaduct, W 9th to the Cardinal crossing', short='CUT south arch viaduct', st='arch', geom=arch_s, gaps=gaps(arch_s),
                src=appr['src'] + '; an arch viaduct over the streets while the tracks run together, to the Cardinal crossing (Ben, 26 October)')
    S.insert(S.index(appr) + 1, dict(appr, name='CUT south approach: viaducts south of the Cardinal crossing', short='CUT south approach (viaduct)',
                                     st='viaduct', geom=norm_s, gaps=[], src=appr['src'] + '; normal viaducts once the tracks split (Ben, 26 October)'))
    north.update(geom=north_arch, st='arch', gaps=gaps(north_arch), src=north['src'] + '; arches over the streets, piers on the street edges (Ben, 26 October)')
    by['North trunk fill'].update(st='embankment', gaps=gaps(by['North trunk fill']['geom']))
    for short, line, zf in (('Intercity pair (viaduct)', icl, icz), ('C&O pair (viaduct)', col, coz)):
        st = by[short]
        ds = np.arange(0, line.length, 5.0)
        pts = [line.interpolate(d) for d in ds]
        inside = [st['geom'].buffer(1).contains(q) for q in pts]
        h = np.array([zf(q.x, q.y) for q in pts]) - sample(np.array([(q.x, q.y) for q in pts]))
        low = [d for d, i, hh in zip(ds, inside, h) if i and hh < STREET_CLEAR]
        if not low:
            st['st'], st['gaps'] = 'viaduct', []
            continue
        from shapely.ops import substring
        emb = st['geom'].intersection(substring(line, min(low) - 2.5, max(low) + 2.5).buffer(40, cap_style=2))
        via = st['geom'].difference(emb)
        st.update(st='viaduct', gaps=[], geom=via, src=st['src'] + '; a normal viaduct (Ben, 26 October)')
        S.insert(S.index(st), dict(st, name=st['name'].replace('viaduct', 'descent') + ' (embankment, blind arches)', short=short.replace('viaduct', 'descent'),
                                   kind='fill', st='embankment', blind=True, geom=emb, gaps=[],
                                   src=st['src'].split(';')[0] + f'; the descent, rail under {STREET_CLEAR} m above the ground: an embankment with blind arches on the faces (Ben, 26 October)'))
    by['C&O viaduct (TRIMET)'].update(st='viaduct', gaps=[])
    for st in S:
        st.setdefault('st', st['kind'])
        st.setdefault('gaps', [])


def main():
    B = build(); S, REG = B['S'], B['REG']
    # ---- project onto every line ----
    out = {}
    files = sorted(glob.glob(SITE + '/lines/*_*.json')) + sorted(glob.glob(SITE + '/rer/lines/RER_*.json'))
    r2 = lambda v: round(float(v), 2)
    for fn in files:
        d = jload(fn); P = Path(d['path']); lid = d['id']; blocks = []; env = P.L.envelope.buffer(50)
        for st in S:
            if lid in st['excl'] or not env.intersects(st['geom']): continue
            hit = P.L.intersection(st['geom'])
            segs = [g for g in getattr(hit, 'geoms', [hit]) if g.geom_type == 'LineString' and g.length > 1.0]
            iv = sorted([sorted((P.chain(g.coords[0]), P.chain(g.coords[-1]))) for g in segs])
            merged = []
            for a, b in iv:
                if merged and a - merged[-1][1] < 3: merged[-1][1] = max(merged[-1][1], b)
                else: merged.append([a, b])
            for a, b in merged:
                cs = list(np.arange(a, b, 5.0)) + [b]
                pts = [[round(c, 1), r2(st['z'](*P.at(c)))] for c in cs]
                pl = []
                for poly, z in st['plats']:
                    h = P.L.intersection(poly)
                    for g in getattr(h, 'geoms', [h]):
                        if g.geom_type == 'LineString' and g.length > 0.5:
                            u, v = sorted((P.chain(g.coords[0]), P.chain(g.coords[-1]))); pl.append([round(u, 1), round(v, 1), z])
                gp = []   # street openings (bridges, arches) along this line, with the street
                for nm, gg in st['gaps']:
                    h = P.L.intersection(gg)
                    for g in getattr(h, 'geoms', [h]):
                        if g.geom_type == 'LineString' and g.length > 0.5:
                            u, v = sorted((P.chain(g.coords[0]), P.chain(g.coords[-1])))
                            if v >= a - 1 and u <= b + 1: gp.append([round(u, 1), round(v, 1), nm])
                blk = dict(n=st['name'], l=st['short'], k=st['kind'], st=st['st'], c0=round(a, 1), c1=round(b, 1), p=pts, b=st['below'], t=st['top'], o=st['open'], pl=sorted(pl), s=st['src'])
                if st['st'] in ('embankment', 'arch'): blk['gaps'] = sorted(gp)
                blocks.append(blk)
        # ground runs: street re-grades (add) and open cuts (cap at the trough floor)
        step, n = d['step_m'], len(d['ground_dm'])
        add_v, cap_v, used = {}, {}, set()
        for rg in REG:
            if not env.intersects(rg['band']): continue
            h = P.L.intersection(rg['band'])
            for g in getattr(h, 'geoms', [h]):
                if g.geom_type != 'LineString' or g.length < 0.5: continue
                u, v = sorted((P.chain(g.coords[0]), P.chain(g.coords[-1])))
                for i in range(int(math.ceil(u / step)), int(math.floor(v / step)) + 1):
                    dz = rg['dz'](*P.at(i * step))
                    if abs(dz) > 0.01: used.add(rg['src'])
                    if abs(dz) > 0.01 and abs(dz) > abs(add_v.get(i, 0)): add_v[i] = dz   # crossing streets: the larger re-grade, not the sum
        for st in S:
            if not st['cut'] or lid in st['excl'] or not env.intersects(st['geom']): continue
            h = P.L.intersection(st['geom'])
            for g in getattr(h, 'geoms', [h]):
                if g.geom_type != 'LineString' or g.length < 0.5: continue
                u, v = sorted((P.chain(g.coords[0]), P.chain(g.coords[-1])))
                for i in range(int(math.ceil(u / step)), int(math.floor(v / step)) + 1):
                    z = st['z'](*P.at(i * step)) - st['below']; cap_v[i] = min(cap_v.get(i, 1e9), z)
        def runs(m):
            rs = []
            for i in sorted(m):
                if rs and i == rs[-1]['i0'] + len(rs[-1]['v']): rs[-1]['v'].append(r2(m[i]))
                else: rs.append({'i0': i, 'v': [r2(m[i])]})
            return rs
        rec = {}
        if blocks: rec['blocks'] = sorted(blocks, key=lambda x: x['c0'])
        if add_v: rec['add'] = runs(add_v); rec['add_src'] = sorted(used)
        if cap_v: rec['cap'] = runs(cap_v)
        if rec: out[lid] = rec
    meta = {'built': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), 'source': 'Mill Creek Deck published version 1793028977-4bc6 (tracks.json, structures.json, deck.json, norwood.json); layout version 2461',
            'heights': 'from each structure\'s rail: box 1.0 m below, 6.6 m above (RER sizes, 25 kV); trough and at grade 0.8 m track bed, 5.8 m clear above; viaduct 1.6 m to the arch underside (Deck rule), 5.8 m clear above',
            'structure_types': 'st: embankment (k fill; the CUT fan W 9th to W Liberty, the north trunk fill, the intercity and C&O descents), arch (k viaduct; the south approach to the Cardinal crossing, the north arch viaduct) or viaduct (normal). gaps: the street openings on an embankment or arch viaduct along the line [c0, c1, street]; a line in the open crosses only inside one (Ben, 26 October)',
            'notes': ['Lower-pair levels rebuilt from the Deck dive figures (Ben, 26 October: until the Deck publishes a level per point)', 'Norwood levels approximate, from the ground data (North Viaduct Plan)', 'W 8th ramp ends and the Bank and Findlay ramps are drawing values']}
    import os; os.makedirs(SITE + "/context", exist_ok=True); jsave(SITE + "/context/lines.json", {"meta": meta, "lines": out})
    for k, v in out.items(): print(k, [(b["l"], b["c0"], b["c1"], b["p"][0][1]) for b in v.get("blocks", [])], "add" in v and sum(len(r["v"]) for r in v["add"]), "cap" in v and sum(len(r["v"]) for r in v["cap"]))


if __name__ == '__main__':
    main()
