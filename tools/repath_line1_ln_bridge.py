"""Line 1 over the L&N bridge (Ben, 2 November 2026): "I have changed Line 1 to be elevated using the L&N bridge ...
it should connect to the existing Line 1 at both ends. Both Newport stations move east to meet it."

Ben's path (data/kmz/Line_1_LN_bridge.kmz, from New_Line_1.kmz) leaves Line 1 just east of Taft Theater and rejoins it
just south of Newport Central. This puts it in the Mill Creek Deck, which every Metro line is tied to:

- the Deck's two Line 1 pieces (`M-L1-714186-4339800`, which ends where Line 1 crosses E 716,800, and
  `M-L1-716800-4329894`) take the new path between the two joins, split again at E 716,800: in Ben's layout edits
  (`hub/seed/deck/layout.json` `transit`, the line as he drew it) and in the Deck's generated lines (both
  `context.json`), so "Reset this line" on the Deck does not bring the old path back;
- the station points of Pennsylvania Station, Levee, Newport-6th, Newport-9th and Newport Central go to Ben's points
  (projected onto the path) and their generated Line 1 platforms are redrawn there (one island each; the Deck draws the
  platform type and spacing from the structure settings and the Profiles). Levee is also Line 11's: its Line 11 platform
  is not moved (the Deck measures it from the station point it is generated against, so it stays where it was);
- Deck station edits keyed by the old points move to the new keys (the Pennsylvania Station side platforms); the Levee
  slide (-0.8 m against the old point) is dropped;
- the line file's Deck segs (`data/profile/lines/Line_1.json`) take the new piece ends, so the next Deck tie rebuilds
  Line 1 on the new path (`tools/rer_deck_routes.py`; the hub's Deck tie runs it on the next start after the seed).

Run once: python tools/repath_line1_ln_bridge.py [--kmz PATH]
"""
import argparse
import json
import math
import os
import re
import zipfile

from pyproj import Transformer
from shapely.geometry import LineString, Point

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TO_UTM = Transformer.from_crs(4326, 26916, always_xy=True)
P1, P2 = 'M-L1-714186-4339800', 'M-L1-716800-4329894'
SPLIT_E = 716800.0
MOVED = {'Pennsylvania': 'Pennsylvania Station', 'Levee': 'Levee', 'Newport-6th': 'Newport-6th', 'Newport-9th': 'Newport-9th', 'Newport Central': 'Newport Central'}
ISLAND = 8.0   # the Deck's Metro island width (drawing value, context meta metro_twin)
PLAT = 121.92


def jload(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def jsave(p, d, compact=False):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, separators=(',', ':') if compact else None, indent=None if compact else 1)


def read_kmz(path):
    with zipfile.ZipFile(path) as z:
        t = z.read('doc.kml').decode('utf-8')
    pms = re.findall(r'<Placemark>.*?</Placemark>', t, re.S)
    line, pts = None, {}
    for pm in pms:
        name = re.search(r'<name>(.*?)</name>', pm).group(1)
        xy = [TO_UTM.transform(*map(float, q.split(',')[:2])) for q in re.search(r'<coordinates>(.*?)</coordinates>', pm, re.S).group(1).split()]
        if '<LineString>' in pm:
            line = xy
        else:
            pts[name] = xy[0]
    return line, pts


def qpt(a, k, b, t):
    u = 1 - t
    return (u * u * a[0] + 2 * u * t * k[0] + t * t * b[0], u * u * a[1] + 2 * u * t * k[1] + t * t * b[1])


def curve(v, K):
    """the Deck's drawn line: straight segments, or quadratic curves where K[i] holds a control point"""
    out = [tuple(v[0])]
    for i in range(len(v) - 1):
        a, b, k = v[i], v[i + 1], (K or {}).get(str(i))
        if k:
            n = max(6, min(48, math.ceil(math.dist(a, b) / 3)))
            out += [qpt(a, k, b, j / n) for j in range(1, n + 1)]
        else:
            out.append(tuple(b))
    return out


def locate(v, K, p):
    """(segment index, t) of the point of the drawn line nearest p"""
    best = None
    for i in range(len(v) - 1):
        a, b, k = v[i], v[i + 1], (K or {}).get(str(i))
        if not k:   # straight: the exact foot of the perpendicular
            dx, dy = b[0] - a[0], b[1] - a[1]
            t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / ((dx * dx + dy * dy) or 1e-9)))
            d = math.dist((a[0] + dx * t, a[1] + dy * t), p)
            if best is None or d < best[0]:
                best = (d, i, t)
            continue
        m = max(200, int(math.dist(a, b) / 0.1))
        for j in range(m + 1):
            t = j / m
            q = qpt(a, k, b, t) if k else (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            d = math.dist(q, p)
            if best is None or d < best[0]:
                best = (d, i, t)
    return best


def split_seg(a, k, b, t):
    """a quadratic (or straight) segment cut at t: (first part's control, the cut point, second part's control)"""
    if not k:
        q = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        return None, q, None
    k1 = (a[0] + (k[0] - a[0]) * t, a[1] + (k[1] - a[1]) * t)
    k2 = (k[0] + (b[0] - k[0]) * t, k[1] + (b[1] - k[1]) * t)
    q = (k1[0] + (k2[0] - k1[0]) * t, k1[1] + (k2[1] - k1[1]) * t)
    return k1, q, k2


def r1(p):
    return [round(p[0], 1), round(p[1], 1)]


def splice(v1, K1, v2, K2, new):
    """piece 1 up to the first point of the new path, the new path, piece 2 from its last point; cut at E 716,800"""
    d0, i0, t0 = locate(v1, K1, new[0])
    d1, i1, t1 = locate(v2, K2, new[-1])
    assert d0 < 1.0 and d1 < 1.0, (d0, d1)
    ka, q0, _ = split_seg(v1[i0], (K1 or {}).get(str(i0)), v1[i0 + 1], t0)
    _, q1, kb = split_seg(v2[i1], (K2 or {}).get(str(i1)), v2[i1 + 1], t1)
    head = [tuple(p) for p in v1[:i0 + 1]] + [q0]
    kh = {str(j): (K1 or {})[str(j)] for j in range(i0) if (K1 or {}).get(str(j))}
    if ka:
        kh[str(i0)] = r1(ka)
    tail = [q1] + [tuple(p) for p in v2[i1 + 1:]]
    kt = {}
    if kb:
        kt['0'] = r1(kb)
    for j in range(i1 + 1, len(v2) - 1):
        if (K2 or {}).get(str(j)):
            kt[str(j - i1)] = (K2 or {})[str(j)]
    mid = [tuple(p) for p in new[1:-1]]
    # the whole line, then cut at E 716,800 (the piece boundary the Deck draws)
    allv = head + mid + tail
    nh = len(head)
    kall = dict(kh)
    for j, k in kt.items():
        kall[str(int(j) + nh + len(mid))] = k
    for i in range(nh - 1, nh + len(mid)):
        a, b = allv[i], allv[i + 1]
        if (a[0] - SPLIT_E) * (b[0] - SPLIT_E) <= 0 and a[0] != b[0] and str(i) not in kall:
            t = (SPLIT_E - a[0]) / (b[0] - a[0])
            cut = (SPLIT_E, a[1] + (b[1] - a[1]) * t)
            p1 = allv[:i + 1] + [cut]
            p2 = [cut] + allv[i + 1:]
            k1 = {j: k for j, k in kall.items() if int(j) < i}
            k2 = {str(int(j) - i): k for j, k in kall.items() if int(j) > i}
            return [r1(p) for p in p1], k1, [r1(p) for p in p2], k2
    raise SystemExit('the new path does not cross E 716,800 on a straight segment')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kmz', default=os.path.join(ROOT, 'data', 'kmz', 'Line_1_LN_bridge.kmz'))
    a = ap.parse_args()
    new, pts = read_kmz(a.kmz)
    lay_p = os.path.join(ROOT, 'hub', 'seed', 'deck', 'layout.json')
    lay = jload(lay_p)
    ctx_ps = [os.path.join(ROOT, 'hub', 'sites', 'deck', 'context.json'), os.path.join(ROOT, 'data', 'deck', 'context.json')]
    ctx0 = jload(ctx_ps[0])
    m1 = next(m for m in ctx0['metro'] if m['id'] == P1)
    m2 = next(m for m in ctx0['metro'] if m['id'] == P2)
    e1 = lay['transit'].get(P1) or {'c': m1['c'], 'k': m1.get('k') or {}}
    e2 = lay['transit'].get(P2) or {'c': m2['c'], 'k': m2.get('k') or {}}
    c1, k1, c2, k2 = splice(e1['c'], e1.get('k'), e2['c'], e2.get('k'), new)
    line = LineString(curve(c1, k1)[:-1] + curve(c2, k2))
    print(f'piece 1: {len(e1["c"])} -> {len(c1)} vertices, ends {c1[-1]}; piece 2: {len(e2["c"])} -> {len(c2)}, starts {c2[0]}')
    lay['transit'][P1] = {'c': c1, 'k': k1}
    lay['transit'][P2] = {'c': c2, 'k': k2}

    # the station points: Ben's, on the path
    target = {}
    for kn, nm in MOVED.items():
        p = pts[kn]
        q = line.interpolate(line.project(Point(p)))
        target[nm] = (round(q.x, 1), round(q.y, 1))
        print(f'{nm}: {math.dist(p, (q.x, q.y)):.1f} m off the path; moved')

    def key(nm, p):
        return f'metro:{nm}:{round(p[0])}:{round(p[1])}'
    rekey = {}
    for ctx_p in ctx_ps:
        ctx = jload(ctx_p)
        for m in ctx['metro']:
            if m['id'] in (P1, P2):
                c, k = (c1, k1) if m['id'] == P1 else (c2, k2)
                old = LineString(curve(m['c'], m.get('k')))
                m['c'] = c
                if 'k' in m or k:
                    m['k'] = k
                mine = LineString(curve(c, k))
                # bored-flag samples every 20 m: kept where the line is unchanged, 0 (not bored) on the new path; the
                # Deck takes the spacing from the Profiles' tube points once the 3D build has run
                hs = [h for h in m.get('hs', []) if mine.distance(Point(h[0], h[1])) < 1.0 and old.distance(Point(h[0], h[1])) < 1.0]
                keep = LineString(curve(c, k))
                for d in range(0, int(keep.length) + 1, 20):
                    q = keep.interpolate(d)
                    if old.distance(q) > 1.0:
                        hs.append([round(q.x, 1), round(q.y, 1), 0])
                hs.sort(key=lambda h: keep.project(Point(h[0], h[1])))
                m['hs'] = hs
                if 'curves' in m:
                    m['curves'] = [cv for cv in m['curves'] if mine.distance(Point(cv[1], cv[2])) < 1.0]
        for s in ctx['stations']:
            if s['name'] in target and 'Line 1' in s['line']:
                if ctx_p == ctx_ps[0]:
                    rekey[key(s['name'], s['p'])] = key(s['name'], target[s['name']])
                s['p'] = list(target[s['name']])
        # the moved stations' generated Line 1 platforms: one island on the new line, centred on the station point
        ctx['plats'] = [q for q in ctx['plats'] if not (q.get('pid') in (P1, P2) and q.get('st') in target)]
        for nm, p in target.items():
            pid = P1 if p[0] < SPLIT_E else P2
            g = LineString(curve(c1, k1) if pid == P1 else curve(c2, k2))
            s0 = g.project(Point(p))
            ring_l, ring_r = [], []
            for j in range(9):
                s = max(0.0, min(g.length, s0 - PLAT / 2 + PLAT * j / 8))
                q, q2 = g.interpolate(s), g.interpolate(min(g.length, s + 0.5))
                tx, ty = q2.x - q.x, q2.y - q.y
                L = math.hypot(tx, ty) or 1.0
                nx, ny = -ty / L, tx / L
                ring_l.append([round(q.x + nx * ISLAND / 2, 1), round(q.y + ny * ISLAND / 2, 1)])
                ring_r.append([round(q.x - nx * ISLAND / 2, 1), round(q.y - ny * ISLAND / 2, 1)])
            ring = ring_l + ring_r[::-1]
            ring.append(ring[0])
            ctx['plats'].append({'sys': 'metro', 'line': 'Line 1', 'pid': pid, 'c': ring, 'st': nm, 'id': f'P-M-L1-{round(p[0])}-{round(p[1])}'})
        jsave(ctx_p, ctx, compact=True)
    # Deck station edits keyed by the old points
    for old, nk in rekey.items():
        e = lay['stations'].pop(old, None)
        if not e:
            continue
        s = e.get('s') or {}
        for pid in list(s):
            if pid in (P1, P2):
                s[pid].pop('o', None)   # the slide was against the old point
                if not s[pid]:
                    del s[pid]
        if not s:
            e.pop('s', None)
        if e:
            lay['stations'][nk] = e
        print(f'station edit {old} -> {nk if e else "(dropped)"}: {e}')
    lay['updated'] = '2026-11-02T12:00:00.000Z'
    jsave(lay_p, lay)
    # the line file's Deck segs: the new piece ends
    lp = os.path.join(ROOT, 'data', 'profile', 'lines', 'Line_1.json')
    d = jload(lp)
    for s in d['segs']:
        if s['piece'] == P1:
            s['v'] = c1[-1]
        if s['piece'] == P2:
            s['u'] = c2[0]
    jsave(lp, d, compact=True)
    print('done: run the Deck tie (the hub does on its next start; or tools/rer_deck_routes.py --apply --only Line_1 with a Deck export)')


if __name__ == '__main__':
    main()
