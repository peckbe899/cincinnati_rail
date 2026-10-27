"""The other systems at Union Terminal (CUT) and Norwood Central, for Station 3D.

The structures come from the same definitions as the Rail Profiles context (tools/make_profile_context.py build()),
so both tools draw the same thing: the lower level (-2) box, the lower-pair tunnel and open cut (the dive), the
south throats, the intercity and C&O pairs (tunnel, trough, viaduct), the CUT platform deck, the approach viaduct,
the north arch viaduct, the trunk fill, the river bridges and the Norwood Central cut. The Union Terminal TRI box is
drawn round the Deck's three box islands at the Profiles level.

Also: the APEx, lower-level and Norwood tracks at those structures' levels (a track outside every structure stays
unlevelled), the APEx, lower and Norwood platforms, viaduct piers down to the street, and finished-ground tiles at
10 m (the map 3 ground, the Deck's street re-grades, the floors of the open cuts).

Rulings (Ben, 2026-10-26): one Union Terminal TRI box level (the Profiles level, 135.7 m); arches drawn to the
street, no footing check; the Deck's street re-grades are finished ground; lower-pair levels from the Deck's dive
figures until it publishes a level per point; the Norwood ORR, Transvalley and APEx tracks are fixed context.
Drawing values: the 20 m pier spacing and 2 m pier thickness; platform tops 1.0 m above the rail.

Coordinates: the Deck's UTM metres less the snapshot origin (E0, N0), as sync.py does for the Deck's tracks.
"""
import math
import os
import sys

import numpy as np
import shapely
import shapely.prepared
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

TILE = 400.0          # finished-ground tiles: two cells of the snapshot's 200 m grid, aligned to it
TSTEP = 10.0          # finished-ground spacing inside a tile
DENS = 5.0            # outline points at most this far apart
SPAN = 20.0           # pier spacing along a viaduct (drawing value)
PIER = 2.0            # pier thickness (drawing value)
TRACK_STEP = 5.0
PLAT_ABOVE = 1.0
APEX_FAM = ('CUT platform deck', 'CUT approach viaduct', 'North arch viaduct', 'North trunk fill')
BRIDGES = {   # Deck structures.json bridges and their rail level (Deck notes and log)
    'APEx bridge': (164.0, 'apex', 'Deck: APEx 164.0 m at the bridge'),
    'CVG Express span': (164.0, 'apex', 'Deck: about 164 m, beside the APEx bridge'),
    'Cincinnati Southern bridge (1922)': (164.0, 'lower', 'Deck: CS bridge 164.0 m (intercity pair)'),
    'C&O bridge (1929)': (160.4, 'lower', 'Deck: the C&O pair at 160.4 m on the TRIMET approach'),
    'Ludlow underbridge': (162.5, 'apex', 'Deck: rail 162.5 m over Ludlow Avenue'),
}
SYS_COL = {'apex': '1baf7a', 'orr': 'eda100', 'tv': 'e87ba4', 'bay': 'eda100', 'ic': 'eda100'}


def enc(vals, scale):
    out, prev = [], 0
    for v in vals:
        q = int(round(float(v) * scale))
        out.append(q - prev)
        prev = q
    return out


def densify(coords, step=DENS):
    c = [tuple(map(float, q[:2])) for q in coords]
    if len(c) > 1 and c[0] == c[-1]:
        c = c[:-1]
    out = []
    for a, b in zip(c, c[1:] + c[:1]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(math.ceil(L / step)))
        for k in range(n):
            out.append((a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n))
    return out


def polys(g):
    if g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, MultiPolygon):
        return list(g.geoms)
    return [q for q in getattr(g, 'geoms', []) if isinstance(q, Polygon)]


def build(E0, N0, ut_islands=None):
    """ut_islands: [(ring [[x, y] local], rail)] for the Union Terminal TRI box islands (sync.py's platforms)"""
    import make_profile_context as mpc
    B = mpc.build()
    S, REG, T, NW, stru = B['S'], B['REG'], B['T'], B['NW'], B['stru']
    for st in S:
        st['fam'] = 'apex' if st['name'].startswith(APEX_FAM) else 'nw' if st['name'].startswith('Norwood') else 'lower'
    for nm, (z, fam, src) in BRIDGES.items():
        if nm in stru:
            S.append(dict(name=nm, short=nm, kind='bridge', geom=stru[nm], z=(lambda zz: lambda x, y: zz)(z), below=1.6, top=5.8,
                          open=True, plats=[], src=src, excl=set(), cut=False, fam=fam))
    loc = lambda x, y: (x - E0, y - N0)

    # finished ground at Deck UTM points: map 3 ground, + street re-grades (the larger where two cross), capped at cut floors
    cuts = [st for st in S if st['cut']]

    def finished(xy):
        xy = np.asarray(xy, float)
        z = mpc.sample(xy)
        dz = np.zeros(len(xy))
        for rg in REG:
            m = shapely.contains_xy(rg['band'], xy[:, 0], xy[:, 1])
            for i in np.where(m)[0]:
                v = rg['dz'](*xy[i])
                if abs(v) > abs(dz[i]):
                    dz[i] = v
        z = z + dz
        for st in cuts:
            m = shapely.contains_xy(st['geom'], xy[:, 0], xy[:, 1])
            for i in np.where(m)[0]:
                z[i] = min(z[i], st['z'](*xy[i]) - st['below'])
        return z

    items, notes = [], []
    # ---- structures ----
    for st in S:
        out = []
        for p in polys(st['geom']):
            p = p.buffer(0)
            for q in polys(p):
                rings = [densify(q.exterior.coords)] + [densify(h.coords) for h in q.interiors]
                rr = []
                for ring in rings:
                    a = np.array(ring)
                    zr = [st['z'](x, y) for x, y in ring]
                    g = finished(a)
                    rr.append({'x': enc(a[:, 0] - E0, 10), 'y': enc(a[:, 1] - N0, 10), 'z': enc(zr, 100), 'g': enc(np.nan_to_num(g, nan=float(np.nanmean(g))), 100)})
                out.append(rr)
        if out:
            items.append({'type': 'struct', 'n': st['name'], 'l': st['short'], 'k': st['kind'], 'f': st['fam'], 'b': st['below'], 't': st['top'],
                          's': st['src'], 'polys': out})

    # ---- tracks: each at the level of the structure it runs in (its own family first) ----
    tracks = []
    for f in T['features']:
        p, g = f['properties'], f['geometry']
        if p.get('layer') not in ('apex', 'lower', 'passing') or g['type'] != 'LineString':
            continue
        nm = p.get('name') or ''
        if 'CVG Express' in nm or nm.startswith('Track 1'):
            continue   # the CVG Express is a Profiles line
        if p['layer'] == 'lower' or nm.startswith(('Lower', 'Transvalley', 'R5', 'C&O', 'CS line', 'Intercity')):
            sysk = 'tv' if nm.startswith('Transvalley') else 'orr'
            fams = ('lower', 'nw', 'apex')
        else:
            sysk, fams = 'apex', ('apex', 'nw')
        tracks.append((nm, sysk, fams, g['coordinates']))
    for f in NW['features']:
        p, g = f['properties'], f['geometry']
        if p.get('layer') != 'nw_track' or p.get('tunnel') or p.get('track') in ('W1', 'W2'):
            continue
        tracks.append(('Norwood ' + p.get('name', ''), p.get('sys', 'apex'), ('nw',), g['coordinates']))
    prep = [(st, shapely.prepared.prep(st['geom'].buffer(2.0))) for st in S]
    unlev = []
    nlev = 0
    for nm, sysk, fams, coords in tracks:
        L = LineString([tuple(q[:2]) for q in coords])
        if L.length < 2:
            continue
        n = max(2, int(math.ceil(L.length / TRACK_STEP)) + 1)
        pts = [L.interpolate(L.length * k / (n - 1)) for k in range(n)]
        zs = []
        for q in pts:
            z = None
            for fam in fams:
                for st, pp in prep:
                    if st['fam'] == fam and pp.contains(q):
                        z = st['z'](q.x, q.y)
                        break
                if z is not None:
                    break
            zs.append(z)
        run, runs = None, []
        for q, z in zip(pts, zs):
            k = z is not None
            if run is None or run[0] != k:
                run = [k, []]
                runs.append(run)
            run[1].append((q.x, q.y, z))
        for k, seg in runs:
            if len(seg) < 2:
                continue
            a = np.array([(x, y) for x, y, _ in seg])
            if k:
                items.append({'type': 'rail', 'n': nm, 'sys': sysk, 'col': SYS_COL.get(sysk, '1baf7a'), 'x': enc(a[:, 0] - E0, 10), 'y': enc(a[:, 1] - N0, 10),
                              'z': enc([z for _, _, z in seg], 100)})
                nlev += 1
            else:
                unlev.append({'deck_line': nm, 'sys': sysk, 'from': 'Deck tracks.json', 'x': enc(a[:, 0] - E0, 10), 'y': enc(a[:, 1] - N0, 10)})

    # ---- platforms ----
    plats = [(shapely.geometry.shape(f['geometry']), 160.3, 'apex', f['properties'].get('name')) for f in T['features'] if f['properties'].get('layer') == 'apex_plat']
    plats += [(shapely.geometry.shape(f['geometry']), 144.0, 'orr', f['properties'].get('name')) for f in T['features'] if f['properties'].get('layer') == 'lower_plat']
    plats += [(shapely.geometry.shape(f['geometry']), 178.0, f['properties'].get('sys', 'apex'), f['properties'].get('name')) for f in NW['features'] if f['properties'].get('layer') == 'nw_plat']
    for poly, rail, sysk, nm in plats:
        for q in polys(poly):
            a = np.array(q.exterior.coords[:-1])
            items.append({'type': 'plat', 'n': nm, 'sys': sysk, 'rail': rail, 'top': round(rail + PLAT_ABOVE, 2), 'x': enc(a[:, 0] - E0, 100), 'y': enc(a[:, 1] - N0, 100)})

    # ---- the Union Terminal TRI box, round the Deck's three box islands ----
    if ut_islands:
        rings = [Polygon(r) for r, _ in ut_islands]
        rail = min(z for _, z in ut_islands if z is not None)
        mrr = unary_union(rings).minimum_rotated_rectangle
        bx = mrr.buffer(5.0, join_style=2)   # outer track 1.75 m off the island edge, wall 3.25 m outside it (sync.py BOX_MARGIN)
        a = np.array(densify(bx.exterior.coords))
        items.append({'type': 'struct', 'n': 'Union Terminal TRI box (A, B, D)', 'l': 'Union Terminal TRI box', 'k': 'box', 'f': 'tri', 'b': 1.0, 't': 6.6,
                      's': f'Deck: three box islands (A and B north, D centre, B and A south); rail {rail:.1f} m, the Profiles level (Ben, 26 October: one level for RER-1, 2 and 4); RER box sizes; walls 5.0 m outside the islands (assumed)',
                      'polys': [[{'x': enc(a[:, 0], 10), 'y': enc(a[:, 1], 10), 'z': enc([rail] * len(a), 100), 'g': enc([rail + 10] * len(a), 100)}]], 'local': True})

    # ---- piers: across each viaduct every SPAN m, along its longest track, from the street to the arch underside ----
    railsets = {}
    for nm, sysk, fams, coords in tracks:
        railsets.setdefault(fams[0], []).append(LineString([tuple(q[:2]) for q in coords]))
    npier = 0
    for st in S:
        if st['kind'] != 'viaduct':
            continue
        for q in polys(st['geom']):
            cands = [l.intersection(q) for l in railsets.get(st['fam'], []) + railsets.get('apex', []) + railsets.get('lower', [])]
            segs = [g for c in cands for g in (getattr(c, 'geoms', [c])) if g.geom_type == 'LineString' and g.length > SPAN]
            if not segs:
                continue
            spine = max(segs, key=lambda g: g.length)
            for d in np.arange(SPAN / 2, spine.length, SPAN):
                c = spine.interpolate(d)
                a, b = spine.interpolate(max(0, d - 1)), spine.interpolate(min(spine.length, d + 1))
                tx, ty = b.x - a.x, b.y - a.y
                Ln = math.hypot(tx, ty) or 1
                nx_, ny_ = -ty / Ln, tx / Ln
                cut = LineString([(c.x - nx_ * 150, c.y - ny_ * 150), (c.x + nx_ * 150, c.y + ny_ * 150)]).intersection(q)
                parts = [g for g in getattr(cut, 'geoms', [cut]) if g.geom_type == 'LineString' and g.distance(c) < 0.5]
                if not parts:
                    continue
                seg = parts[0]
                zt = st['z'](c.x, c.y) - st['below']
                (x0, y0), (x1, y1) = seg.coords[0], seg.coords[-1]
                gz = finished(np.array([[x0, y0], [c.x, c.y], [x1, y1]]))
                if np.isnan(gz).all() or zt - np.nanmax(gz) < 1.0:
                    continue
                hx, hy = tx / Ln * PIER / 2, ty / Ln * PIER / 2
                ring = [(x0 - hx, y0 - hy), (x1 - hx, y1 - hy), (x1 + hx, y1 + hy), (x0 + hx, y0 + hy)]
                items.append({'type': 'pier', 'of': st['short'], 'x': [round(x - E0, 1) for x, _ in ring], 'y': [round(y - N0, 1) for _, y in ring],
                              'zt': round(zt, 2), 'zb': [round(float(np.nan_to_num(gz[0], nan=np.nanmin(gz))), 2), round(float(np.nan_to_num(gz[2], nan=np.nanmin(gz))), 2)]})
                npier += 1

    # ---- finished-ground tiles round every structure and re-grade, aligned to the snapshot's 200 m grid ----
    return dict(items=items, unlevelled=unlev, finished=finished, region=unary_union([st['geom'] for st in S] + [rg['band'] for rg in REG]),
                counts={'structures': sum(1 for i in items if i['type'] == 'struct'), 'rails': nlev, 'unlevelled': len(unlev),
                        'platforms': sum(1 for i in items if i['type'] == 'plat'), 'piers': npier},
                sources=['Mill Creek Deck tracks.json, structures.json, deck.json, norwood.json (data/deck)', 'Rail Profiles context definitions (tools/make_profile_context.py)',
                         'map 3 ground (data/profile/dem)'])


def tiles(ctx, E0, N0, gx0, gy0):
    """finished-ground tiles (local coordinates) covering the structures and re-grades, 150 m round them"""
    reg = ctx['region'].buffer(150)
    x0, y0, x1, y1 = reg.bounds
    out = []
    i0, i1 = int(math.floor((x0 - E0 - gx0) / TILE)), int(math.ceil((x1 - E0 - gx0) / TILE))
    j0, j1 = int(math.floor((y0 - N0 - gy0) / TILE)), int(math.ceil((y1 - N0 - gy0) / TILE))
    n = int(TILE / TSTEP) + 1
    for i in range(i0, i1):
        for j in range(j0, j1):
            tx, ty = gx0 + i * TILE, gy0 + j * TILE
            if not reg.intersects(shapely.geometry.box(tx + E0, ty + N0, tx + TILE + E0, ty + TILE + N0)):
                continue
            xs, ys = np.meshgrid(tx + np.arange(n) * TSTEP, ty + np.arange(n) * TSTEP)
            z = ctx['finished'](np.c_[xs.ravel() + E0, ys.ravel() + N0])
            if np.isnan(z).all():
                continue
            z = np.where(np.isnan(z), np.nanmean(z), z)
            out.append({'i': i, 'j': j, 'x0': round(tx, 1), 'y0': round(ty, 1), 'step': TSTEP, 'n': n, 'z': enc(z, 10)})
    return out
