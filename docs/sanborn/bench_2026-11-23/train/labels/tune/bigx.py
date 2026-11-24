# bigx (open land) on 1A (scored against Ben's map) and on non-truth plates (share of pseudo block it removes); 44 is NOT used
import sys, json, numpy as np, cv2
sys.path.insert(0, 'bench_2026-11-23/train/staged/tools/sanborn/unet')
import make_labels_v2 as M
MAP = 'bench_2026-11-23/train/labels/out/1A/'
ml = cv2.imread(MAP + 'label.png', 0); mt = cv2.imread(MAP + 'lines.png', 0); sm = json.load(open(MAP + 'streetmap.json', encoding='utf8')); out = []
for N in ('1A', '60B', '30'):
    I = M.pseudo_inputs(N); ft = M.scale_ft(N) or 100; al, _ = M.alley_strips(I, ft); base = None
    for bx in (0, 2, 3, 5, 10):
        lab, t, e, c = M.pseudo_labels(I, dict(M.PSEUDO, bigx=bx), ft, al)
        row = dict(plate=N, bigx=bx, block_px=c['block'], line_neg=c['line_neg'])
        if N == '1A':
            r = M.compare_arrays(N, lab, t, ml, mt, sm); row.update(blkP=r['area']['block_precision'], cov=r['area']['coverage_of_decided'], undecided=r['area']['taught_where_map_undecided'], ben_neg=r['lines']['ben_lines']['wrongly_negative'])
        out.append(row); print(json.dumps(row), flush=True)
json.dump(out, open('bench_2026-11-23/train/labels/tune/bigx.json', 'w'), indent=0)
