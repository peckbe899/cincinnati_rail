"""F1b: as F1, but only a railroad track of 600 px or more counts as the 'other track' a short one must lie near
(bench_2026-11-21/rail). Scores 44 (no map) and 1A, counts what it drops on the batch plates. Read-only on the repo."""
import sys, json, re
sys.path.insert(0, 'bench_2026-11-21/rail')
import numpy as np
import rail_tracks_copy as rt
from rail_variants import drop_lone_short
from score_rail_bench import score
for N, rp, tp in (('44', 'bench_2026-11-21/rail/runs/44_nomap_rail_rule.json', 'picks22_guided/22-44/rail_ben.page_2026-11-21.json'), ('1A', 'bench_2026-11-21/rail/runs/1A_rail_rule.json', 'picks22_guided/22-1A/rail_ben.json')):
    T = json.load(open(rp))['tracks']; TJ = json.load(open(tp, encoding='utf8')); H, W = (7219, 10768) if N == '44' else (4224, 5761)
    for name, kw in (('F1', {}), ('F1b anchor 600', dict(anchor=600))):
        keep, drop = drop_lone_short(T, 600, 60, **kw); o = score(N, keep, TJ, H, W)['kinds']['railroad']
        print(N, name, 'dropped', len(drop), 'rr left', sum(t['kind'] == 'railroad' for t in keep), '| 10px R', o['tol10']['recall'], 'P', o['tol10']['precision'], '| false len', o['tol10']['false_len'])
S = json.load(open('unet_data/run_plates.json', encoding='utf8')); n1 = n2 = 0; px1 = px2 = 0; drops = []
for N in S:
    if N in ('44', '1A'): continue
    T = json.load(open(f'unet_data/{N}_rail_rule.json', encoding='utf8'))['tracks']
    a = drop_lone_short(T, 600, 60)[1]; b = drop_lone_short(T, 600, 60, anchor=600)[1]
    n1 += len(a); n2 += len(b); px1 += sum(rt.plen(t['pts']) for t in a); px2 += sum(rt.plen(t['pts']) for t in b)
    ka = {json.dumps(t['pts']) for t in a}
    for t in b:
        if json.dumps(t['pts']) not in ka: p = np.asarray(t['pts']); drops.append(dict(plate=N, len=round(rt.plen(p)), a=[round(v) for v in p[0]], b=[round(v) for v in p[-1]]))
print('batch: F1 drops', n1, round(px1), '| F1b drops', n2, round(px2), '| extra F1b drops', len(drops))
json.dump(drops, open('bench_2026-11-21/rail/exp/f1b_extra_drops.json', 'w'), indent=1)
