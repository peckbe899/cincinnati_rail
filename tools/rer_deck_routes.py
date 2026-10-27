"""The RER routes of the Rail Profiles page, tied to the Mill Creek Deck's route pieces (Ben, 2026-10-27: "tie the rail
profiles to the corresponding deck ROWs, so that it always pulls from the correct path").

Each route file (data/profile/rer/lines/RER_<letter>_<name>.json) records the Deck pieces it is built from in `segs`:
the piece id, the stretch of it used (`u` and `v`, its ends, and `pa`/`pb`, the distances along the piece) and the
route chainage it covers (`c0`, `c1`). The Deck is the authority for the plan: this tool rebuilds every route's path
from the Deck's current pieces and compares it with the route file.

    python tools/rer_deck_routes.py                      # check against data/deck/context.json (the Deck's published file)
    python tools/rer_deck_routes.py --geojson F          # check against a live Deck export (Station 3D harness: Ben's edits)
    python tools/rer_deck_routes.py --apply [--db DIR]   # rebuild the routes that drifted, and move everything tied to them

A piece is found by its id; if the Deck no longer has that id, by the nearest piece carrying the same letter. Each seg is
cut from the piece between the projections of its ends (`u`, `v`), so a piece the Deck redraws or extends is followed.

--apply rebuilds a drifted route and carries over, by a chainage map built seg by seg (old seg chainage to new):
the path, ground (map 3 raster, else the old ground at the mapped chainage), stations (at the Deck's station point of the
same name, else mapped), rivers, crossings with the other routes and Metro lines (recomputed), the segs, the line index,
the plan network, the canon (fixed and locked stretches: c0, c1, bend points, painted structure), rer/links.json
(junction chainages and points, shared stretches) and the saved profiles (repo copies in rer/alignments, and with --db
the page database's alignments exported to DIR, written back the same way: bend points, painted structure, length).
The moved database documents are left in DIR for writing to the page; republish the page's files after.
"""
import argparse
import glob
import json
import math
import os
import sys

import numpy as np
from pyproj import Transformer
from shapely.geometry import LineString, Point

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SITE = os.path.join(ROOT, 'data', 'profile')
TO_UTM = Transformer.from_crs(4326, 26916, always_xy=True)
TO_LL = Transformer.from_crs(26916, 4326, always_xy=True)
TOL = 0.5          # a route more than this far from its Deck pieces has drifted (m)
SIMPLIFY = 0.02    # path vertices: the Deck's own, less those within this of a straight line (m)
STATION_REACH = 300.0
STATION_TOL = 1.0   # a station more than this from its Deck platform's centre has drifted (m)


def jload(p):
    return json.load(open(p, encoding='utf8'))


def jsave(p, d, indent=None):
    with open(p, 'w', encoding='utf8') as f:
        json.dump(d, f, ensure_ascii=False, indent=indent, separators=(',', ':') if indent is None else None)


LIVE = os.path.join(ROOT, 'data', 'deck', 'rer_routes.geojson')


def deck_pieces(context=None, geojson=None):
    """{piece id: (letters label, UTM polyline)}: from a GeoJSON export of the Deck page (rer_line; default
    data/deck/rer_routes.geojson, the page with Ben's saved edits), or from its published context.json"""
    out = {}
    if geojson is None and context is None and os.path.exists(LIVE):
        geojson = LIVE
    if geojson:
        for f in jload(geojson)['features']:
            p = f['properties']
            if p.get('layer') not in ('rer_line', 'metro_line') or f['geometry']['type'] != 'LineString':
                continue
            xy = [TO_UTM.transform(*q[:2]) for q in f['geometry']['coordinates']]
            out[p['id']] = (p.get('name', ''), xy)
    else:
        for x in jload(context or os.path.join(ROOT, 'data', 'deck', 'context.json'))['rer']:
            out[x['id']] = (x.get('name', ''), [tuple(q[:2]) for q in x['c']])
    return out


def is_metro(rid):
    return rid.startswith('Line_') or rid == 'CVG_Express'


def st_keys(route):
    """the page's station keys (name, or name#index where a name repeats)"""
    nm = [s['name'] for s in route['stations']]
    return [n if nm.count(n) == 1 else f'{n}#{i}' for i, n in enumerate(nm)]


def slides(route, doc):
    """[platform slide from the station point] per station, from the saved profile (`so`, by station key)"""
    so = (doc or {}).get('so') or {}
    return [float(so.get(k) or 0.0) for k in st_keys(route)]


def deck_stations(context=None, geojson=None):
    if geojson is None and context is None and os.path.exists(LIVE):
        geojson = LIVE
    if geojson:
        return [(f['properties'].get('name'), TO_UTM.transform(*f['geometry']['coordinates'][:2]), set(str(f['properties'].get('lines', '')).split()))
                for f in jload(geojson)['features'] if f['properties'].get('layer') == 'rer_station' and f['geometry']['type'] == 'Point' and not f['properties'].get('deleted')]
    c = jload(context or os.path.join(ROOT, 'data', 'deck', 'context.json'))
    return [(s['name'], tuple(s['p']), set(s.get('lines') or [])) for s in c.get('rer_stations', [])]


def deck_platforms(geojson=None):
    """[(station, line label, UTM centre)] of the Deck's RER platforms as drawn (with Ben's slides): the station's
    position on a route is its platform's centre"""
    geojson = geojson or (LIVE if os.path.exists(LIVE) else None)
    if not geojson:
        return []
    out = []
    for f in jload(geojson)['features']:
        p, g = f['properties'], f['geometry']
        if p.get('layer') not in ('rer_platform', 'metro_platform') or g['type'] not in ('Polygon', 'MultiPolygon'):
            continue
        ring = g['coordinates'][0] if g['type'] == 'Polygon' else g['coordinates'][0][0]
        from shapely.geometry import Polygon
        out.append((p.get('station'), p.get('line', ''), Polygon([TO_UTM.transform(*q[:2]) for q in ring]).centroid.coords[0]))
    return out


PLAT_REACH = 40.0   # a platform within this of the route is on it


def station_target(route, L, chain, s, platforms):
    """the chainage of station s at its Deck platform's centre on this route, or None"""
    me = route.get('letter')
    cand = []
    for nm, lab, p in platforms:
        if nm != s['name'] or L.distance(Point(p)) > PLAT_REACH:
            continue
        if is_metro(route['id']):   # a Metro line: its own platforms only
            if (lab or '').replace('Metro ', '') != route['line']:
                continue
        else:
            ls = letters(lab)
            if (lab or '').startswith('Metro') or (me and (ls & set('ABCDE')) and me not in ls):   # another line's platform
                continue
        c = chain(p)
        if abs(c - s['c']) < STATION_REACH:
            cand.append((abs(c - s['c']), c))
    return min(cand)[1] if cand else None


def station_drift(route, platforms, so=None):
    """[(station, current platform centre c, Deck platform c)] where they differ by more than STATION_TOL (the platform
    centre is the station point plus the saved profile's slide, `so`)"""
    L, chain, _ = chain_of(route['path'])
    so = so or [0.0] * len(route['stations'])
    out = []
    for s, o in zip(route['stations'], so):
        sc = dict(s, c=s['c'] + o)
        t = station_target(route, L, chain, sc, platforms)
        if t is not None and abs(t - sc['c']) > STATION_TOL:
            out.append((s['name'], round(sc['c'], 1), round(t, 1)))
    return out


def letters(label):
    return set(label.replace('RER', '').replace('/', ' ').split())


def cut(line, a, b):
    """the part of LineString `line` between distances a and b along it (a > b: reversed)"""
    lo, hi = sorted((a, b))
    pts = [line.interpolate(lo)]
    d = 0.0
    cs = list(line.coords)
    for i in range(1, len(cs)):
        d += math.dist(cs[i - 1], cs[i])
        if lo < d < hi:
            pts.append(Point(cs[i]))
    pts.append(line.interpolate(hi))
    xy = [(p.x, p.y) for p in pts]
    return xy if a <= b else xy[::-1]


def rebuild(route, pieces):
    """the route's path from the Deck's pieces: (UTM polyline, new segs, notes)"""
    xy, segs, notes, c = [], [], [], 0.0
    for s in route['segs']:
        pid = s['piece']
        if pid == 'gap':        # a straight link the Deck draws no piece for (through the Union Terminal box)
            part = [tuple(s['u']), tuple(s['v'])]
            if xy and math.dist(xy[-1], part[0]) < 0.05:
                part = part[1:]
            n = sum(math.dist(p, q) for p, q in zip([xy[-1]] + part[:-1] if xy else part[:-1], part if xy else part[1:]))
            xy += part
            segs.append(dict(s, c0=round(c, 1), c1=round(c + n, 1)))
            c += n
            continue
        if pid == 'profiles':   # where the Deck draws no piece (past its region, or not drawn): the route's own path
            L = LineString(route_xy(route))
            a, b = L.project(Point(s['u'])), L.project(Point(s['v']))
            part = cut(L, a, b)
            n = 0.0
            if xy and math.dist(xy[-1], part[0]) < 0.05:
                part = part[1:]
            for i, q in enumerate(part):
                prev = part[i - 1] if i else (xy[-1] if xy else None)
                if prev is not None:
                    n += math.dist(prev, q)
            xy += part
            segs.append(dict(s, c0=round(c, 1), c1=round(c + n, 1)))
            c += n
            continue
        if pid not in pieces:   # the Deck renamed or replaced it: the nearest piece with the same letter(s)
            want = letters(s.get('lines', ''))
            same = (lambda lab: lab == s['lines']) if s.get('lines', '').startswith('Metro') else (lambda lab: want & letters(lab))
            mid = LineString([s['u'], s['v']]).interpolate(0.5, normalized=True)
            cand = [(LineString(g).distance(mid), k) for k, (lab, g) in pieces.items() if same(lab) and len(g) > 1]
            if not cand:
                raise SystemExit(f"{route['id']}: Deck piece {pid} is gone and no piece carries {sorted(want)}")
            pid = min(cand)[1]
            notes.append(f"piece {s['piece']} not in the Deck: using {pid}")
        L = LineString(pieces[pid][1])
        # the stretch of the piece: at its stored distances while they still land on the seg's ends (the piece is
        # unchanged there); else where the ends project onto the redrawn piece (searched near the stored distance,
        # so a piece that passes near the point twice is not cut at the wrong pass)
        def place(pt, d0):
            if d0 is not None and 0 <= d0 <= L.length + 0.5 and L.interpolate(min(d0, L.length)).distance(Point(pt)) <= TOL:
                return min(d0, L.length)
            best = None
            for d in np.arange(0, L.length + 1.0, 1.0):
                e = L.interpolate(min(d, L.length)).distance(Point(pt)) + (0.0 if d0 is None else 1e-4 * abs(d - d0))
                if best is None or e < best[0]:
                    best = (e, min(d, L.length))
            return best[1]
        a, b = place(s['u'], s.get('pa') if pid == s['piece'] else None), place(s['v'], s.get('pb') if pid == s['piece'] else None)
        du, dv = L.interpolate(a).distance(Point(s['u'])), L.interpolate(b).distance(Point(s['v']))
        if max(du, dv) > TOL:
            notes.append(f"{pid}: the seg ends moved {du:.1f} / {dv:.1f} m off the piece")
        part = cut(L, a, b)
        n = 0.0
        if xy and math.dist(xy[-1], part[0]) < 0.05:
            part = part[1:]
        elif xy:
            notes.append(f"{pid}: {math.dist(xy[-1], part[0]):.1f} m gap to the previous seg")
        for i, q in enumerate(part):   # this seg's chainage includes the joint from the previous seg's end
            prev = part[i - 1] if i else (xy[-1] if xy else None)
            if prev is not None:
                n += math.dist(prev, q)
        xy += part
        segs.append(dict(s, piece=pid, pa=round(float(a), 1), pb=round(float(b), 1), fwd=bool(b >= a), c0=round(c, 1), c1=round(c + n, 1),
                         u=[round(v, 1) for v in (L.interpolate(a).x, L.interpolate(a).y)],
                         v=[round(v, 1) for v in (L.interpolate(b).x, L.interpolate(b).y)]))
        c += n
    return xy, segs, notes


def route_xy(route):
    return [TO_UTM.transform(p[1], p[2]) for p in route['path']]


def drift(route, xy):
    """largest distance either way between the route file's path and the Deck path, and the length change"""
    old, new = LineString(route_xy(route)), LineString(xy)
    sample = lambda L: [L.interpolate(d) for d in np.arange(0, L.length, 5.0)] + [Point(L.coords[-1])]
    d1 = max(new.distance(p) for p in sample(old))
    d2 = max(old.distance(p) for p in sample(new))
    return max(d1, d2), new.length - route['length_m']


def cmap(old_segs, new_segs):
    """old chainage -> new chainage, seg by seg"""
    xo = [old_segs[0]['c0']] + [s['c1'] for s in old_segs]
    xn = [new_segs[0]['c0']] + [s['c1'] for s in new_segs]
    return lambda c: float(np.interp(c, xo, xn))


def resample(xy):
    """the route path as the page stores it, [c, lon, lat], on the Deck's own vertices"""
    L = LineString(xy).simplify(SIMPLIFY)
    out, d = [], 0.0
    cs = list(L.coords)
    for i, q in enumerate(cs):
        if i:
            d += math.dist(cs[i - 1], q)
        lon, lat = TO_LL.transform(*q)
        out.append([round(d, 2), round(lon, 7), round(lat, 7)])
    return out


def chain_of(path_ll):
    xy = [TO_UTM.transform(p[1], p[2]) for p in path_ll]
    L = LineString(xy)
    cv = np.array([p[0] for p in path_ll])
    dv = np.concatenate([[0], np.cumsum([math.dist(xy[i - 1], xy[i]) for i in range(1, len(xy))])])
    return L, (lambda pt: float(np.interp(L.project(Point(pt)), dv, cv))), (lambda c: L.interpolate(float(np.interp(c, cv, dv))))


def apply_route(rid, route, xy, segs, files, db_dir, stations_deck, so=None):
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import make_profile_context as mpc
    m = cmap(route['segs'], segs)
    old_L = route['length_m']
    new = dict(route)
    new['path'] = resample(xy)
    new['length_m'] = round(new['path'][-1][0], 1)
    new['route_chainage_m'] = [0.0, new['length_m']]
    new['segs'] = segs
    L, chain, at = chain_of(new['path'])
    # ground: the map 3 raster where it has data, else the old ground at the mapped chainage
    st = route['step_m']
    n = int(math.ceil(new['length_m'] / st)) + 1
    cs = np.minimum(np.arange(n) * st, new['length_m'])
    og = np.array([np.nan if v is None else v / 10 for v in route['ground_dm']], float)
    oc = np.arange(len(og)) * st
    inv_x = [m(c) for c in oc]
    pts = np.array([(at(c).x, at(c).y) for c in cs])
    g = np.full(len(cs), np.nan)
    x0, y1 = 695000.0, 4350000.0
    inside = (pts[:, 0] > x0 + 6) & (pts[:, 0] < x0 + 2 * mpc._ds.width - 6) & (pts[:, 1] < y1 - 6) & (pts[:, 1] > y1 - 2 * mpc._ds.height + 6)
    if inside.any():
        g[inside] = mpc.sample(pts[inside])
    fill = ~np.isfinite(g)
    g[fill] = np.interp(cs[fill], inv_x, og)
    new['ground_dm'] = [None if not np.isfinite(v) else int(round(v * 10)) for v in g]
    if route.get('ground_dm_lidar'):   # the LiDAR ground: the same raster where it has data, else the old, mapped
        ol = np.array([np.nan if v is None else v / 10 for v in route['ground_dm_lidar']], float)
        gl = g.copy()
        gl[fill] = np.interp(cs[fill], inv_x[:len(ol)], ol)
        new['ground_dm_lidar'] = [None if not np.isfinite(v) else int(round(v * 10)) for v in gl]
    for pc in new.get('pieces', []):   # the drawn (KMZ) pieces' stretches, mapped
        pc['c0'], pc['c1'] = round(m(pc['c0']), 1), round(m(pc['c1']), 1)
    # stations at their Deck platform's centre (the platform as the Deck draws it, slid or not), else at the Deck's
    # station point of the same name, else mapped
    platforms = deck_platforms()
    so = so or [0.0] * len(new['stations'])
    placed = set()
    for s, o, k in zip(new['stations'], so, st_keys(new)):
        s0 = dict(s, c=m(s['c']) + o)
        t = station_target(new, L, chain, s0, platforms)

        hit = [(math.dist(p, at(m(s['c'])).coords[0]), p) for nm, p, _ in stations_deck if nm == s['name']]
        hit = [h for h in hit if h[0] < STATION_REACH]
        if t is not None:
            c = t   # the station point at the platform centre: its slide in the saved profile is reset (main)
            placed.add(k)
            pc = at(c)
            near = [p for nm, lab, p in platforms if nm == s['name'] and math.dist(p, pc.coords[0]) < PLAT_REACH + 60]
            s['offset'] = round(min((L.distance(Point(p)) for p in near), default=0.0), 1)
        elif hit:
            p = min(hit)[1]
            c = chain(p)
            s['offset'] = round(L.distance(Point(p)), 1)
        else:
            c = m(s['c'])
        q = at(c)
        lon, lat = TO_LL.transform(q.x, q.y)
        s.update(c=round(c, 1), lon=round(lon, 7), lat=round(lat, 7))
    for r in new.get('rivers', []):
        r['c0'], r['c1'] = round(m(r['c0']), 1), round(m(r['c1']), 1)
    # crossings with every other line, recomputed. A Metro x RER crossing is kept on the RER route only (the page
    # gives it to the Metro line from there)
    me = LineString(xy)
    xs = []
    my_kind = 'metro' if is_metro(rid) else 'rer'
    for fn, d in files.items():
        if d['id'] == rid:
            continue
        if d['id'] in ('RER_1', 'RER_2', 'RER_3', 'RER_4', 'RER_5'):   # the old cores (railsim): their entries move along
            ch_ = [dict(x, oc=round(m(x['oc']), 1)) if x.get('wid') == rid and 'oc' in x else x for x in d.get('crossings', [])]
            if ch_ != d.get('crossings', []):
                d['crossings'] = ch_
                files[fn] = d
                jsave(fn, d)
            continue
        OL, ochain, _ = chain_of(d['path'])
        hit = OL.intersection(me)
        rer = not is_metro(d['id'])
        keep = [x for x in d.get('crossings', []) if x.get('wid') != rid]
        mine, theirs = not (my_kind == 'metro' and rer), not (my_kind == 'rer' and not rer)
        for p in getattr(hit, 'geoms', [hit]):
            if p.is_empty or p.geom_type != 'Point':
                continue
            c, co = chain((p.x, p.y)), ochain((p.x, p.y))
            if mine:
                xs.append({'c': round(c, 1), 'wid': d['id'], 'oc': round(co, 1), 'kind': 'rer' if rer else 'metro', 'with': d.get('short') or d['line']})
            if theirs:
                keep.append({'c': round(co, 1), 'wid': rid, 'oc': round(c, 1), 'kind': my_kind, 'with': route.get('short') or route['line']})
        if keep != d.get('crossings', []):
            d['crossings'] = sorted(keep, key=lambda x: x['c'])
            files[fn] = d
            jsave(fn, d)
    new['crossings'] = sorted(xs, key=lambda x: x['c'])
    return new, m, old_L, placed


def move_doc(doc, m, length):
    if not doc:
        return doc
    doc = dict(doc)
    doc['pvi'] = [[round(m(c), 1), z] for c, z in doc.get('pvi', [])]
    doc['ovr'] = [[round(m(a), 1), round(m(b), 1), *r] for a, b, *r in doc.get('ovr', [])]
    if 'length_m' in doc:
        doc['length_m'] = length
    return doc


def routes():
    """[(id, file, saved profile file)] of every tied route: the RER routes, then the Metro lines"""
    out = []
    for e in jload(os.path.join(SITE, 'rer', 'lines', 'index.json')):
        out.append((e['id'], os.path.join(SITE, 'rer', 'lines', e['id'] + '.json'), os.path.join(SITE, 'rer', 'alignments', e['id'] + '.json')))
    for e in jload(os.path.join(SITE, 'lines', 'index.json')):
        out.append((e['id'], os.path.join(SITE, 'lines', e['id'] + '.json'), os.path.join(SITE, 'alignments', e['id'] + '.json')))
    return out


def saved_doc(rid, al, db):
    """the saved profile: the page database's export (--db) if it has one, else the repo copy"""
    for p in ([os.path.join(db, rid + '.json')] if db else []) + [al]:
        if os.path.exists(p):
            return jload(p)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--context', help='the Deck context.json (default data/deck/context.json)')
    ap.add_argument('--geojson', help="a Deck GeoJSON export (rer_line, metro_line and platform features); default data/deck/rer_routes.geojson, else --context")
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--db', help='a folder of the page database alignments (one JSON per route) to move as well')
    ap.add_argument('--json', help='write the check as JSON here')
    ap.add_argument('--only', help='comma-separated route ids')
    a = ap.parse_args()
    pieces = deck_pieces(a.context, a.geojson)
    report, drifted = [], []
    platforms = deck_platforms(a.geojson)
    only = set(a.only.split(',')) if a.only else None
    for rid, fn, al in routes():
        if only and rid not in only:
            continue
        r = jload(fn)
        if not r.get('segs'):
            report.append({'id': rid, 'status': 'no segs'})
            continue
        so = slides(r, saved_doc(rid, al, a.db))
        xy, segs, notes = rebuild(r, pieces)
        d, dl = drift(r, xy)
        dseg = max(abs((n['c1'] - n['c0']) - (o['c1'] - o['c0'])) for o, n in zip(r['segs'], segs))
        d = max(d, dseg)
        sd = station_drift(r, platforms, so)
        ok = d <= TOL and abs(dl) <= TOL and not sd
        notes += [f"{nm} at {c:.1f}, its Deck platform at {t:.1f} ({t - c:+.1f} m)" for nm, c, t in sd]
        report.append({'id': rid, 'max_m': round(d, 2), 'length_change_m': round(dl, 2), 'stations': sd, 'ok': ok, 'notes': notes})
        if not ok:
            drifted.append((rid, fn, al, r, xy, segs, so))
    for x in report:
        print(f"{x['id']:22s} " + (x['status'] if 'status' in x else f"{'ok     ' if x['ok'] else 'DRIFTED'} max {x['max_m']:8.2f} m, length {x['length_change_m']:+8.2f} m") + ('  ' + '; '.join(x.get('notes') or []) if x.get('notes') else ''))
    if a.json:
        jsave(a.json, report, indent=1)
    if not a.apply:
        sys.exit(1 if drifted else 0)
    files = {fn: jload(fn) for fn in sorted(glob.glob(os.path.join(SITE, 'lines', '*_*.json')) + glob.glob(os.path.join(SITE, 'rer', 'lines', 'RER_*_*.json')))}
    canon_f, links_f = os.path.join(SITE, 'rer', 'canon.json'), os.path.join(SITE, 'rer', 'links.json')
    canon, links = jload(canon_f), jload(links_f)
    net_f, mnet_f = os.path.join(SITE, 'rer', 'network.json'), os.path.join(SITE, 'network.json')
    net, mnet = jload(net_f), jload(mnet_f)
    ridx_f, midx_f = os.path.join(SITE, 'rer', 'lines', 'index.json'), os.path.join(SITE, 'lines', 'index.json')
    ridx, midx = jload(ridx_f), jload(midx_f)
    sdeck = deck_stations(a.context, a.geojson)
    for rid, fn, al, r, xy, segs, so in drifted:
        new, m, old_L, placed = apply_route(rid, r, xy, segs, files, a.db, sdeck, so)
        jsave(fn, new)
        files[fn] = new
        metro = is_metro(rid)
        for e in (midx if metro else ridx):
            if e['id'] == rid:
                e['length_m'] = new['length_m']
        if metro:
            pl = [[round(p[1], 5), round(p[2], 5)] for p in new['path']]
            net['metro'][rid] = pl
            mnet['metro'][rid] = pl
        else:
            net['rer'][rid] = [[round(p[1], 7), round(p[2], 7)] for p in new['path']]
        cn = canon['lines'].get(rid) or {}
        for lk in cn.get('locked', []):
            lk['c0'], lk['c1'] = round(m(lk['c0']), 1), round(m(lk['c1']), 1)
            lk['pvi'] = [[round(m(c), 1), z] for c, z in lk.get('pvi', [])]
            lk['ovr'] = [[round(m(x), 1), round(m(y), 1), t] for x, y, t in lk.get('ovr', [])]
        for j in links['junctions']:
            for mem in j['members']:
                if mem['r'] == rid:
                    mem['c'] = round(m(mem['c']), 1)
        for sh in links['shared']:
            if sh['a'] == rid:
                sh['ca'] = [round(m(c), 1) for c in sh['ca']]
            if sh['b'] == rid:
                sh['cb'] = [round(m(c), 1) for c in sh['cb']]
        sts = {k: s for k, s in zip(st_keys(new), new['stations'])}
        targets = [al] + ([os.path.join(a.db, rid + '.json')] if a.db else [])
        for p in targets:
            if os.path.exists(p):
                doc = move_doc(jload(p), m, new['length_m'])
                so_d = doc.get('so') or {}
                if so_d:   # a platform placed from the Deck is at its station point: no slide
                    doc['so'] = {k: v for k, v in so_d.items() if k not in placed}
                    so_d = doc['so']
                if doc.get('stations'):   # the saved summary of stations: at their new points and platform centres
                    for x, k in zip(doc['stations'], [k for k in st_keys(new) if k not in (doc.get('del') or [])]):
                        if k in sts and sts[k]['name'] == x.get('name'):
                            x['point_c'] = sts[k]['c']
                            x['c'] = round(sts[k]['c'] + float(so_d.get(k) or 0.0), 1)
                jsave(p, doc, indent=2 if p == al else 1)
        print(f"rebuilt {rid}: {old_L:.1f} -> {new['length_m']:.1f} m")
    # junction points where their routes now meet
    by = {fn.split('/')[-1][:-5]: d for fn, d in files.items()}
    for j in links['junctions']:
        ps = []
        for mem in j['members']:
            d = by.get(mem['r'])
            if d:
                _, _, at = chain_of(d['path'])
                ps.append(at(mem['c']).coords[0])
        if ps:
            j['p'] = [round(float(np.mean([p[0] for p in ps])), 1), round(float(np.mean([p[1] for p in ps])), 1)]
    jsave(ridx_f, ridx)
    jsave(midx_f, midx)
    jsave(net_f, net)
    jsave(mnet_f, mnet)
    jsave(canon_f, canon, indent=1)
    jsave(links_f, links, indent=1)


if __name__ == '__main__':
    main()
