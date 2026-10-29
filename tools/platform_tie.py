"""Platform moves from the Rail Profiles to the Deck (Ben, 29 October: "it should run in both directions; when one has
been updated more recently, it pulls the changes from that one to the other").

A platform slid in the Profiles (a saved profile's `so`, metres along the line from its station point) on a station whose
platform is drawn on the Deck is written into the Deck layout as that platform's offset along its Deck line piece
(`stations[station id].s[piece id].o`). The Deck tie that follows puts the station at the moved platform's centre and
clears the slide, so the Deck, the Profiles and the 3D map agree.

Which side wins, per platform: the sync record (hub `params/platform_sync`: each platform's Deck offset when the two
last agreed) tells whether the Deck has moved that platform since. If only the Profiles moved it, the Profiles win; if
only the Deck, the Deck (the Deck tie resets the slide); if both, the record saved more recently (the profile, or the
Deck layout). With no sync record yet, the more recent record wins.

Usage (the hub's pipeline runs it):
    python3 tools/platform_tie.py --docs DIR --layout LAYOUT.json --times TIMES.json [--sync SYNC.json]
        [--geojson data/deck/rer_routes.geojson] --out OUT.json
  TIMES.json: {"deck/layout": epoch, "alignments/<id>": epoch, ...}; OUT.json: {"layout": layout or null, "moves": [...]}
    python3 tools/platform_tie.py --snapshot [--geojson ...] --out SYNC.json   (the sync record from the Deck's export)
"""
import argparse
import glob
import json
import os
import sys

from shapely.geometry import LineString, Point, Polygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rer_deck_routes import LIVE, PLAT_REACH, SITE, TO_UTM, is_metro, jload, st_keys   # noqa: E402

MOVED_M = 0.05   # a Deck offset that changed by more than this since the last sync was moved on the Deck


def deck_export(geojson):
    fc = jload(geojson)
    lines, plats = {}, []
    for f in fc['features']:
        p, g = f['properties'], f['geometry']
        if p.get('layer') in ('rer_line', 'metro_line') and g['type'] == 'LineString':
            lines[p['id']] = LineString([TO_UTM.transform(*q[:2]) for q in g['coordinates']])
        elif p.get('layer') in ('rer_platform', 'metro_platform') and p.get('pid') and g['type'] in ('Polygon', 'MultiPolygon'):
            ring = g['coordinates'][0] if g['type'] == 'Polygon' else g['coordinates'][0][0]
            plats.append(dict(p, centre=Polygon([TO_UTM.transform(*q[:2]) for q in ring]).centroid))
    # one entry per platform (a side-platform station draws two rings: their mean)
    by = {}
    for q in plats:
        by.setdefault((q['station_id'], q['pid']), []).append(q)
    out = []
    for (sid, pid), qs in by.items():
        c = Point(sum(q['centre'].x for q in qs) / len(qs), sum(q['centre'].y for q in qs) / len(qs))
        out.append(dict(qs[0], centre=c))
    return lines, out


def snapshot(geojson):
    _, plats = deck_export(geojson)
    return {'about': 'Each Deck platform offset when the Deck and the Profiles last agreed (tools/platform_tie.py)',
            'offsets': {f"{q['station_id']}|{q['pid']}": q['offset_m'] for q in plats}}


def route_file(rid):
    f = os.path.join(SITE, 'lines', rid + '.json') if is_metro(rid) else os.path.join(SITE, 'rer', 'lines', rid + '.json')
    return f if os.path.exists(f) else None


def label_ok(rid, route, label):
    if is_metro(rid):
        return label == 'Metro ' + route.get('line', '')
    letter = rid.split('_')[1] if rid.startswith('RER_') else None
    return bool(letter) and label.startswith('RER') and letter in label.replace('RER', '').replace('/', ' ').split()


def tie(docs, layout, times, sync, geojson):
    lines, plats = deck_export(geojson)
    last = (sync or {}).get('offsets')
    t_deck = float(times.get('deck/layout') or 0)
    lay = json.loads(json.dumps(layout))
    lay.setdefault('stations', {})
    moves = []
    for f in sorted(glob.glob(os.path.join(docs, '*.json'))):
        rid = os.path.basename(f)[:-5]
        doc = jload(f)
        so = doc.get('so') or {}
        if not any(abs(float(v or 0)) > 0.01 for v in so.values()):
            continue
        rf = route_file(rid)
        if not rf:
            continue
        route = jload(rf)
        path = route['path']
        L = LineString([TO_UTM.transform(p[1], p[2]) for p in path])
        cs = [p[0] for p in path]

        def at(c):   # the route's point at chainage c (the profile's path)
            c = max(cs[0], min(cs[-1], c))
            for i in range(1, len(cs)):
                if cs[i] >= c:
                    t = (c - cs[i - 1]) / ((cs[i] - cs[i - 1]) or 1)
                    a, b = L.coords[i - 1], L.coords[i]
                    return Point(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            return Point(L.coords[-1])
        t_doc = float(times.get('alignments/' + rid) or 0)
        for s, k in zip(route['stations'], st_keys(route)):
            v = float(so.get(k) or 0)
            if abs(v) <= 0.01:
                continue
            here = at(s['c'])
            cand = [q for q in plats if q['station'] == s['name'] and label_ok(rid, route, q.get('line', '')) and L.distance(q['centre']) <= PLAT_REACH]
            if not cand:
                moves.append({'route': rid, 'station': s['name'], 'slide': v, 'done': False, 'why': 'no platform drawn on the Deck: the slide stays in the profile'})
                continue
            q = min(cand, key=lambda q: q['centre'].distance(here))
            D = lines.get(q['pid'])
            if D is None:
                continue
            key = f"{q['station_id']}|{q['pid']}"
            deck_moved = last is not None and key in last and abs(float(last[key]) - float(q['offset_m'])) > MOVED_M
            profile_newer = t_doc >= t_deck
            if (deck_moved or last is None) and not profile_newer:
                moves.append({'route': rid, 'station': s['name'], 'slide': v, 'done': False, 'why': 'moved on the Deck more recently: the Deck wins (the slide is reset)'})
                continue
            new = at(s['c'] + v)
            o_new = float(q['offset_m']) + D.project(new) - D.project(q['centre'])
            cap = float(q.get('slide_max_m') or 150.0)
            note = ''
            if abs(o_new) > cap:
                note = f'; held at the Deck\'s {cap:.0f} m slide limit'
                o_new = max(-cap, min(cap, o_new))
            e = lay['stations'].setdefault(q['station_id'], {})
            e.setdefault('s', {}).setdefault(q['pid'], {})['o'] = round(o_new, 1)
            moves.append({'route': rid, 'station': s['name'], 'key': k, 'slide': v, 'done': True, 'deck_station': q['station_id'], 'pid': q['pid'],
                          'from_o': q['offset_m'], 'to_o': round(o_new, 1), 'why': ('both moved; the profile is more recent' if deck_moved else 'moved in the Profiles') + note})
    changed = any(m['done'] for m in moves)
    if changed:
        import datetime
        lay['updated'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    return {'layout': lay if changed else None, 'moves': moves}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--docs')
    ap.add_argument('--layout')
    ap.add_argument('--times')
    ap.add_argument('--sync')
    ap.add_argument('--geojson', default=LIVE)
    ap.add_argument('--snapshot', action='store_true')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if a.snapshot:
        json.dump(snapshot(a.geojson), open(a.out, 'w'), indent=1)
        return
    sync = jload(a.sync) if a.sync and os.path.exists(a.sync) else None
    r = tie(a.docs, jload(a.layout), jload(a.times), sync, a.geojson)
    json.dump(r, open(a.out, 'w'), ensure_ascii=False)
    for m in r['moves']:
        print(f"{m['route']} {m['station']}: slide {m['slide']:+.1f} m: " + (f"Deck offset {m['from_o']} -> {m['to_o']} m ({m['why']})" if m['done'] else m['why']))
    if not r['moves']:
        print('No platform slides in the profiles')


if __name__ == '__main__':
    main()
