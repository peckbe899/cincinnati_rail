"""Does M1 help the no-guide batch (area_ng1 + lines_ng1) with a wider cut or a lower line threshold? Read-only."""
import json, sys
import numpy as np, cv2
import ws44 as W
from pq44 import pq
from m1_check import ws_inst, per_instance, half, fp_analysis
pl = cv2.imread(sys.argv[1], 0); ng1 = W.area('area_ng1')
for cut, lthr in ((6, 127), (10, 127), (3, 64), (6, 64)):
    ln = pl if lthr == 127 else np.where(pl > lthr, 255, pl).astype(np.uint8)
    ws = ws_inst(ng1, ln, cut=cut); a, k = per_instance(ws); r = pq(W.gt, W.ng, half(a), k, f'area_ng1 + lines_ng1 inst cut{cut} linethr{lthr}'); r.update(fp_analysis(W.gt, W.ng, half(a), k))
    print(json.dumps({x: r[x] for x in ('src', 'pred', 'tp', 'fp', 'fn', 'SQ', 'PQ', 'missed_by_merge', 'fp_fragment_of_matched_block', 'fp_mostly_off_ben_blocks')}), flush=True)
