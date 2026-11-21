"""Batch-wide effect of the proposed rail changes (rail-rules, 21 Nov 2026). Read-only on the repo; writes rail-rules/batch/.

For every batch plate except 44 and 1A (their batch rail files mix in Ben's tracks):
  batch     unet_data/N_rail_rule.json as the batch wrote it
  orig      orig/rail_tracks.py on the batch's bins (unet_data/N_bins.png): must equal 'batch' (reproduction check)
  key       orig tracing on the proposed bins (batch/N_bins.png from batch_bins.py where the KEY was found, else the
            batch's bins): the KEY change alone
  railroad filters on top of 'key' (each recorded with the tracks it drops, for checking by eye):
            s300_30  single, 300 px / 30 px  (the setting the plate-44 folds chose by their tie-break)
            s600_60  single, 600 px / 60 px  (the rail agent's F1)
            g600_60  group: tracks linked within 60 px, a group under 600 px in all dropped (= proposed drop_alone)
  streetcar reach on top of 'key': 300, 350 (fold B's choice), 500 (fold A's choice); the length each adds over the
            batch's streetcar (points more than 15 px from every batch streetcar track, every 3 px) is recorded
  full      proposed/rail_tracks.py tracks() on the proposed bins, with its TRACKS as they stand (written out)
    cd data/sanborn
    python bench_2026-11-21/rail-rules/batch_tracks.py [-j 4] [N ...]
Writes batch/tracks_compare.json and batch/tracks/N_rail_rule.json (the 'full' tracks)."""
import sys, os, json, re, time, importlib.util
from multiprocessing import Pool
import numpy as np, cv2
from scipy.spatial import cKDTree
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'batch'); sys.path.insert(0, HERE)


def load(which):
    spec = importlib.util.spec_from_file_location(f'rt_{which}', os.path.join(HERE, which, 'rail_tracks.py')); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


RO = load('orig'); RP = load('proposed')
FILTERS = {'s300_30': ('single', 300, 30), 's600_60': ('single', 600, 60), 'g600_60': ('group', 600, 60)}
REACHES = (300, 350, 500)


def drop_group(P, short, near):   # = sweep44.drop_group
    if not P: return P
    S = [np.vstack([p[:1]] + [a[None] + np.linspace(0, 1, max(2, int(np.hypot(*(b - a)) / 5) + 1))[1:, None] * (b - a)[None] for a, b in zip(p[:-1], p[1:])]) for p in P]
    who = np.concatenate([np.full(len(s), i) for i, s in enumerate(S)]); T = cKDTree(np.vstack(S)); par = list(range(len(P)))
    def f(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    for i, s in enumerate(S):
        nb = set()
        for js in T.query_ball_point(s, near): nb.update(who[js].tolist())
        for j in nb:
            if j != i: par[f(i)] = f(j)
    tot = {}
    for i, p in enumerate(P): tot[f(i)] = tot.get(f(i), 0) + RO.plen(p)
    return [p for i, p in enumerate(P) if tot[f(i)] >= short]


def drop_single(P, short, near):   # the single-track form (rail agent's F1; proposed/rail_tracks.py's first draft)
    S = [np.vstack([p[:1]] + [a[None] + np.linspace(0, 1, max(2, int(np.hypot(*(b - a)) / 5) + 1))[1:, None] * (b - a)[None] for a, b in zip(p[:-1], p[1:])]) for p in P]
    if len(P) < 2: return [p for p in P if RO.plen(p) >= short]
    who = np.concatenate([np.full(len(s), i) for i, s in enumerate(S)]); T = cKDTree(np.vstack(S)); keep = []
    for i, p in enumerate(P):
        if RO.plen(p) >= short or any((who[js] != i).any() for js in T.query_ball_point(S[i], near) if js): keep.append(p)
    return keep


def J(P, kind): return [dict(kind=kind, src='rule', pts=[[round(float(x), 1), round(float(y), 1)] for x, y in p]) for p in P]


def dense(p, step=3.0):
    p = np.asarray(p, float); S = [p[:1]]
    for a, b in zip(p[:-1], p[1:]):
        n = max(2, int(np.hypot(*(b - a)) / step) + 1); S.append(a[None] + np.linspace(0, 1, n)[1:, None] * (b - a)[None])
    return np.vstack(S)


def far_points(new, ref, d):
    if not new: return []
    R = cKDTree(np.vstack([dense(p) for p in ref])) if ref else None; out = []
    for i, p in enumerate(new):
        S = dense(p); f = np.ones(len(S), bool) if R is None else R.query(S, distance_upper_bound=d)[0] > d
        out += [(i, float(x), float(y)) for x, y in S[f]]
    return out


def stats(tr):
    o = {}
    for k in ('railroad', 'streetcar'):
        L = [RO.plen(t['pts']) for t in tr if t['kind'] == k]; o[k] = dict(n=len(L), px=round(sum(L)))
    return o


def one(N):
    t0 = time.time()
    batch = json.load(open(f'unet_data/{N}_rail_rule.json', encoding='utf8'))['tracks']
    Bb = cv2.imread(f'unet_data/{N}_bins.png', 0); kp = os.path.join(OUT, f'{N}_bins.png'); keyrun = os.path.exists(kp); Bp = cv2.imread(kp, 0) if keyrun else Bb
    rr0b = RO.railroad_tracks((Bb == 4).astype(np.uint8)); sc0b = RO.streetcar_tracks((Bb == 5).astype(np.uint8))
    orig = J(rr0b, 'railroad') + J(sc0b, 'streetcar')
    if keyrun: rr0 = RO.railroad_tracks((Bp == 4).astype(np.uint8)); sc0 = RO.streetcar_tracks((Bp == 5).astype(np.uint8))
    else: rr0, sc0 = rr0b, sc0b
    key = J(rr0, 'railroad') + J(sc0, 'streetcar')
    r = dict(plate=N, key_run=keyrun, orig_equals_batch=(orig == batch), batch=stats(batch), key=stats(key))
    if keyrun:
        kx0, ky0, kx1, ky1 = [int(v) for v in re.search(r'the printed KEY at \((\d+), (\d+), (\d+), (\d+)\)', open(os.path.join(OUT, f'{N}.log')).read()).groups()]
        r['key_box'] = [kx0, ky0, kx1, ky1]
        inside = lambda t: ((np.asarray(t['pts'])[:, 0] >= kx0) & (np.asarray(t['pts'])[:, 0] < kx1) & (np.asarray(t['pts'])[:, 1] >= ky0) & (np.asarray(t['pts'])[:, 1] < ky1)).mean() > 0.5
        r['batch_tracks_in_key'] = [dict(kind=t['kind'], len=round(RO.plen(t['pts']))) for t in batch if inside(t)]
        r['key_tracks_in_key'] = [dict(kind=t['kind'], len=round(RO.plen(t['pts']))) for t in key if inside(t)]
    r['filters'] = {}
    for name, (mode, s, n) in FILTERS.items():
        kept = drop_single(rr0, s, n) if mode == 'single' else drop_group(rr0, s, n); ks = {id(p) for p in kept}
        if mode == 'group': assert [id(p) for p in kept] == [id(p) for p in RP.drop_alone(rr0, s, n)], N   # the proposed drop_alone is this group form
        r['filters'][name] = dict(n=len(kept), px=round(sum(RO.plen(p) for p in kept)),
                                  dropped=[dict(plate=N, len=round(RO.plen(p)), a=[round(float(v)) for v in p[0]], b=[round(float(v)) for v in p[-1]]) for p in rr0 if id(p) not in ks])
    scb = [np.asarray(t['pts']) for t in batch if t['kind'] == 'streetcar']; r['reach'] = {}
    for R in REACHES:
        car = RP.streetcar_tracks((Bp == 5).astype(np.uint8), reach=R); ap = far_points(car, scb, 15.0)
        r['reach'][str(R)] = dict(n=len(car), px=round(sum(RO.plen(p) for p in car)), added_px=3 * len(ap), added_pts=[(round(x), round(y)) for _, x, y in ap[::5]])
    full = RP.tracks(Bp); r['full'] = stats(full); r['full_settings'] = dict(RP.TRACKS)
    os.makedirs(os.path.join(OUT, 'tracks'), exist_ok=True)
    json.dump(dict(plate=N, settings=RP.TRACKS, note='rail-rules proposed tracks on the proposed bins; not ground truth', tracks=full), open(os.path.join(OUT, 'tracks', f'{N}_rail_rule.json'), 'w'), separators=(',', ':'))
    r['secs'] = round(time.time() - t0)
    print(N, json.dumps(dict(eq=r['orig_equals_batch'], batch=r['batch'], key=r['key'], filt={k: (v['n'], len(v['dropped'])) for k, v in r['filters'].items()}, reach={k: (v['n'], v['added_px']) for k, v in r['reach'].items()}, full=r['full'], secs=r['secs'])), flush=True)
    return r


if __name__ == '__main__':
    a = sys.argv[1:]; jobs = int(a[a.index('-j') + 1]) if '-j' in a else 4
    skip = {a[i + 1] for i, x in enumerate(a) if x == '-j'}
    order = lambda n: (int(re.match(r'\d+', n).group()), n)
    plates = [x for x in a if not x.startswith('-') and x not in skip] or [n for n in sorted(json.load(open('unet_data/run_plates.json', encoding='utf8')), key=order) if n not in ('44', '1A')]
    print('full settings', RP.TRACKS, 'plates', len(plates), flush=True)
    with Pool(jobs) as pool: R = pool.map(one, plates, chunksize=1)
    json.dump(dict(full_settings=RP.TRACKS, filters=FILTERS, reaches=REACHES, plates=R), open(os.path.join(OUT, 'tracks_compare.json'), 'w'), indent=1)
    print('orig == batch on', sum(r['orig_equals_batch'] for r in R), 'of', len(R))
