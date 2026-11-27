"""Dev analysis (fix_block_a): for each block-number target of the dev block truth, which code a mask gives its text px.
    cd data/sanborn; python -B bench_2026-11-26/text_fix/fix_block_a/code/dev_codes.py MASK_PATTERN FOLD
Dev only: reads truth. Not used at run time."""
import json, os, sys
import numpy as np, cv2
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from folds import fold_of
TR = 'bench_2026-11-26/text_fix/dev_block/truth'


def main():
    pat, fold = sys.argv[1], sys.argv[2]
    crops = json.load(open(os.path.join(TR, 'crops.json')))
    tot = np.zeros(6, int)
    for cid, c in sorted(crops.items()):
        if fold != 'all' and fold_of(c['plate']) != fold: continue
        x0, y0, x1, y1 = c['win']; m = cv2.imread(pat.replace('{plate}', c['plate']), cv2.IMREAD_UNCHANGED)[y0:y1, x0:x1]
        tr = cv2.imread(os.path.join(TR, f'{cid}_mask.png'), 0)
        W = json.load(open(os.path.join(TR, f'{cid}_words.json'), encoding='utf8'))['words']
        for w in W:
            if not w.get('target'): continue
            pm = np.zeros(tr.shape, np.uint8); cv2.fillPoly(pm, [np.round(np.array(w['poly']) - [x0, y0]).astype(np.int32)], 1)
            sel = (pm > 0) & (tr == 2); h = np.bincount(m[sel], minlength=6)[:6]; tot += h
            print(f"{cid} {c['plate']:>4s} {c['scale_ft_per_inch']} {w['reading']:>4s} n={sel.sum():5d} rec={(h[2]+h[3])/max(1,sel.sum()):.2f} codes0-5={h.tolist()}")
    print('total', tot.tolist(), 'recall', round((tot[2] + tot[3]) / tot.sum(), 4))


if __name__ == '__main__':
    main()
