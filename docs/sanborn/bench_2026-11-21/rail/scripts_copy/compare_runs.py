"""Compare a variant run of the rail rules with the batch's run on one plate (bench_2026-11-21/rail). Read-only on the repo.
    cd data/sanborn
    python bench_2026-11-21/rail/compare_runs.py N BASE_rail_rule.json VARIANT_rail_rule.json [--f1]
Prints railroad tracks / px, base length the variant drops and variant length it adds (farther than 10 px from the other),
census hook candidates removed, and on 44 the score against Ben's 28 tracks. --f1 also applies the lone-short filter."""
import sys, json
sys.path.insert(0, 'bench_2026-11-21/rail')
import numpy as np, cv2
import rail_tracks_copy as rt
from rail_variants import drop_lone_short
from score_rail_bench import score, samples, seglen_weights, draw, dist, clip
N, bp, vp = sys.argv[1:4]
H, W = cv2.imread(f'cufp/22-{N}.jpg', 0).shape
T = {'base': json.load(open(bp))['tracks'], 'variant': json.load(open(vp))['tracks']}
if '--f1' in sys.argv: T['variant+F1'] = drop_lone_short(T['variant'], 600, 60)[0]
hooks = [h for h in json.load(open('bench_2026-11-21/rail/census/hook_candidates.json')) if h['plate'] == N]
rrlen = lambda tr: sum(rt.plen(t['pts']) for t in tr if t['kind'] == 'railroad')
Dv = {v: dist(draw([t['pts'] for t in tr if t['kind'] == 'railroad'], H, W)) for v, tr in T.items()}
def far(tr, D):
    s = 0.0
    for t in tr:
        if t['kind'] != 'railroad': continue
        S = samples(t['pts']); w = seglen_weights(S); q = clip(S, H, W); s += float((w * (D[q[:, 1], q[:, 0]] > 10)).sum())
    return round(s)
out = {}
for v, tr in T.items():
    o = dict(n=sum(t['kind'] == 'railroad' for t in tr), px=round(rrlen(tr)))
    if v != 'base':
        o['base_dropped'] = far(T['base'], Dv[v]); o['added'] = far(tr, Dv['base'])
        o['hooks_removed'] = int(sum((Dv[v][clip(samples([h['a'], h['b']]), H, W)[:, 1], clip(samples([h['a'], h['b']]), H, W)[:, 0]] > 10).mean() > 0.5 for h in hooks)); o['hook_candidates'] = len(hooks)
    if N == '44':
        TJ = json.load(open('picks22_guided/22-44/rail_ben.page_2026-11-21.json', encoding='utf8')); s = score('44', tr, TJ, H, W)['kinds']['railroad']
        o.update(R10=s['tol10']['recall'], P10=s['tol10']['precision'], R30=s['tol30']['recall'], P30=s['tol30']['precision'], false_tracks=s['tol30']['false_tracks'])
    out[v] = o
print(N, json.dumps(out))
