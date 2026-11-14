"""Guided reading, tracing pass (14 November 2026): points along every street, not only at its crossings.

    cd data/sanborn
    python ../../tools/sanborn/guided/trace.py N stations CROPDIR    -> picks22_guided/22-N/trace.json, crops CROPDIR/t/<id>.jpg
    python ../../tools/sanborn/guided/trace.py N ends CROPDIR        -> picks22_guided/22-N/ends.json,  crops CROPDIR/e/<id>.jpg
                                                                       (after merge_guided.py has merged the station reads)

stations: every today's street on the plate (streets.py), a station every STEP m along it, skipping the stretch within
SKIP m of a crossing with another street (the crossings are read on their own). Each crop is 400 x 400 plate px around
the station with a red cross on it; the readers mark the street's centre line nearest the cross, or say it is not drawn.
ends: for every run of traced points (merge_guided.py), at each end where the street is not traced further (the next
station is not drawn, off the plate, or today's street ends), a 600 x 600 crop past the last traced point: the readers
mark where the street ends on the plate, or say it runs on out of the crop.
"""
import collections, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import streets as S  # noqa: E402
from shapely.geometry import Point  # noqa: E402
STEP, SKIP = 60.0, 25.0
N, PHASE, CROPS = sys.argv[1], sys.argv[2], sys.argv[3].rstrip('/') + '/'
P = S.Plate(N); OUT = S.SP + f'picks22_guided/22-{N}/'; os.makedirs(OUT, exist_ok=True)
ST = P.streets(); BY = {s['sid']: s for s in ST}
if PHASE == 'stations':
    rows = []; os.makedirs(CROPS + 't', exist_ok=True)
    others = {s['sid']: [o['geom'] for o in ST if o['sid'] != s['sid'] and o['name'] != s['name']] for s in ST}
    for s in ST:
        g = s['geom']
        if not g.intersects(P.box): continue
        X = [g.intersection(o) for o in others[s['sid']] if g.intersects(o)]
        xt = [g.project(q) for x in X for q in getattr(x, 'geoms', [x]) if q.geom_type == 'Point']
        L = g.length; n = max(1, int(round(L / STEP))); ts = np.linspace(0, L, n + 1)
        for k, t in enumerate(ts):
            if any(abs(t - u) < SKIP for u in xt): continue
            q = g.interpolate(t); c = P.px(q.x, q.y)
            if not P.on_plate(c, 40): continue
            rows.append(dict(id=None, sid=s['sid'], name=s['name'], t=round(float(t), 1), E=round(q.x, 2), N=round(q.y, 2),
                             pred=[round(float(c[0]), 1), round(float(c[1]), 1)], runs=P.way(g, q), end_today=k in (0, len(ts) - 1)))
    rows.sort(key=lambda r: (r['sid'], r['t']))
    for i, r in enumerate(rows):
        r['id'] = f'{N}-t{i + 1:03d}'
        cx = int(min(max(r['pred'][0], 200), P.W - 200)); cy = int(min(max(r['pred'][1], 200), P.H - 200))
        r['box'] = [cx - 200, cy - 200, cx + 200, cy + 200]
        S.render_crop(N, r['box'], CROPS + f't/{r["id"]}.jpg', [r['pred']])
    json.dump(rows, open(OUT + 'trace.json', 'w', encoding='utf8', newline='\n'), indent=1)
    print(N, 'stations', len(rows), 'on', len({r['sid'] for r in rows}), 'streets')
elif PHASE == 'ends':
    M = json.load(open(OUT + 'merge.json', encoding='utf8'))
    old = json.load(open(OUT + 'ends.json', encoding='utf8')) if os.path.exists(OUT + 'ends.json') else []
    rnd = max([e.get('round', 1) for e in old], default=0) + 1
    log = collections.Counter((e['rid'], e['side']) for e in M.get('ends_read', []))
    stop = {(e['rid'], e['side']) for e in M.get('ends_read', []) if e['result'] != 'runs on'}
    rows = []; os.makedirs(CROPS + 'e', exist_ok=True)
    for run in M['runs']:
        g = BY[run['sid']]['geom']; pts = np.array(run['points'], float)
        for side in ('start', 'end'):
            if not run[side + '_open'] or run[side] or (run['rid'], side) in stop or log[(run['rid'], side)] >= 6: continue
            pt = pts[0] if side == 'start' else pts[-1]
            if len(pts) >= 2: d = (pts[0] - pts[1]) if side == 'start' else (pts[-1] - pts[-2])
            else:
                t0 = run['t'][0]; q0 = g.interpolate(max(0, t0 - 20) if side == 'start' else min(g.length, t0 + 20)); d = P.px(q0.x, q0.y) - pt
            nd = np.linalg.norm(d); d = d / nd if nd > 1 else np.array([1.0, 0.0])
            word = {0: 'right', 1: 'bottom', 2: 'left', 3: 'top'}[int(((np.degrees(np.arctan2(d[1], d[0])) + 45) % 360) // 90)]
            c = pt + d * 220
            cx = int(min(max(c[0], 300), P.W - 300)); cy = int(min(max(c[1], 300), P.H - 300))
            rows.append(dict(id=None, sid=run['sid'], run=run['run'], rid=run['rid'], side=side, name=run['name'], round=rnd,
                             from_px=[round(float(pt[0]), 1), round(float(pt[1]), 1)], toward=word, box=[cx - 300, cy - 300, cx + 300, cy + 300]))
    for i, r in enumerate(rows):
        r['id'] = f'{N}-e{len(old) + i + 1:03d}'
        S.render_crop(N, r['box'], CROPS + f'e/{r["id"]}.jpg', [r['from_px']])
    json.dump(old + rows, open(OUT + 'ends.json', 'w', encoding='utf8', newline='\n'), indent=1)
    print(N, 'round', rnd, 'run ends to read', len(rows))
