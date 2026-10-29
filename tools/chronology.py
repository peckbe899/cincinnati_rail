"""The Chronology record (hub chronology/segments; Ben, 28 October): opening year and phase of every Metro and TRI
segment (between two neighbouring stations of a route) and station.

- Systems: metro, tri, cvx (the CVG Express, the airport line: its own system, Ben 28 October).
- Segment key: Metro, the line and the two station names, sorted ("metro|Line_11|Clay|Manhattan"); TRI, the two station
  names ("tri|City Hall|Fountain Square"), so track shared by several TRI routes is one segment (no Metro lines share
  track: two Metro lines between the same two stations run in their own tunnels). Station key: system and name.
- Phase of a segment: set by hand, else from its year (phase_years), else not set: the line's phase in the structure
  record (and a drawn piece's phase there) stands in.
- The routes file (data/profile/chronology_lines.json, written by main()): every Metro line and every TRI route (the
  lettered A-E trunks and branches; the numbered RER-1 to RER-5 services are not routes), with a light path, its stations
  and segments in order, and for a branch its parent route.

Usage: python3 tools/chronology.py   (writes data/profile/chronology_lines.json; the hub's Deck tie runs it)
"""
import glob
import json
import math
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PROFILE = os.path.join(ROOT, 'data', 'profile')
DEFAULT = os.path.join(PROFILE, 'chronology.json')
ROUTES = os.path.join(PROFILE, 'chronology_lines.json')


def seg_key(sys_, a, b, line=None):
    a, b = sorted((a, b))
    return f'{sys_}|{line}|{a}|{b}' if sys_ == 'metro' else f'{sys_}|{a}|{b}'


def st_key(sys_, name):
    return f'{sys_}|{name}'


def phase_of_year(rec, year):
    if year is None:
        return None
    for y0, y1, ph in rec.get('phase_years') or []:
        if y0 <= year <= y1:
            return ph
    return None


def seg_phase(rec, key):
    e = (rec.get('segments') or {}).get(key) or {}
    return e.get('phase') or phase_of_year(rec, e.get('year'))


def stations_sorted(stations):
    return sorted(stations, key=lambda s: s['c'])


def phase_at(rec, sys_, stations, c, line=None):
    """the phase of the segment of a route at chainage c (before the first or past the last station: the end segment)"""
    st = stations_sorted(stations)
    if not rec or len(st) < 2:
        return None
    i = 0
    while i + 2 < len(st) and c > st[i + 1]['c']:
        i += 1
    return seg_phase(rec, seg_key(sys_, st[i]['name'], st[i + 1]['name'], line))


def _light(path, tol=3.0):
    """drop path vertices within tol m of the chord (Douglas-Peucker on lon/lat scaled to metres)"""
    if len(path) < 3:
        return path
    kx, ky = 111320 * math.cos(math.radians(path[0][2])), 110540
    pts = [(p[1] * kx, p[2] * ky) for p in path]
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (x0, y0), (x1, y1) = pts[a], pts[b]
        L = math.hypot(x1 - x0, y1 - y0) or 1
        best, k = -1, None
        for i in range(a + 1, b):
            d = abs((x1 - x0) * (y0 - pts[i][1]) - (x0 - pts[i][0]) * (y1 - y0)) / L
            if d > best:
                best, k = d, i
        if k is not None and best > tol:
            keep[k] = True
            stack += [(a, k), (k, b)]
    return [[round(p[0], 1), round(p[1], 7), round(p[2], 7)] for p, f in zip(path, keep) if f]


JUNCTION_M = 25      # TRI path ends this close meet at a junction
JUNCTION_ST_M = 200  # a station this close to a junction is the junction


def join_routes(rs):
    """TRI routes meet where their paths end at the same point (Ben, 29 October: branches did not reach their trunks).
    Each route gets the junction as its end station there: a station within JUNCTION_ST_M of the point (Xavier, Covington
    Union, Latonia, Edgewood, South Cumminsville), else a junction point named after the nearest station ("Anderson Ferry
    junction"; `pseudo`, not drawn as a station), so the stretch from the junction is a segment. A route end on another
    route's path (not at its end) joins it the same way."""
    kx, ky = 111320 * math.cos(math.radians(39.1)), 110540
    dist = lambda a, b: math.hypot((a[0] - b[0]) * kx, (a[1] - b[1]) * ky)
    stations = [s for r in rs for s in r['data']['stations']]
    ends = [(r, e, (r['data']['path'][e][1], r['data']['path'][e][2]), r['data']['path'][e][0]) for r in rs for e in (0, -1)]
    groups = []
    for x in ends:
        for g in groups:
            if any(dist(x[2], y[2]) <= JUNCTION_M for y in g):
                g.append(x); break
        else:
            groups.append([x])

    def on_other_path(x):
        r, _, p, _ = x
        for q in rs:
            if q is r:
                continue
            P = q['data']['path']
            for a, b in zip(P, P[1:]):
                ax, ay, bx, by = (a[1] - p[0]) * kx, (a[2] - p[1]) * ky, (b[1] - p[0]) * kx, (b[2] - p[1]) * ky
                dx, dy = bx - ax, by - ay
                t = max(0, min(1, -(ax * dx + ay * dy) / ((dx * dx + dy * dy) or 1)))
                if math.hypot(ax + t * dx, ay + t * dy) <= JUNCTION_M:
                    return True
        return False
    used = {}
    for g in groups:
        if len({x[0]['id'] for x in g}) < 2 and not on_other_path(g[0]):
            continue
        pt = (sum(x[2][0] for x in g) / len(g), sum(x[2][1] for x in g) / len(g))
        near = min(stations, key=lambda s: dist(pt, (s['lon'], s['lat'])))
        if dist(pt, (near['lon'], near['lat'])) <= JUNCTION_ST_M:
            J = {'name': near['name'], 'lon': near['lon'], 'lat': near['lat']}
        else:
            nm = near['name'] + ' junction'
            if nm in used and dist(used[nm], pt) > JUNCTION_M:   # another junction near the same station: by its route
                nm = sorted(x[0]['name'] for x in g)[0] + ' junction'
            used[nm] = pt
            J = {'name': nm, 'lon': round(pt[0], 7), 'lat': round(pt[1], 7), 'pseudo': True}
        for r, e, p, c in g:
            st = r['_st']
            if not st or st[e]['name'] == J['name']:
                continue
            j = dict(J, c=c, junction=True)
            r['_st'] = [j] + st if e == 0 else st + [j]


SAME_STATION_M = 1000   # TRI stations of one name further apart than this are different stations


def split_names(rs):
    """TRI stations are keyed by name, so two different stations of one name would share an opening year: Western Hills
    (the RER A junction, and the Westwood branch's station 5.4 km out) and Dent (RER A Westwood, RER D 1.6 km away).
    Places of one name more than SAME_STATION_M apart: the place on the most routes keeps the name, the others take
    "name (route)"."""
    kx, ky = 111320 * math.cos(math.radians(39.1)), 110540
    by = {}
    for r in rs:
        for s in r['_st']:
            if not s.get('pseudo'):
                by.setdefault(s['name'], []).append((r, s))
    for name, inst in by.items():
        places = []   # [[(r, s), ...]] by location
        for r, s in inst:
            for pl in places:
                q = pl[0][1]
                if math.hypot((q['lon'] - s['lon']) * kx, (q['lat'] - s['lat']) * ky) <= SAME_STATION_M:
                    pl.append((r, s)); break
            else:
                places.append([(r, s)])
        if len(places) < 2:
            continue
        places.sort(key=lambda pl: (-len({r['id'] for r, _ in pl}), min(r['id'] for r, _ in pl)))
        for pl in places[1:]:
            label = sorted({r['name'] for r, _ in pl})[0]
            for r, s in pl:
                i = r['_st'].index(s)
                r['_st'][i] = dict(s, name=f'{name} ({label})', was=name)


def routes():
    out = []
    for fn in sorted(glob.glob(os.path.join(PROFILE, 'lines', '*_*.json'))):
        d = json.load(open(fn, encoding='utf8'))
        cvx = d['id'] == 'CVG_Express'   # the CVG Express: its own system, the airport line (Ben, 28 October)
        out.append(dict(id=d['id'], sys='cvx' if cvx else 'metro', name=d['line'], color=d.get('color'), kind='branch' if d['id'] == 'Line_2b' else 'line',
                        parent='Line_2' if d['id'] == 'Line_2b' else None, data=d))
    for fn in sorted(glob.glob(os.path.join(PROFILE, 'rer', 'lines', 'RER_*_*.json'))):
        d = json.load(open(fn, encoding='utf8'))
        m = re.match(r'RER_([A-E])_(\w+)', d['id'])
        if not m:
            continue
        out.append(dict(id=d['id'], sys='tri', name=d['line'], color=d.get('color'), kind=d.get('kind') or 'trunk',
                        parent=None if d.get('kind') == 'trunk' else f'RER_{m.group(1)}_trunk', opened=d.get('opened'), data=d))
    for r in out:
        r['_st'] = stations_sorted(r['data']['stations'])
    join_routes([r for r in out if r['sys'] == 'tri'])
    split_names([r for r in out if r['sys'] == 'tri'])
    for r in out:
        d = r.pop('data')
        st = r.pop('_st')
        r['length'] = d['length_m']
        r['path'] = _light(d['path'])
        r['stations'] = [dict(name=s['name'], c=round(s['c'], 1), lon=s['lon'], lat=s['lat'], **{k: s[k] for k in ('was', 'junction', 'pseudo') if k in s}) for s in st]
        r['segments'] = [seg_key(r['sys'], a['name'], b['name'], r['id']) for a, b in zip(st, st[1:])]
    return out


def default_record(rs):
    """the starting record (tracker 2B; handoff of 28 October): the Phase 2 opening segments with their years, the CVG
    Express (1969, later), the TRI routes' opening years; everything else not set"""
    rec = {'about': 'Opening year and phase of every Metro and TRI segment and station (Ben, 28 October). Phases by year: '
                    'tracker 2B, with the years between as Ben ruled (1919-33 Phase 1, 1942-49 Phase 2, 1980 on later).',
           'phase_years': [[1800, 1933, '1'], [1934, 1949, '2'], [1950, 1979, '3'], [1980, 2200, 'later']],
           'segments': {}, 'stations': {}, 'core': {},
           'notes': ['Line 1, the Pearl Street Trunk, opened in November 1905 (first revenue service); the tracker names no stations for it.',
                     'Lines 1-7 between their original termini are Phase 1, years not set: the termini are not in the repo, so every Line 1-7 '
                     'segment is not set and takes Phase 1 from the line.']}
    by = {r['id']: r for r in rs}
    opening = {'Line_8': ('Northside', 'Union Terminal', 1934), 'Line_9': ('Camp Washington', 'Oakley', 1936), 'Line_10': ('Mill Creek', 'Paradrome', 1937),
               'Line_11': ('Manhattan', 'Ludlow', 1939), 'Line_12': ('Hopple', 'Pleasant Ridge', 1941)}
    for lid, (a, b, y) in opening.items():
        r = by[lid]
        names = [s['name'] for s in r['stations']]
        note = f"{r['name']} opening segment, {a} to {b} (tracker 2B)"
        if a in names and b in names:
            i, j = sorted((names.index(a), names.index(b)))
            keys = r['segments'][i:j]
            for k in keys:
                rec['segments'][k] = {'year': y, 'phase': '2', 'src': 'tracker', 'note': note}
            rec['core'][lid] = keys
        else:   # kept as an orphan until Ben places it
            k = seg_key('metro', a, b, lid)
            rec['segments'][k] = {'year': y, 'phase': '2', 'src': 'tracker', 'note': note + '; a station is not on the line'}
            rec['core'][lid] = [k]
    for k in by['CVG_Express']['segments']:   # cvx|... keys
        rec['segments'][k] = {'year': 1969, 'phase': 'later', 'src': 'Ben', 'note': 'CVG Express opened 1969 (Ben); built as a later extension'}
    for r in rs:
        if r['sys'] == 'tri' and r.get('opened'):
            for k in r['segments']:
                rec['segments'].setdefault(k, {'year': int(r['opened']), 'src': 'default', 'note': f"{r['name']}: the route's opening year"})
    return rec


def main():
    rs = routes()
    json.dump({'about': __doc__.split('\n\n')[0], 'routes': rs}, open(ROUTES, 'w', encoding='utf8'), separators=(',', ':'), ensure_ascii=False)
    print(f'{len(rs)} routes, {sum(len(r["segments"]) for r in rs)} segments -> {ROUTES} ({os.path.getsize(ROUTES) // 1024} kB)')
    if not os.path.exists(DEFAULT):
        json.dump(default_record(rs), open(DEFAULT, 'w', encoding='utf8'), indent=1, ensure_ascii=False)
        print('default record ->', DEFAULT)


if __name__ == '__main__':
    main()
