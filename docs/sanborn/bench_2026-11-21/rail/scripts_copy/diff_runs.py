"""Stretches of railroad in run A's tracks that lie more than TOL px from every railroad track of run B (bench_2026-11-21/rail).
Read-only. Writes OUT.json in the montage list format.
    python bench_2026-11-21/rail/diff_runs.py N A.json B.json OUT.json [TOL] [MINLEN]"""
import sys, json, numpy as np, cv2
sys.path.insert(0, 'bench_2026-11-21/rail')
from score_rail_bench import samples, seglen_weights, draw, dist, clip
N, ap, bp, op = sys.argv[1:5]; tol = float(sys.argv[5]) if len(sys.argv) > 5 else 10; mn = float(sys.argv[6]) if len(sys.argv) > 6 else 40
H, W = cv2.imread(f'cufp/22-{N}.jpg', 0).shape
A = json.load(open(ap))['tracks']; B = json.load(open(bp))['tracks']
D = dist(draw([t['pts'] for t in B if t['kind'] == 'railroad'], H, W)); out = []
for t in A:
    if t['kind'] != 'railroad': continue
    S = samples(t['pts']); w = seglen_weights(S); q = clip(S, H, W); bad = D[q[:, 1], q[:, 0]] > tol; run = []; L = 0
    for s, f, ww in list(zip(S, bad, w)) + [(S[-1], False, 0)]:
        if f: run.append(s); L += ww
        else:
            if L >= mn: out.append(dict(plate=N, len=round(L), a=[round(float(v)) for v in run[0]], b=[round(float(v)) for v in run[-1]]))
            run = []; L = 0
json.dump(out, open(op, 'w')); print(N, len(out), 'stretches', sum(o['len'] for o in out), 'px')
