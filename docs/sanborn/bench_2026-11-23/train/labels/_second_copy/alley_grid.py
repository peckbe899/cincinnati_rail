# alley detector settings on 1A ONLY: strips found, their share of Ben's block / street, and Ben's lines wrongly negative
import sys, json, itertools, numpy as np, cv2
sys.path.insert(0, 'bench_2026-11-23/train/staged/tools/sanborn/unet')
import make_labels_v2 as M
N = '1A'; I = M.pseudo_inputs(N); MAP = 'bench_2026-11-23/train/labels/out/'
ml = cv2.imread(MAP + N + '/label.png', 0); mt = cv2.imread(MAP + N + '/lines.png', 0); sm = json.load(open(MAP + N + '/streetmap.json', encoding='utf8'))
base = dict(M.ALLEY); rows = []
for cross, passes, tint_share, reach in itertools.product((True, False), (1, 2), (0.15, 0.3), (40.0, 80.0)):
    M.ALLEY = dict(base, cross=cross, passes=passes, tint_share=tint_share, reach_ft=reach)
    al, found = M.alley_strips(I, 100)
    lab, t, e, c = M.pseudo_labels(I, M.PSEUDO, 100, al); r = M.compare_arrays(N, lab, t, ml, mt, sm)
    row = dict(cross=cross, passes=passes, tint_share=tint_share, reach_ft=reach, strips=len(found), px=int(al.sum()), on_map_block=round(float((ml[al] == 1).mean()), 3), on_map_street=round(float((ml[al] == 0).mean()), 3),
               cov=r['area']['coverage_of_decided'], ben_neg=r['lines']['ben_lines']['wrongly_negative'], drawn_neg=r['lines']['ben_drawn']['wrongly_negative'], negcov=r['lines']['neg_coverage_of_map_neg'])
    rows.append(row); print(json.dumps(row), flush=True)
json.dump(rows, open('bench_2026-11-23/train/labels/tune/1A_alley_grid.json', 'w'), indent=0)
