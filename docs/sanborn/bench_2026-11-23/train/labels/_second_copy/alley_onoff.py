# 1A only: the final thresholds with and without the alley strips, and with the crossing test off
import sys, json, numpy as np, cv2
sys.path.insert(0, 'bench_2026-11-23/train/staged/tools/sanborn/unet')
import make_labels_v2 as M
th = dict(M.PSEUDO, **json.loads(sys.argv[1])); I = M.pseudo_inputs('1A'); MAP = 'bench_2026-11-23/train/labels/out/1A/'
ml = cv2.imread(MAP + 'label.png', 0); mt = cv2.imread(MAP + 'lines.png', 0); sm = json.load(open(MAP + 'streetmap.json', encoding='utf8'))
base = dict(M.ALLEY); out = []
for tag, al_cfg in (('no alley', None), ('alley, crossing test on', dict(base, cross=True)), ('alley, crossing test off', dict(base, cross=False))):
    if al_cfg: M.ALLEY = al_cfg; al, f = M.alley_strips(I, 100)
    else: al, f = None, []
    lab, t, e, c = M.pseudo_labels(I, th, 100, al); r = M.compare_arrays('1A', lab, t, ml, mt, sm)
    row = dict(tag=tag, strips=len(f), cov=r['area']['coverage_of_decided'], blkP=r['area']['block_precision'], stP=r['area']['street_precision'], ben_neg=r['lines']['ben_lines']['wrongly_negative'], drawn_neg=r['lines']['ben_drawn']['wrongly_negative'], negcov=r['lines']['neg_coverage_of_map_neg'])
    out.append(row); print(json.dumps(row))
json.dump(out, open('bench_2026-11-23/train/labels/tune/1A_alley_onoff.json', 'w'), indent=0)
