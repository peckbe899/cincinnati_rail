"""List the stretches of Ben's tracks that the rule tracks miss (bench_2026-11-21/rail). Read-only.
    cd data/sanborn
    python bench_2026-11-21/rail/missed_runs.py N RULE_TRACKS.json TRUTH.json [TOL] [MINLEN]"""
import sys, json, numpy as np, cv2
sys.path.insert(0, 'bench_2026-11-21/rail')
from score_rail_bench import samples, seglen_weights, draw, dist, clip
N, rp, tp = sys.argv[1:4]; tol = float(sys.argv[4]) if len(sys.argv) > 4 else 10; mn = float(sys.argv[5]) if len(sys.argv) > 5 else 40
H, W = cv2.imread(f'cufp/22-{N}.jpg', 0).shape
rule = json.load(open(rp, encoding='utf8'))['tracks']; T = json.load(open(tp, encoding='utf8'))['tracks']
for k in ('railroad', 'streetcar'):
    D = dist(draw([t['pts'] for t in rule if t['kind'] == k], H, W))
    for i, t in enumerate(T):
        if t['kind'] != k or t.get('src') == 'rule': continue
        S = samples(t['pts']); w = seglen_weights(S); q = clip(S, H, W); ok = D[q[:, 1], q[:, 0]] <= tol
        run = []; L = 0
        for s, f, ww in list(zip(S, ok, w)) + [(S[-1], True, 0)]:
            if not f: run.append(s); L += ww
            else:
                if L >= mn: a, b = run[0], run[-1]; print(f'{k:9s} track {i:2d}: missed {L:5.0f} px from ({a[0]:.0f},{a[1]:.0f}) to ({b[0]:.0f},{b[1]:.0f})')
                run = []; L = 0
