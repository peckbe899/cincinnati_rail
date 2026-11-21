"""Experiment E1 scoring: the rail rules with blocks from the area network (exp/area/N_area_*) against the same rules
without (exp/area/N_base_*, identical to the batch on unplaced plates). bench_2026-11-21/rail; read-only on the repo.
    cd data/sanborn
    python bench_2026-11-21/rail/exp_area_score.py N [N ...]
44: scored against Ben's 28 tracks. Others: railroad length the area run drops or adds (base length farther than 10 px
from every area-run track), split into the census 'hook candidates' (visually checked false on 5, 11, 14) and the rest;
also with the lone-short filter F1 on top."""
import sys, json
sys.path.insert(0, 'bench_2026-11-21/rail')
import numpy as np, cv2
import rail_tracks_copy as rt
from rail_variants import drop_lone_short
from score_rail_bench import score, samples, seglen_weights, draw, dist, clip
D = 'bench_2026-11-21/rail/exp/area'
hooks = json.load(open('bench_2026-11-21/rail/census/hook_candidates.json'))
res = {}
for N in sys.argv[1:]:
    H, W = cv2.imread(f'cufp/22-{N}.jpg', 0).shape
    import os
    T = {v: json.load(open(f'{D}/{N}_{v}_rail_rule.json', encoding='utf8'))['tracks'] for v in ('base', 'area', 'area80') if os.path.exists(f'{D}/{N}_{v}_rail_rule.json')}
    T['area+F1'] = drop_lone_short(T['area'], 600, 60)[0]; T['base+F1'] = drop_lone_short(T['base'], 600, 60)[0]
    if 'area80' in T: T['area80+F1'] = drop_lone_short(T['area80'], 600, 60)[0]
    r = res[N] = {}
    for v, tr in T.items():
        rr = [t for t in tr if t['kind'] == 'railroad']; r[v] = dict(n=len(rr), px=round(sum(rt.plen(t['pts']) for t in rr)))
    if N == '44':
        TJ = json.load(open('picks22_guided/22-44/rail_ben.page_2026-11-21.json', encoding='utf8'))
        for v, tr in T.items():
            o = score('44', tr, TJ, H, W)['kinds']['railroad']; r[v].update(R10=o['tol10']['recall'], P10=o['tol10']['precision'], R30=o['tol30']['recall'], P30=o['tol30']['precision'], false_tracks=o['tol30']['false_tracks'])
    else:
        Dv = {v: dist(draw([t['pts'] for t in tr if t['kind'] == 'railroad'], H, W)) for v, tr in T.items()}
        for v in [k for k in T if k != 'base']:
            lost = 0.0
            for t in T['base']:
                if t['kind'] != 'railroad': continue
                S = samples(t['pts']); w = seglen_weights(S); q = clip(S, H, W); lost += float((w * (Dv[v][q[:, 1], q[:, 0]] > 10)).sum())
            r[v]['base_len_dropped'] = round(lost)
        hk = [h for h in hooks if h['plate'] == N]; gone = {}
        for v in [k for k in T if k != 'base']:
            g = 0
            for h in hk:
                S = samples([h['a'], h['b']]); q = clip(S, H, W); g += (Dv[v][q[:, 1], q[:, 0]] > 10).mean() > 0.5
            gone[v] = int(g)
        r['hook_candidates'] = len(hk); r['hooks_removed'] = gone
    print(N, json.dumps(r))
json.dump(res, open(f'{D}/area_scores_{"_".join(sys.argv[1:])}.json', 'w'), indent=1)
