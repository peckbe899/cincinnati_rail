"""Stage registration, step 1: candidate controls for every sheet (written to <work>/controls/<sid>.json).

Sources: 'new' = today's OSM named-street intersections located on the scan by corridor fitting (controls.py);
'picks12' = the Topography workspace's named 1912 intersections (read off the start-model mosaic, so their scan pixel
is exact under the start model), paired with today's OSM intersection of the same two street names within 60 m.
"""
import json, os, pickle, sys, time, zipfile
from multiprocessing import Pool
from pathlib import Path
import numpy as np, cv2

from common import load_paths, load_all, frame_px, norm_name
from controls import osm_network, SheetMatcher

MIN_INSIDE = 0.70
MIN_CURV = 0.08


def _net(P):
    f = Path(P['work']) / 'osm_net.pkl'
    if not f.exists():
        pickle.dump(osm_network(P['osm_streets']), open(f, 'wb'))
    return pickle.load(open(f, 'rb'))


def run_sheet(args):
    paths, sid = args
    P = load_paths(paths); ids, _ = load_all(P); d = ids[sid]
    out = Path(P['work']) / 'controls' / f'{sid}.json'
    if out.exists():
        return sid, 'kept'
    t0 = time.time()
    lines, inter = _net(P)
    img = cv2.imread(str(Path(P['sheets']) / d['file']))
    fr = frame_px(d)
    M = SheetMatcher(img, d['start'], fr); del img
    E, N = d['start'].p2utm(np.array([c[0] for c in fr], float), np.array([c[1] for c in fr], float))
    mids = np.array([l[0].mean(0) for l in lines]); ext = np.array([np.ptp(l[0], 0).max() for l in lines])
    res = []
    for e, n, nm in inter:
        if not (E.min() < e < E.max() and N.min() < n < N.max()):
            continue
        near = [lines[i] for i in np.nonzero(np.hypot(mids[:, 0] - e, mids[:, 1] - n) < 60 + ext / 2 + 5)[0]]
        r = M.match(e, n, near)
        if r is None:
            continue
        r.update(xy=[e, n], name=' / '.join(nm), source='new')
        r['ok'] = bool(r['inside'] >= MIN_INSIDE and r['curv'] >= MIN_CURV)
        res.append(r)
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(dict(sheet=sid, file=d['file'], mpp_half=M.mpp, candidates=res), open(out, 'w'))
    return sid, f'{time.time() - t0:.0f}s candidates {len(res)} ok {sum(r["ok"] for r in res)}'


def picks12(P, ids):
    """picks12 intersections -> controls on the sheet whose frame holds them, paired with OSM by names."""
    lines, inter = _net(P)
    osm = {}
    for e, n, nm in inter:
        for a in nm:
            for b in nm:
                if a < b:
                    osm.setdefault((norm_name(a), norm_name(b)), []).append((e, n, f'{a} / {b}'))
    out = {}
    with zipfile.ZipFile(P['picks12']) as z:
        for f in sorted(x for x in z.namelist() if x.startswith('sbg/picks12/') and x.endswith('.json')):
            for p in json.loads(z.read(f))['intersections']:
                key = tuple(sorted((norm_name(p['a']), norm_name(p['b']))))
                cands = [c for c in osm.get(key, []) if np.hypot(c[0] - p['E'], c[1] - p['N']) < 60]
                if not cands:
                    continue
                e, n, nm = min(cands, key=lambda c: np.hypot(c[0] - p['E'], c[1] - p['N']))
                for sid, d in ids.items():
                    u, v = d['start'].utm2p(np.array([p['E']]), np.array([p['N']]))
                    fr = np.array(frame_px(d), float)
                    if cv2.pointPolygonTest(fr.astype(np.float32), (float(u[0]), float(v[0])), True) > 60:
                        out.setdefault(sid, []).append(dict(px=[float(u[0]), float(v[0])], xy=[e, n],
                                                            name=f"{p['a']} / {p['b']}", osm_name=nm, source='picks12',
                                                            area=f.split('/')[-1][:-5], ok=True))
                        break
    return out


if __name__ == '__main__':
    paths = sys.argv[1] if len(sys.argv) > 1 else 'configs/ground_paths.json'
    P = load_paths(paths); ids, _ = load_all(P); _net(P)
    with Pool(int(os.environ.get('NPROC', 6))) as pool:
        for sid, msg in pool.imap_unordered(run_sheet, [(paths, s) for s in sorted(ids)]):
            print(sid, msg, flush=True)
    pk = picks12(P, ids)
    json.dump(pk, open(Path(P['work']) / 'controls' / 'picks12.json', 'w'))
    print('picks12 paired:', {k: len(v) for k, v in pk.items()})
