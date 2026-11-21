"""Held-out tuning of the three track-stage changes on plate 44 (rail-rules, 21 Nov 2026). Read-only on the repo; writes
bench_2026-11-21/rail-rules/sweep/. Uses variants/rail_tracks_sweep.py (the proposed tracing plus the rejected railroad join).

Bins: plate 44 run as a plate that was never placed (no street map, no label, no Ben tracks: runs/44_nomap_prop_bins.png,
identical to rail/runs/44_nomap_bins.png and to the orig copy's). Truth: Ben's 28 tracks
(picks22_guided/22-44/rail_ben.page_2026-11-21.json; rail_ben.json still holds 26).
Folds: bench44's A and B (fold_score.py). Every setting is scored on both folds; a setting is CHOSEN on one fold and then
READ on the other. The rule for choosing was fixed before the sweep ran:
  railroad stages  highest F1 by length at 10 px; ties (within 0.0005) -> fewer of Ben's tracks broken in their
                   interior -> fewer false tracks -> the setting nearest the batch (earliest in the grid)
  streetcar stage  highest F1 by length at 30 px; ties -> fewer broken + gaps -> nearest the batch
Stages, in order (S2 uses S1's choice on the same fold; S3 is independent of the railroad):
  S1 rr_join      0 (batch), 10, 20, 30, 45, 60, 90 px (ends facing within 25 degrees)
  S2 rr_alone     off (batch), short 300/450/600/900/1200 px x near 30/60/100/150 px, as 'single' (proposed drop_alone)
                  or 'group' (a group of tracks linked within `near` dropped whole when its total is under `short`)
  S3 car_reach    150 (batch), 200, 250, 300, 350, 400, 500, 600 px
Plate 1A (10 checked streetcar tracks; no railroad drawn; begun, not complete) is scored for every setting as an outside
check, never used for choosing. Streetcar is also scored against the rail agent's scratch truth with Ben's 5 gaps under
street names bridged (rail/exp/44_truth_bridged.json), never used for choosing.
    cd data/sanborn
    python bench_2026-11-21/rail-rules/sweep44.py"""
import sys, os, json, time, importlib.util
from multiprocessing import Pool
import numpy as np, cv2
from scipy.spatial import cKDTree
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from fold_score import fscore
spec = importlib.util.spec_from_file_location('rt_prop', os.path.join(HERE, 'variants', 'rail_tracks_sweep.py')); rt = importlib.util.module_from_spec(spec); spec.loader.exec_module(rt)
OUT = os.path.join(HERE, 'sweep')
T44 = json.load(open('picks22_guided/22-44/rail_ben.page_2026-11-21.json', encoding='utf8'))
TBR = json.load(open('bench_2026-11-21/rail/exp/44_truth_bridged.json', encoding='utf8'))
T1A = json.load(open('picks22_guided/22-1A/rail_ben.json', encoding='utf8'))
H44, W44, H1A, W1A = 7219, 10768, 4224, 5761
JOINS = [0, 10, 20, 30, 45, 60, 90]; REACH = [150, 200, 250, 300, 350, 400, 500, 600]
ALONE = [None] + [(m, s, n) for m in ('single', 'group') for s in (300, 450, 600, 900, 1200) for n in (30, 60, 100, 150)]
STATS = ('recall', 'precision', 'f1', 'false_len', 'found', 'partial', 'missed', 'broken_interior', 'gaps', 'false_tracks', 'false_tracks_len', 'n_rule', 'n_ben')


def J(P, kind): return [dict(kind=kind, src='rule', pts=np.asarray(p).tolist()) for p in P]


def drop_group(P, short, near):
    """tracks linked when any of their points lie within `near` px; a group whose total length is under `short` is dropped"""
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
    for i, p in enumerate(P): tot[f(i)] = tot.get(f(i), 0) + rt.plen(p)
    return [p for i, p in enumerate(P) if tot[f(i)] >= short]


def apply_alone(P, a):
    if a is None: return P
    m, s, n = a; return rt.drop_alone(P, s, n) if m == 'single' else drop_group(P, s, n)


def pick(o, kind, regs):
    return {reg: {f'tol{t}': {x: o[reg][kind][f'tol{t}'][x] for x in STATS} for t in (10, 30)} for reg in regs}


def job(args):
    """one setting of one kind -> its scores (44 folds, 1A, and for streetcar 44 against the bridged truth)"""
    kind, key, P44, P1A = args
    tr44 = J(P44, kind); tr1A = J(P1A, kind)
    r = dict(kind=kind, key=key, n44=len(tr44), n1A=len(tr1A), len44=round(sum(rt.plen(t['pts']) for t in tr44)))
    r['44'] = pick(fscore('44', tr44, T44, H44, W44)[0], kind, ('all', 'A', 'B'))
    r['1A'] = pick(fscore('1A', tr1A, T1A, H1A, W1A, ('all',))[0], kind, ('all',))
    if kind == 'streetcar': r['44br'] = pick(fscore('44', tr44, TBR, H44, W44, ('all', 'A', 'B'))[0], kind, ('all', 'A', 'B'))
    return r


def rr_key(r, reg):
    s = r['44'][reg]['tol10']; return (round((s['f1'] or 0) / 0.0005), -s['broken_interior'], -s['false_tracks'])


def car_key(r, reg):
    s = r['44'][reg]['tol30']; return (round((s['f1'] or 0) / 0.0005), -(s['broken_interior'] + s['gaps']))


def choose(results, keyf, reg):
    best = None
    for r in results:   # grid order = nearest the batch first: a tie keeps the earlier
        k = keyf(r, reg)
        if best is None or k > best[0]: best = (k, r)
    return best[1]


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True); t0 = time.time()
    B = {'44': cv2.imread(os.path.join(HERE, 'runs/44_nomap_prop_bins.png'), 0), '1A': cv2.imread(os.path.join(HERE, 'runs/1A_prop_bins.png'), 0)}
    RR = {(N, j): rt.railroad_tracks((B[N] == 4).astype(np.uint8), join=j) for N in B for j in JOINS}
    CAR = {(N, r): rt.streetcar_tracks((B[N] == 5).astype(np.uint8), reach=r) for N in B for r in REACH}
    print(f'traced in {time.time() - t0:.0f} s', flush=True)
    with Pool(6) as pool:
        S1 = pool.map(job, [('railroad', dict(rr_join=j), RR['44', j], RR['1A', j]) for j in JOINS])
        S3 = pool.map(job, [('streetcar', dict(car_reach=r), CAR['44', r], CAR['1A', r]) for r in REACH])
        jch = {reg: choose(S1, rr_key, reg)['key']['rr_join'] for reg in ('A', 'B')}
        S2 = {}
        for j in sorted(set(jch.values())):
            S2[j] = pool.map(job, [('railroad', dict(rr_join=j, rr_alone=a), apply_alone(RR['44', j], a), apply_alone(RR['1A', j], a)) for a in ALONE])
    print(f'scored in {time.time() - t0:.0f} s', flush=True)
    choice = {}
    for reg in ('A', 'B'):
        a = choose(S2[jch[reg]], rr_key, reg)['key']['rr_alone']; r = choose(S3, car_key, reg)['key']['car_reach']
        choice[reg] = dict(rr_join=jch[reg], rr_alone=a, car_reach=r)
    json.dump(dict(choice=choice, S1=S1, S2={str(k): v for k, v in S2.items()}, S3=S3), open(os.path.join(OUT, 'sweep44.json'), 'w'), indent=1)
    print('CHOICE', json.dumps(choice))

    def line(r, kind):
        s = r['44']; t = 'tol10' if kind == 'railroad' else 'tol30'; o = f"{str(r['key']):60s} n{r['n44']:3d} {r['len44']:6d}px"
        for reg in ('all', 'A', 'B'):
            x = s[reg][t]; o += f" | {reg} R{100 * x['recall']:5.1f} P{100 * (x['precision'] or 0):5.1f} F{100 * (x['f1'] or 0):5.1f} br{x['broken_interior']} g{x['gaps']} ft{x['false_tracks']}"
        y = r['1A']['all'][t]; o += f" || 1A R{100 * (y['recall'] or 0):5.1f} P{100 * (y['precision'] or 0):5.1f} n{r['n1A']} br{y['broken_interior']} g{y['gaps']}"
        if '44br' in r: z = r['44br']['all'][t]; o += f" || 44br R{100 * z['recall']:5.1f} P{100 * z['precision']:5.1f}"
        return o
    with open(os.path.join(OUT, 'sweep44.txt'), 'w') as f:
        for name, L, kind in [('S1 rr_join', S1, 'railroad')] + [(f'S2 rr_alone (join {j})', v, 'railroad') for j, v in S2.items()] + [('S3 car_reach', S3, 'streetcar')]:
            f.write(f'== {name} (railroad at 10 px, streetcar at 30 px)\n'); [f.write(line(r, kind) + '\n') for r in L]
        f.write('CHOICE ' + json.dumps(choice) + '\n')
    print(open(os.path.join(OUT, 'sweep44.txt')).read()); print(f'done in {time.time() - t0:.0f} s')
