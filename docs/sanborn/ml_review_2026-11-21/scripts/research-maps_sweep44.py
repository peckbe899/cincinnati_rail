import json, time, numpy as np
import ws44 as W
from pq44 import pq
e1, ng1 = W.area('edge_v1'), W.area('area_ng1'); mn = np.minimum(e1, ng1)
for nm, pa in (('A edge_v1', e1), ('C min', mn)):
    for thr in (127, 180):
        for ss in (4, 8):
            for sb in (14, 24):
                inst, n = W.blocks(pa, W.pl, seed_b=sb, seed_s=ss, thr=thr); r = pq(W.gt, W.ng, inst, n, f'{nm} thr{thr} seedS{ss} seedB{sb}')
                print(json.dumps({k: r[k] for k in ('src', 'pred', 'tp', 'fp', 'fn', 'SQ', 'RQ', 'PQ', 'missed_by_merge')}), flush=True)
