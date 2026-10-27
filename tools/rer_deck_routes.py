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
            if p.get('layer') != 'rer_line' or f['geometry']['type'] != 'LineString':
                continue
            xy = [TO_UTM.transform(*q[:2]) for q in f['geometry']['coordinates']]
            out[p['id']] = (p.get('name', ''), xy)
    else:
        for x in jload(context or os.path.join(ROOT, 'data', 'deck', 'context.json'))['rer']:
            out[x['id']] = (x.get('name', ''), [tuple(q[:2]) for q in x['c']])
    return out


def deck_stations(context=None, geojson=None):
    if geojson is None and context is None and os.path.exists(LIVE):
        geojson = LIVE
    if geojson:
        return [(f['properties'].get('name'), TO_UTM.transform(*f['geometry']['coordinates'][:2]), set(str(f['properties'].get('lines', '')).split()))
                for f in jload(geojson)['features'] if f['properties'].get('layer') == 'rer_station' and f['geometry']['type'] == 'Point' and not f['properties'].get('deleted')]
    c = jload(context or os.path.join(ROOT, 'data', 'deck', 'context.json'))
    return [(s['name'], tuple(s['p']), set(s.get('lines') or [])) for s in c.get('rer_stations', [])]


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
        if pid not in pieces:   # the Deck renamed or replaced it: the nearest piece with the same letter(s)
            want = letters(s.get('lines', ''))
            mid = LineString([s['u'], s['v']]).interpolate(0.5, normalized=True)
            cand = [(LineString(g).distance(mid), k) for k, (lab, g) in pieces.items() if want & letters(lab) and len(g) > 1]
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


def apply_route(rid, route, xy, segs, files, db_dir, stations_deck):
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
    # stations at the Deck's point of the same name, else mapped
    for s in new['stations']:
        hit = [(math.dist(p, at(m(s['c'])).coords[0]), p) for nm, p, _ in stations_deck if nm == s['name']]
        hit = [h for h in hit if h[0] < STATION_REACH]
        if hit:
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
    # crossings with every other line (Metro lines and the RER routes), recomputed
    me = LineString(xy)
    xs = []
    for fn, d in files.items():
        if d['id'] == rid or d['id'] in ('RER_1', 'RER_2', 'RER_3', 'RER_4', 'RER_5'):
            continue
        OL, ochain, _ = chain_of(d['path'])
        hit = OL.intersection(me)
        rer = d['id'].startswith('RER_')
        keep = [x for x in d.get('crossings', []) if x.get('wid') != rid]
        for p in getattr(hit, 'geoms', [hit]):
            if p.is_empty or p.geom_type != 'Point':
                continue
            c, co = chain((p.x, p.y)), ochain((p.x, p.y))
            xs.append({'c': round(c, 1), 'wid': d['id'], 'oc': round(co, 1), 'kind': 'rer' if rer else 'metro', 'with': d.get('short') or d['line']})
            if rer:
                keep.append({'c': round(co, 1), 'wid': rid, 'oc': round(c, 1), 'kind': 'rer', 'with': route.get('short') or route['line']})
        if rer and keep != d.get('crossings', []):
            d['crossings'] = sorted(keep, key=lambda x: x['c'])
            files[fn] = d
            jsave(fn, d)
    new['crossings'] = sorted(xs, key=lambda x: x['c'])
    return new, m, old_L


def move_doc(doc, m, length):
    if not doc:
        return doc
    doc = dict(doc)
    doc['pvi'] = [[round(m(c), 1), z] for c, z in doc.get('pvi', [])]
    doc['ovr'] = [[round(m(a), 1), round(m(b), 1), *r] for a, b, *r in doc.get('ovr', [])]
    if 'length_m' in doc:
        doc['length_m'] = length
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--context', help='the Deck context.json (default data/deck/context.json)')
    ap.add_argument('--geojson', help="a Deck GeoJSON export (rer_line features); default data/deck/rer_routes.geojson, else --context")
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--db', help='a folder of the page database alignments (one JSON per route) to move as well')
    ap.add_argument('--json', help='write the check as JSON here')
    a = ap.parse_args()
    pieces = deck_pieces(a.context, a.geojson)
    idx = jload(os.path.join(SITE, 'rer', 'lines', 'index.json'))
    report, drifted = [], []
    for e in idx:
        fn = os.path.join(SITE, 'rer', 'lines', e['id'] + '.json')
        r = jload(fn)
        if not r.get('segs'):
            report.append({'id': e['id'], 'status': 'no segs'})
            continue
        xy, segs, notes = rebuild(r, pieces)
        d, dl = drift(r, xy)
        dseg = max(abs((n['c1'] - n['c0']) - (o['c1'] - o['c0'])) for o, n in zip(r['segs'], segs))
        d = max(d, dseg)
        ok = d <= TOL and abs(dl) <= TOL
        report.append({'id': e['id'], 'max_m': round(d, 2), 'length_change_m': round(dl, 2), 'ok': ok, 'notes': notes})
        if not ok:
            drifted.append((e['id'], fn, r, xy, segs))
    for x in report:
        print(f"{x['id']:22s} " + (x['status'] if 'status' in x else f"{'ok     ' if x['ok'] else 'DRIFTED'} max {x['max_m']:8.2f} m, length {x['length_change_m']:+8.2f} m") + ('  ' + '; '.join(x.get('notes') or []) if x.get('notes') else ''))
    if a.json:
        jsave(a.json, report, indent=1)
    if not a.apply:
        sys.exit(1 if drifted else 0)
    files = {fn: jload(fn) for fn in sorted(glob.glob(os.path.join(SITE, 'lines', '*_*.json')) + glob.glob(os.path.join(SITE, 'rer', 'lines', 'RER_*_*.json')))}
    canon_f, links_f = os.path.join(SITE, 'rer', 'canon.json'), os.path.join(SITE, 'rer', 'links.json')
    canon, links = jload(canon_f), jload(links_f)
    net_f = os.path.join(SITE, 'rer', 'network.json')
    net = jload(net_f)
    sdeck = deck_stations(a.context, a.geojson)
    for rid, fn, r, xy, segs in drifted:
        new, m, old_L = apply_route(rid, r, xy, segs, files, a.db, sdeck)
        jsave(fn, new)
        files[fn] = new
        for e in idx:
            if e['id'] == rid:
                e['length_m'] = new['length_m']
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
        al = os.path.join(SITE, 'rer', 'alignments', rid + '.json')
        if os.path.exists(al):
            jsave(al, move_doc(jload(al), m, new['length_m']), indent=2)
        if a.db and os.path.exists(os.path.join(a.db, rid + '.json')):
            jsave(os.path.join(a.db, rid + '.json'), move_doc(jload(os.path.join(a.db, rid + '.json')), m, new['length_m']), indent=1)
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
    jsave(os.path.join(SITE, 'rer', 'lines', 'index.json'), idx)
    jsave(net_f, net)
    jsave(canon_f, canon, indent=1)
    jsave(links_f, links, indent=1)


if __name__ == '__main__':
    main()
