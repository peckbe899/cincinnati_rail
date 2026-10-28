"""The north arch viaduct widened for the catenary's middle masts, and the streets beside it (Ben, 28 October; viaduct
handoff sections 5 and 7). Run once on the Deck's base files and layout record; rerunning it starts again from the git
copies (`--from-git`).

- Widening: both APEx-side gaps from 4.5 to 6.0 m. "Widen on a side": the opposite face stays, the APEx tracks move 1.5 m
  toward the widened side and the near ORR / Transvalley pair 3.0 m. By stretch, along APEx north approach track 3 from
  the CUT north throat: the straight north from CUT (to about 1,250 m) on the west (Exposition Boulevard) side; from the
  turn to the north-west (1,250-1,650 m) to Queen Street on the north-east / east side (Spring Grove, J1); north of Queen
  Street on the north-west side. Side switches inside the curves (1,250-1,650 m and 3,250-3,900 m, Queen Street at about
  3,530 m), eased; tapered out at the CUT throat (the first 150 m) and toward Ludlow (the last 200 m). R5 follows the west
  pair where it runs with it. The north arch viaduct polygon grows by the tracks' 4.2 m deck edge.
- MT (basin SMV0032) along the west face and J1 (layout S056) along the east face, from Hopple to their north ends, with
  their near edge 2.3 m from the structure (layout edits, undoable on the Deck); the Millvale cross streets (M1-M20)
  end at the moved MT.
- Frontage streets for the arcade shops (section 7.4), Bank to Hopple, both sides, against the widened faces: about 15 m
  (4.5 m sidewalk along the arcade, 2.4 parking, 3.4 lane one way, 2.4 parking, 2.4 sidewalk), one-way with parking when
  built, pedestrian today with a 6.1 m fire lane; added to deck.json (S080, S081).

Usage: python3 tools/deck_widen.py [--db hub/hub.db]   (writes hub/sites/deck/*.json, data/deck/*.json and the layout)
"""
import argparse
import json
import math
import os
import sqlite3
import subprocess

import numpy as np
from shapely.geometry import LineString, Point, mapping, shape
from shapely.ops import unary_union, nearest_points

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SITE, DATA = os.path.join(ROOT, 'hub', 'sites', 'deck'), os.path.join(ROOT, 'data', 'deck')
GAP_STREET = 2.3
FRONTAGE_W = 15.0


def smooth(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def weights(d, L):
    """(west, east) widening weights along the trunk"""
    start, end = smooth(d / 150.0), smooth((L - d) / 200.0)
    if d < 1250:
        w, e = 1.0, 0.0
    elif d < 1650:
        s = smooth((d - 1250) / 400.0)
        w, e = 1 - s, s
    elif d < 3250:
        w, e = 0.0, 1.0
    elif d < 3900:
        s = smooth((d - 3250) / 650.0)
        w, e = s, 1 - s
    else:
        w, e = 1.0, 0.0
    k = start * end
    return w * k, e * k


def densify(line, step=5.0):
    n = max(2, int(math.ceil(line.length / step)) + 1)
    return LineString([line.interpolate(line.length * i / (n - 1)) for i in range(n)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=os.path.join(ROOT, 'hub', 'hub.db'))
    ap.add_argument('--from-git', action='store_true', help='start from the committed base files')
    a = ap.parse_args()
    load = lambda f: json.loads(subprocess.check_output(['git', 'show', 'HEAD:hub/sites/deck/' + f], cwd=ROOT)) if a.from_git else json.load(open(os.path.join(SITE, f)))
    T, ST, DK, BA = load('tracks.json'), load('structures.json'), load('deck.json'), load('basin.json')
    ref = [LineString(f['geometry']['coordinates']) for f in T['features'] if f['properties'].get('name') == 'APEx north approach 3 of 6'][0]
    if ref.coords[0][1] > ref.coords[-1][1]:
        ref = LineString(ref.coords[::-1])
    L = ref.length

    def frame(x, y):
        d = ref.project(Point(x, y))
        p0, p1 = ref.interpolate(max(0, d - 2)), ref.interpolate(min(L, d + 2))
        tx, ty = p1.x - p0.x, p1.y - p0.y
        n = math.hypot(tx, ty) or 1
        return d, -ty / n, tx / n          # chainage, left normal (west on the straight north)

    def group(name):
        if name.startswith('Lower-level pair W') and 'on the viaduct' in name:
            return 'W'
        if name.startswith('Lower-level pair E') and 'on the viaduct' in name:
            return 'E'
        if name.startswith('APEx north approach'):
            return 'A'
        if name.startswith('R5'):
            return 'R5'
        return None

    shift = {'W': lambda w, e: 3.0 * w, 'A': lambda w, e: 1.5 * (w - e), 'E': lambda w, e: -3.0 * e}
    wpair = unary_union([LineString(f['geometry']['coordinates']) for f in T['features'] if group(f['properties'].get('name') or '') == 'W'])
    moved, new_lines = 0, []
    for f in T['features']:
        g = group(f['properties'].get('name') or '')
        if not g or f['geometry']['type'] != 'LineString':
            continue
        line = densify(LineString(f['geometry']['coordinates']))
        out = []
        for x, y in line.coords:
            d, nx, ny = frame(x, y)
            w, e = weights(d, L)
            if g == 'R5':   # with the west pair where it runs on it, fading off as it leaves
                k = max(0.0, min(1.0, 1 - (wpair.distance(Point(x, y)) - 1.0) / 20.0))
                o = shift['W'](w, e) * k
            else:
                o = shift[g](w, e)
                if g == 'A':   # the Indianapolis pair leaving for the upper deck: fade the shift as it leaves the lower deck
                    lat = abs((x - ref.interpolate(d).x) * nx + (y - ref.interpolate(d).y) * ny)
                    o *= max(0.0, min(1.0, 1 - (lat - 15.0) / 15.0))
            out.append((round(x + nx * o, 2), round(y + ny * o, 2)))
        f['geometry']['coordinates'] = [list(p) for p in LineString(out).simplify(0.05).coords]
        new_lines.append(LineString(out))
        moved += 1
    # the north arch viaduct grows by the shifted tracks' deck edge
    for f in ST['features']:
        if f['properties'].get('name') == 'North arch viaduct':
            old = shape(f['geometry'])
            grow = unary_union([l.buffer(4.2, cap_style=2) for l in new_lines]).intersection(old.buffer(8.0))
            new = unary_union([old, grow]).buffer(0.2).buffer(-0.2)
            f['geometry'] = json.loads(json.dumps(mapping(new.simplify(0.1))))
            f['properties']['note'] = (f['properties'].get('note') or '') + '; widened for the catenary middle masts: both APEx-side gaps 6.0 m, by side (Ben, 28 October)'
            struct = new
    # the deck's own edge for the faces: the lower-deck tracks + 4.2 m (the Deck polygon also takes in RER A's viaduct)
    deck = unary_union([l.buffer(4.2, cap_style=2) for l in new_lines]).buffer(6.0).buffer(-6.0)
    # frontage streets, Bank to Hopple, against the widened faces (deck.json)
    bank_d, hopple_d = 128.0, 2172.0
    band = LineString([ref.interpolate(d).coords[0] for d in np.arange(bank_d, hopple_d, 5.0)])
    face = deck.buffer(FRONTAGE_W / 2, join_style=2).boundary
    adds = []
    for side, sid, nm in ((1, 'S080', 'Arcade frontage, west (Bank to Hopple)'), (-1, 'S081', 'Arcade frontage, east (Bank to Hopple)')):
        pts = []
        for d in np.arange(bank_d, hopple_d + 0.1, 10.0):
            p = ref.interpolate(d)
            _, nx, ny = frame(p.x, p.y)
            ray = LineString([(p.x, p.y), (p.x + side * nx * 140, p.y + side * ny * 140)])
            hit = ray.intersection(face)
            cand = [q for q in getattr(hit, 'geoms', [hit]) if q.geom_type == 'Point']
            if cand:
                q = min(cand, key=lambda q: q.distance(p))
                pts.append((round(q.x, 2), round(q.y, 2)))
        if len(pts) > 2:
            line = LineString(pts).simplify(0.3)
            adds.append({'type': 'Feature', 'properties': {'layer': 'street', 'id': sid, 'name': nm, 'kind': 'frontage', 'width_m': FRONTAGE_W, 'side': 'deck',
                         'note': 'frontage street for the shops in the arcade (Ben, 28 October): built one way with parking both sides and a 4.5 m sidewalk along the arcade '
                                 '(4.5 + 2.4 + 3.4 + 2.4 + 2.4 m, drawing values); pedestrian today, keeping a 6.1 m fire lane (no rear access to the shops); direction not set'},
                         'geometry': {'type': 'LineString', 'coordinates': [list(c) for c in line.coords]}})
    DK['features'] = [f for f in DK['features'] if f['properties'].get('id') not in ('S080', 'S081')] + adds
    for d_ in (SITE, DATA):
        json.dump(T, open(os.path.join(d_, 'tracks.json'), 'w'), separators=(',', ':'), ensure_ascii=False)
        json.dump(ST, open(os.path.join(d_, 'structures.json'), 'w'), separators=(',', ':'), ensure_ascii=False)
        json.dump(DK, open(os.path.join(d_, 'deck.json'), 'w'), separators=(',', ':'), ensure_ascii=False)
    # MT and J1 2.3 m off the widened faces, from Hopple to their north ends; the M streets end at MT (layout edits)
    db = sqlite3.connect(a.db)
    lay = json.loads(db.execute("select data from docs where path='deck/layout'").fetchone()[0])
    base = {f['properties']['id']: f for f in BA['features'] + DK['features'] if f['properties'].get('id')}
    E = lay['streets']

    def coords(sid):
        e = E.get(sid) or {}
        return LineString(e.get('c') or base[sid]['geometry']['coordinates'])
    hop_y = 4334891.0
    report = []
    for sid, w in (('SMV0032', 18.29), ('S056', 18.3)):
        old = coords(sid)
        ring = deck.buffer(GAP_STREET + w / 2, join_style=2).boundary
        out = []
        for x, y in densify(old, 10.0).coords:
            if y < hop_y - 20:   # south of Hopple: as it is
                out.append((x, y))
                continue
            q = nearest_points(ring, Point(x, y))[0]
            out.append((round(q.x, 2), round(q.y, 2)))
        new = LineString(out).simplify(0.5)
        moved_m = max(Point(p).distance(new) for p in old.coords)
        E[sid] = dict(E.get(sid) or {}, c=[list(c) for c in new.coords], note='moved to 2.3 m off the widened viaduct (Ben, 28 October)')
        report.append(f'{sid}: moved up to {moved_m:.1f} m')
    mt = coords('SMV0032')
    trimmed = 0
    for i in list(range(1, 25)):
        sid = f'SMV{i:04d}'
        if sid in ('SMV0005', 'SMV0006') or sid not in base or (E.get(sid) or {}).get('del'):
            continue
        l = coords(sid)
        x = l.intersection(mt)
        if x.is_empty:
            continue
        q = x if x.geom_type == 'Point' else list(getattr(x, 'geoms', [x]))[0]
        cs = list(l.coords)
        west_first = cs[0][0] < cs[-1][0]
        dq = l.project(q)
        from shapely.ops import substring
        keep = substring(l, 0, dq) if west_first else substring(l, dq, l.length)
        if keep.length < l.length - 1:
            E[sid] = dict(E.get(sid) or {}, c=[[round(a_, 2), round(b_, 2)] for a_, b_ in keep.coords], note='ends at MT (Ben, 28 October)')
            trimmed += 1
    lay['updated'] = __import__('datetime').datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')
    print(f'tracks moved: {moved}; frontage streets: {len(adds)}; {"; ".join(report)}; M streets ending at MT: {trimmed}')
    json.dump(lay, open(os.path.join(ROOT, 'hub', 'work', 'layout_widened.json'), 'w'), ensure_ascii=False)


if __name__ == '__main__':
    main()
