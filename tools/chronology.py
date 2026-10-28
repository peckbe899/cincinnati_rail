"""The Chronology record (hub chronology/segments; Ben, 28 October): opening year and phase of every Metro and TRI
segment (between two neighbouring stations of a route) and station.

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


def routes():
    out = []
    for fn in sorted(glob.glob(os.path.join(PROFILE, 'lines', '*_*.json'))):
        d = json.load(open(fn, encoding='utf8'))
        out.append(dict(id=d['id'], sys='metro', name=d['line'], color=d.get('color'), kind='branch' if d['id'] == 'Line_2b' else 'line',
                        parent='Line_2' if d['id'] == 'Line_2b' else None, data=d))
    for fn in sorted(glob.glob(os.path.join(PROFILE, 'rer', 'lines', 'RER_*_*.json'))):
        d = json.load(open(fn, encoding='utf8'))
        m = re.match(r'RER_([A-E])_(\w+)', d['id'])
        if not m:
            continue
        out.append(dict(id=d['id'], sys='tri', name=d['line'], color=d.get('color'), kind=d.get('kind') or 'trunk',
                        parent=None if d.get('kind') == 'trunk' else f'RER_{m.group(1)}_trunk', opened=d.get('opened'), data=d))
    for r in out:
        d = r.pop('data')
        st = stations_sorted(d['stations'])
        r['length'] = d['length_m']
        r['path'] = _light(d['path'])
        r['stations'] = [dict(name=s['name'], c=round(s['c'], 1), lon=s['lon'], lat=s['lat']) for s in st]
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
    for k in by['CVG_Express']['segments']:
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
