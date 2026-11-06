try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import sys, time, json
sys.path.insert(0, (_ws.CODE + 'yard'))
from zipkit import *
T_END = 5350.0
def series(breaks, minbody=250.0):
    room = ROOM0; allL = []; info = []
    for t0, t1 in zip(breaks, breaks[1:]):
        lo = min(edges(t)[0] for t in range(int(t0), int(t1), 50)); hi = max(edges(t)[1] for t in range(int(t0), int(t1), 50))
        tr, th = yard(room, lat_range(-round(-lo / SP) * SP, round(hi / SP) * SP), 0.0, t0 + (30 if t0 > 0 else 0), t1 - 30, minbody)
        room = take(room, tr + th); allL += tr + th; info.append(len(tr))
    return fp(allL).area / 1e4, info, allL
def zipper(t_start, P, off, minbody=200.0, reach=1.0, cap=40.0):
    """two lanes, leads on the outside edges; lane W yards every P from t_start, lane E offset by off"""
    room = ROOM0; allL = []; info = []; ALLSP = []
    for lane, sgn, ts in (('W', -1, t_start), ('E', +1, t_start + off)):
        spans = []
        t = ts if ts <= 0 else 0.0
        bnds = [0.0] + [x for x in [ts + k * P for k in range(0, 20)] if 0 < x < T_END] + [T_END]
        bnds = sorted(set(round(v) for v in bnds))
        for t0, t1 in zip(bnds, bnds[1:]):
            if t1 - t0 < 400: continue
            E = [edges(t) for t in range(int(t0), int(t1) + 1, 25)]
            if sgn < 0: lead = max(e[0] for e in E) + 1.0; lead = -math.floor(-lead / SP) * SP; xs = lat_range(lead, cap)
            else: lead = min(e[1] for e in E) - 1.0; lead = math.floor(lead / SP) * SP; xs = lat_range(-cap, lead)
            spans.append((lane, t0, t1, lead, xs))
        ALLSP.extend(spans)
    for lane_, t0, t1, lead, xs in sorted(ALLSP, key=lambda q: (q[1] + q[2]) / 2):
        tr, th = yard(room, xs, lead, float(t0) + (30 if t0 > 0 else 0), float(t1) - 30, minbody)
        room = take(room, tr + th); allL += tr + th; info.append((lane_, t0, t1, lead, len(tr)))
    return fp(allL).area / 1e4, info, allL
if __name__ == '__main__' and sys.argv[1] in ('series', 'zipper'):
    mode = sys.argv[1]
    t = time.time()
    if mode == 'series':
        br = [float(v) for v in sys.argv[2].split(',')]
        a, info, L = series(br); print('series', br, 'ha %.1f' % a, info, '%.0fs' % (time.time() - t))
    else:
        ts, P, off, cap = [float(v) for v in sys.argv[2:6]]
        a, info, L = zipper(ts, P, off, cap=cap); print('zipper', ts, P, off, 'ha %.1f' % a, info, '%.0fs' % (time.time() - t))
    json.dump([list(l.coords) for l in L], open((_ws.DATA + 'yard/zs_%s.json') % '_'.join(sys.argv[1:]).replace(',', '-'), 'w'))
def series2(breaks, minbody=250.0, south_stub=True, sides=True):
    room = ROOM0; allL = []; info = []
    for i, (t0, t1) in enumerate(zip(breaks, breaks[1:])):
        tt0 = t0 + (30 if t0 > 0 else 0); tt1 = t1 - 30
        E = [edges(t) for t in range(int(tt0), int(tt1) + 1, 50)]
        lo = -math.floor(-max(e[0] for e in E) / SP) * SP; hi = math.floor(min(e[1] for e in E) / SP) * SP
        if i == 0 and south_stub:
            lo2 = -math.floor(-max(e[0] for e in E if True) / SP) * SP
            tr, th = stub_south(room, lat_range(lo, hi), 0.0, tt1, minbody)
        else:
            tr, th = yard(room, lat_range(lo, hi), 0.0, tt0, tt1, minbody)
        room = take(room, tr + th); allL += tr + th; info.append(('core', t0, t1, len(tr)))
        if sides and tr:
            lat = {}
            for l in tr:
                ts_ = [F.Lc(*c)[1] for c in (l.coords[0], l.coords[-1])]; x_ = round(F.Lc(*l.interpolate(0.5, normalized=True).coords[0])[0] / SP) * SP
                lat[x_] = (min(ts_), max(ts_))
            lo_, hi_ = min(lat), max(lat)
            sl = []
            for sgn, cx in ((-1, lo_), (1, hi_)):
                a_, b_ = lat[cx]
                room, sl1 = side_yards(room, tr, cx if sgn < 0 else -1e9, cx if sgn > 0 else 1e9, a_ + 60, b_ - 60, minbody=200.0, only=sgn)
                sl += sl1
            allL += sl; info.append(('side', t0, t1, len([1 for l in sl])))
    return fp(allL).area / 1e4, info, allL
if __name__ == '__main__' and sys.argv[1] == 'series2':
    br = [float(v) for v in sys.argv[2].split(',')]
    t = time.time(); a, info, L = series2(br); print('series2', br, 'ha %.1f' % a, info, '%.0fs' % (time.time() - t))
    json.dump([list(l.coords) for l in L], open((_ws.DATA + 'yard/zs_series2_%s.json') % sys.argv[2].replace(',', '-'), 'w'))
