"""Station 3D sync: one snapshot of a station area from the Rail Profiles editor and the Mill Creek Deck.

The editors' published files and saved records are fetched first by a Claude session (Artifact read, ArtifactData
with out_dir) into CACHE (see README.md). This script picks the lines within RADIUS of the station, runs both
editors headless (harness.js) so the levels, structure types and platforms come from the editors' own code, and
writes snapshot.json: every coordinate in metres, x east and y north (true) from the station origin, z the
elevation in metres (NAVD88, as the editors). The snapshot is then written to the 3D page's database.

Usage: python3 sync.py [--cache DIR] [--out snapshot.json] [--area fountain_square] [--dry-run]
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

AREAS = {
    # origin: the Fountain Square model's reference point (stations/fountain_square/README.md); frame_turn: that
    # model's frame is turned 11 degrees with the street grid (frame north = true bearing 349)
    'fountain_square': dict(name='Fountain Square', lon=-84.5125, lat=39.1018, radius=400.0, frame_turn=-11.0,
                            stations=['Fountain Square']),
}

# Platform lengths (Ben, 2026-10-26): Metro 400 ft, TRI 670 ft. The Profiles editor's RER default is 200 m.
PLATFORM_M = {'metro': 121.92, 'rer': 204.216}
PLATFORM_ABOVE_RAIL = {'metro': 1.0, 'rer': 1.0}   # platform top above the rail: assumption, not in the editors

# Structure sizes measured from the rail (Rail Profiles editor: METRO_ST, RER_DEFAULTS). Widths and tube spacing are
# not in the editors: assumptions, marked in the snapshot.
METRO_ST = {
    'box': dict(k='box', below=1.0, top=4.6, cover=0.6, width=8.5),
    'tube': dict(k='tube', below=0.68, top=4.08, od=4.76, spacing=7.0),
    'bore': dict(k='bore', below=3.2, top=5.8, od=9.0),
}
RER_ST = {
    'box': dict(k='box', below=1.0, top=6.6, width=11.0),
    'bore': dict(k='tube', below=1.0, top=7.5, od=8.5, spacing=11.0),
}
OPEN_ST = dict(k='open', below=0.8, top=0.0, width=9.0)
ERA_SHIELD = {**{f'Line_{k}': 'tube' for k in ['1', '2', '2b', '3', '4', '5', '6', '7']},
              **{f'Line_{k}': 'bore' for k in ['8', '9', '10', '11', '12', '13', '14']}, 'CVG_Express': 'bore'}
ASSUMED = ['Metro box width 8.5 m', 'Metro twin tubes 7.0 m apart', 'RER box width 11.0 m',
           'RER bored tubes: twin, 8.5 m outside diameter, 11.0 m apart', 'platform tops 1.0 m above the rail',
           'ground: a plane fitted to the Profiles ground within the area']
# RER line to TRI letter (rer/canon.json: RER-n is TRI by KMZ colour, 1 A ... 5 E)
RER_LETTER = {'RER_1': 'A', 'RER_2': 'B', 'RER_3': 'C', 'RER_4': 'D', 'RER_5': 'E'}


def structure(line_id, t):
    """the structure a line has for a Profiles type (the editor's structFor, river crossings aside)"""
    if t in ('elevated', 'atgrade', 'trough'):
        return dict(OPEN_ST, t=t)
    if line_id.startswith('RER_'):
        return dict(RER_ST['box' if t == 'cutcover' else 'bore'])
    if t == 'cutcover':
        return dict(METRO_ST['box'])
    if t == 'deep':
        return dict(METRO_ST['tube'])
    return dict(METRO_ST[ERA_SHIELD.get(line_id, 'tube')])


# ---- UTM zone 16N (EPSG:32616), Krueger series ----
_A, _F = 6378137.0, 1 / 298.257223563
_N = _F / (2 - _F)
_AA = _A / (1 + _N) * (1 + _N ** 2 / 4 + _N ** 4 / 64)
_ALPHA = [_N / 2 - 2 * _N ** 2 / 3 + 5 * _N ** 3 / 16, 13 * _N ** 2 / 48 - 3 * _N ** 3 / 5, 61 * _N ** 3 / 240]
_BETA = [_N / 2 - 2 * _N ** 2 / 3 + 37 * _N ** 3 / 96, _N ** 2 / 48 + _N ** 3 / 15, 17 * _N ** 3 / 480]
_DELTA = [2 * _N - 2 * _N ** 2 / 3 - 2 * _N ** 3, 7 * _N ** 2 / 3 - 8 * _N ** 3 / 5, 56 * _N ** 3 / 15]
_K0, _E0, _LON0 = 0.9996, 500000.0, math.radians(-87.0)


def ll_to_utm(lon, lat):
    lon, lat = np.radians(np.asarray(lon, float)), np.radians(np.asarray(lat, float))
    e = 2 * math.sqrt(_N) / (1 + _N)
    t = np.sinh(np.arctanh(np.sin(lat)) - e * np.arctanh(e * np.sin(lat)))
    dl = lon - _LON0
    xi, eta = np.arctan(t / np.cos(dl)), np.arctanh(np.sin(dl) / np.sqrt(1 + t * t))
    E = eta + sum(a * np.cos(2 * j * xi) * np.sinh(2 * j * eta) for j, a in enumerate(_ALPHA, 1))
    N = xi + sum(a * np.sin(2 * j * xi) * np.cosh(2 * j * eta) for j, a in enumerate(_ALPHA, 1))
    return _E0 + _K0 * _AA * E, _K0 * _AA * N


def utm_to_ll(E, N):
    xi, eta = np.asarray(N, float) / (_K0 * _AA), (np.asarray(E, float) - _E0) / (_K0 * _AA)
    xp = xi - sum(b * np.sin(2 * j * xi) * np.cosh(2 * j * eta) for j, b in enumerate(_BETA, 1))
    ep = eta - sum(b * np.cos(2 * j * xi) * np.sinh(2 * j * eta) for j, b in enumerate(_BETA, 1))
    chi = np.arcsin(np.sin(xp) / np.cosh(ep))
    lat = chi + sum(d * np.sin(2 * j * chi) for j, d in enumerate(_DELTA, 1))
    return np.degrees(_LON0 + np.arctan(np.sinh(ep) / np.cos(xp))), np.degrees(lat)


# ---- geometry helpers ----
def r1(v):
    return round(float(v), 1)


def r2(v):
    return round(float(v), 2)


def interp_path(path_c, xy, c):
    """plan point at chainage c on a path given as chainages and points"""
    return np.array([np.interp(c, path_c, xy[:, 0]), np.interp(c, path_c, xy[:, 1])])


def project(path_c, xy, q):
    """chainage and signed offset (+ left) of point q on a polyline"""
    best = (1e18, 0.0, 0.0)
    for i in range(len(xy) - 1):
        a, b = xy[i], xy[i + 1]
        d = b - a
        L2 = float(d @ d)
        if L2 < 1e-9:
            continue
        s = min(1.0, max(0.0, float((q - a) @ d) / L2))
        p = a + s * d
        dist = float(np.hypot(*(q - p)))
        if dist < best[0]:
            off = float(d[0] * (q - a)[1] - d[1] * (q - a)[0]) / math.sqrt(L2)
            best = (dist, path_c[i] + s * (path_c[i + 1] - path_c[i]), off)
    return best


def load_lines(cache):
    out = {}
    for sysk, idx in (('metro', 'profiles/lines/index.json'), ('rer', 'profiles/rer/lines/index.json')):
        base = os.path.dirname(os.path.join(cache, idx))
        for l in json.load(open(os.path.join(cache, idx))):
            d = json.load(open(os.path.join(base, l['id'] + '.json')))
            d['sys'] = sysk
            out[l['id']] = d
    return out


def ranges_near(d, E0, N0, radius):
    """chainage ranges of a line inside the square of half-side radius around the origin (with a 50 m margin)"""
    p = np.array(d['path'], float)
    E, N = ll_to_utm(p[:, 1], p[:, 2])
    c = p[:, 0]
    cc = np.arange(0, d['length_m'], 2.0)
    x, y = np.interp(cc, c, E) - E0, np.interp(cc, c, N) - N0
    m = (np.abs(x) <= radius + 50) & (np.abs(y) <= radius + 50)
    if not m.any():
        return []
    runs, start = [], None
    for i, v in enumerate(m):
        if v and start is None:
            start = i
        if not v and start is not None:
            runs.append((cc[start], cc[i - 1])); start = None
    if start is not None:
        runs.append((cc[start], cc[-1]))
    return runs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', default=os.path.join(HERE, 'cache'))
    ap.add_argument('--out', default=os.path.join(HERE, 'cache', 'snapshot.json'))
    ap.add_argument('--area', default='fountain_square')
    ap.add_argument('--dry-run', action='store_true', help='print levels at the station, write nothing to the page')
    a = ap.parse_args()
    area = AREAS[a.area]
    E0, N0 = (float(v) for v in ll_to_utm(area['lon'], area['lat']))
    R = area['radius']

    lines = load_lines(a.cache)
    job = {'lines': [], 'deck': True}
    for lid, d in lines.items():
        rs = ranges_near(d, E0, N0, R)
        if rs:
            job['lines'].append({'id': lid, 'c0': float(min(r[0] for r in rs)), 'c1': float(max(r[1] for r in rs))})
    jf, rf = os.path.join(a.cache, 'job.json'), os.path.join(a.cache, 'harness_out.json')
    json.dump(job, open(jf, 'w'))
    print('lines near', area['name'] + ':', ', '.join(j['id'] for j in job['lines']), file=sys.stderr)
    subprocess.run(['node', os.path.join(HERE, 'harness.js'), a.cache, jf, rf], check=True)
    H = json.load(open(rf))

    issues = []
    snap_lines, ground_pts = [], []
    for j in job['lines']:
        lid, d, h = j['id'], lines[j['id']], H['profiles'][j['id']]
        p = np.array(d['path'], float)
        E, N = ll_to_utm(p[:, 1], p[:, 2])
        xy = np.c_[E - E0, N - N0]
        g = np.array([np.nan if v is None else v / 10 for v in d['ground_dm']])
        pts, runs, cur = [], [], None
        for c, z, t in h['samples']:
            q = interp_path(p[:, 0], xy, c)
            if abs(q[0]) > R + 50 or abs(q[1]) > R + 50:
                continue
            gz = float(np.interp(c, np.arange(len(g)) * d['step_m'], g))
            pts.append([r1(c), r2(q[0]), r2(q[1]), r2(z), r2(gz)])
            if not math.isnan(gz) and abs(q[0]) <= R and abs(q[1]) <= R:
                ground_pts.append((q[0], q[1], gz))
            if cur is None or cur['t'] != t:
                cur = {'t': t, 'c0': r1(c), 'c1': r1(c), 'st': structure(lid, t)}
                runs.append(cur)
            cur['c1'] = r1(c)
        # stations on this stretch: platform centre (drawn point + offset), rail level from the saved levels
        al = h['align']
        L_pl = PLATFORM_M[d['sys']]
        # as the editor's deriveStations: drop deleted stations (keyed name, or name#index when a name repeats),
        # then move each platform centre by its offset
        names = [s['name'] for s in d['stations']]
        key = lambda i, s: f"{s['name']}#{i}" if names.count(s['name']) > 1 else s['name']
        kept = [s for i, s in enumerate(d['stations']) if key(i, s) not in set(al.get('del') or [])]
        sts = []
        for i, s in enumerate(kept):
            so = al['so'][i] if i < len(al.get('so') or []) else 0
            cmid = s['c'] + (so or 0)
            if not (j['c0'] - L_pl <= cmid <= j['c1'] + L_pl):
                continue
            rail = al['st'][i] if i < len(al.get('st', [])) else None
            q = interp_path(p[:, 0], xy, cmid)
            sts.append({'name': s['name'], 'c': r1(cmid), 'x': r2(q[0]), 'y': r2(q[1]),
                        'rail': r2(rail) if rail is not None else None, 'platform_m': L_pl,
                        'from_c': r1(cmid - L_pl / 2), 'to_c': r1(cmid + L_pl / 2)})
        if not h['saved']:
            issues.append(f"{d['line']}: no saved alignment in the Profiles editor; drawn from its built-in defaults (unsaved)")
        name = d['line'] if d['sys'] == 'metro' else f"{d['line']} (TRI {RER_LETTER.get(lid, '?')})"
        snap_lines.append({'id': lid, 'name': name, 'sys': d['sys'], 'color': d.get('color'), 'saved': h['saved'],
                           'pts': pts, 'runs': runs, 'stations': sts})

    # ground: a plane fitted to the Profiles ground inside the area
    G = np.array(ground_pts)
    A = np.c_[G[:, 0], G[:, 1], np.ones(len(G))]
    gx, gy, gz = np.linalg.lstsq(A, G[:, 2], rcond=None)[0]
    resid = G[:, 2] - A @ np.array([gx, gy, gz])

    # Deck: streets, blocks, transit plan lines, stations and platforms inside the area
    def to_local(coords):
        c = np.asarray(coords, float)
        E, N = ll_to_utm(c[..., 0], c[..., 1])
        return np.stack([E - E0, N - N0], -1)

    def inside(xy, m=0):
        return bool(((np.abs(xy[..., 0]) <= R + m) & (np.abs(xy[..., 1]) <= R + m)).any())

    deck = {'streets': [], 'blocks': [], 'lines': [], 'stations': [], 'platforms': []}
    for f in H['deck']['features']:
        p, g = f['properties'], f.get('geometry')
        L = p.get('layer')
        if not g or L not in ('street', 'block', 'metro_line', 'rer_line', 'metro_station', 'rer_station',
                              'metro_platform', 'rer_platform'):
            continue
        if L == 'street':
            xy = to_local(g['coordinates'])
            if inside(xy, 30):
                deck['streets'].append({'id': p['id'], 'name': p.get('name', ''), 'w': p.get('width_m'),
                                        'kind': p.get('kind'), 'c': [[r1(a), r1(b)] for a, b in xy]})
        elif L == 'block':
            rings = g['coordinates'] if g['type'] == 'Polygon' else [r for poly in g['coordinates'] for r in poly[:1]]
            xy = to_local(rings[0])
            if inside(xy):
                deck['blocks'].append({'id': p['id'], 'type': p.get('type'), 'name': p.get('name', ''),
                                       'c': [[r1(a), r1(b)] for a, b in xy]})
        elif L.endswith('_line'):
            xy = to_local(g['coordinates'])
            if inside(xy):
                deck['lines'].append({'id': p['id'], 'name': p['name'], 'sys': L.split('_')[0],
                                      'c': [[r1(a), r1(b)] for a, b in xy]})
        elif L.endswith('_station'):
            xy = to_local(g['coordinates'])
            if inside(xy) and not p.get('deleted'):
                deck['stations'].append({'id': p['id'], 'name': p['name'], 'sys': L.split('_')[0], 'lines': p.get('lines'),
                                         'x': r2(xy[0]), 'y': r2(xy[1])})
        elif L.endswith('_platform'):
            xy = to_local(g['coordinates'][0])
            if inside(xy):
                deck['platforms'].append({'station': p['station'], 'line': p['line'], 'sys': L.split('_')[0],
                                          'type': p.get('type'), 'n': p.get('n'), 'c': [[r2(a), r2(b)] for a, b in xy]})

    # platforms: Deck plan; level from the matching Profiles line at the platform's centre
    def match(pl):
        name = pl['line']
        if pl['sys'] == 'metro':
            ids = ['Line_' + name.split('Line ')[-1].strip()]
        else:
            letters = name.split('RER ')[-1].replace('/', '')
            ids = [k for k, v in RER_LETTER.items() if v in letters]
        return [l for l in snap_lines if l['id'] in ids]

    for pl in deck['platforms']:
        ring = np.array(pl['c'])
        ctr = ring[:-1].mean(0) if len(ring) > 1 and np.allclose(ring[0], ring[-1]) else ring.mean(0)
        pl['levels'] = []
        for l in match(pl):
            P = np.array([q[1:3] for q in l['pts']])
            cs = np.array([q[0] for q in l['pts']])
            if len(P) < 2:
                continue
            dist, c, off = project(cs, P, ctr)
            if dist > 40:
                issues.append(f"{pl['line']} platform at {pl['station']} is {dist:.0f} m from {l['name']}'s Profiles path")
                continue
            rail = float(np.interp(c, cs, [q[3] for q in l['pts']]))
            pl['levels'].append({'line': l['id'], 'c': r1(c), 'rail': r2(rail), 'off': r1(off), 'dist': r1(dist),
                                 'top': r2(rail + PLATFORM_ABOVE_RAIL[pl['sys']])})
        if not pl['levels']:
            issues.append(f"{pl['line']} platform at {pl['station']}: no Profiles line found for its level")
        # platform length as drawn in the Deck against the rule
        e = ring[:-1] if np.allclose(ring[0], ring[-1]) else ring
        dists = [np.hypot(*(e[i] - e[j])) for i in range(len(e)) for j in range(i + 1, len(e))]
        span = max(dists) if dists else 0
        pl['length_drawn'] = r1(span)

    snap = {
        'area': a.area, 'name': area['name'], 'synced_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'origin': {'lon': area['lon'], 'lat': area['lat'], 'E': r2(E0), 'N': r2(N0), 'crs': 'EPSG:32616'},
        'frame_turn_deg': area['frame_turn'], 'radius': R,
        'ground': {'plane': [round(gx, 6), round(gy, 6), r2(gz)], 'fit_rms': r2(np.sqrt((resid ** 2).mean())),
                   'n': int(len(G))},
        'platform_m': PLATFORM_M, 'platform_above_rail': PLATFORM_ABOVE_RAIL,
        'struct': {'metro': METRO_ST, 'rer': RER_ST, 'open': OPEN_ST}, 'assumed': ASSUMED,
        'sources': {'profiles': H.get('profiles_version'), 'deck': H.get('deck_version'),
                    'profiles_saved': {l['id']: l['saved'] for l in snap_lines}},
        'lines': snap_lines, 'deck': deck, 'issues': issues,
    }
    meta = os.path.join(a.cache, 'versions.json')
    if os.path.exists(meta):
        snap['sources'].update(json.load(open(meta)))
    json.dump(snap, open(a.out, 'w'), separators=(',', ':'))

    # the 3D page's database documents: snapshots/<area> (everything but the bulk, as JSON text) and its parts
    # snapshots/<area>/parts/{lines,deck}, each kept well under the document size limit
    ddir = os.path.join(os.path.dirname(a.out), 'db_out')
    os.makedirs(ddir, exist_ok=True)
    parts = {'lines': {'lines': snap['lines']}, 'deck': {'deck': snap['deck']}}
    head = {k: v for k, v in snap.items() if k not in ('lines', 'deck')}
    for k, v in parts.items():
        json.dump({'json': json.dumps(v, separators=(',', ':')), 'synced_at': snap['synced_at']}, open(os.path.join(ddir, k + '.json'), 'w'))
    json.dump({'json': json.dumps(head, separators=(',', ':')), 'parts': list(parts), 'synced_at': snap['synced_at']},
              open(os.path.join(ddir, 'meta.json'), 'w'))

    # report: rail levels at the area's stations
    for l in snap_lines:
        for s in l['stations']:
            if s['name'] in area['stations']:
                print(f"{l['name']:<22} {s['name']}: rail {s['rail']} m", file=sys.stderr)
    print(f"ground plane z = {gz:.2f} + {gx * 1000:.1f}/km x + {gy * 1000:.1f}/km y (rms {np.sqrt((resid ** 2).mean()):.2f} m)",
          file=sys.stderr)
    print(f"{len(snap_lines)} lines, {len(deck['platforms'])} platforms, {len(deck['streets'])} streets, "
          f"{len(deck['blocks'])} blocks; {len(issues)} issues -> {a.out} ({os.path.getsize(a.out) // 1024} KB)", file=sys.stderr)
    for i in issues:
        print('  issue:', i, file=sys.stderr)


if __name__ == '__main__':
    main()
