"""Dev: like dev_codes.py but for crop-sized masks ({crop} pattern)."""
import json, os, sys
import numpy as np, cv2
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from folds import fold_of
TR = sys.argv[3] if len(sys.argv) > 3 else 'bench_2026-11-26/text_fix/dev_block/truth'
pat, fold = sys.argv[1], sys.argv[2]
crops = json.load(open(os.path.join(TR, 'crops.json'))); tot = np.zeros(6, int); wf = 0; nw = 0
for cid, c in sorted(crops.items()):
    if fold != 'all' and fold_of(c['plate']) != fold: continue
    x0, y0, x1, y1 = c['win']
    p = pat.replace('{crop}', cid).replace('{plate}', c['plate'])
    m = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if m.shape != (y1 - y0, x1 - x0): m = m[y0:y1, x0:x1]
    tr = cv2.imread(os.path.join(TR, f'{cid}_mask.png'), 0)
    for w in json.load(open(os.path.join(TR, f'{cid}_words.json'), encoding='utf8'))['words']:
        if not w.get('target'): continue
        pm = np.zeros(tr.shape, np.uint8); cv2.fillPoly(pm, [np.round(np.array(w['poly']) - [x0, y0]).astype(np.int32)], 1)
        sel = (pm > 0) & (tr == 2); h = np.bincount(m[sel], minlength=6)[:6]; tot += h; r = (h[2] + h[3]) / max(1, sel.sum()); wf += r >= 0.5; nw += 1
        nt = ((pm > 0) & (tr == 1) & np.isin(m, (2, 3))).sum()
        print(f"{cid} {c['plate']:>4s} {c['scale_ft_per_inch']} {w['reading']:>4s} n={sel.sum():5d} rec={r:.2f} codes0-5={h.tolist()} nontext_in_box_called_text={nt}")
print('total', tot.tolist(), 'recall', round((tot[2] + tot[3]) / tot.sum(), 4), f'words {wf}/{nw}')
