"""Dev harness (fix_block_a): run blockfix on padded windows round dev truth crops and write crop-sized masks.
    cd data/sanborn; python -B .../code/devrun.py TRUTH_DIR FOLD(A|B|all) OUT_DIR [--margin 250] [--set k=v ...] [--crops DB01,..]
Writes OUT_DIR/{crop}_text.png (crop window size) for score_text.py "OUT_DIR/{crop}_text.png" --codes 2,3 --truth TRUTH_DIR.
The truth is read only for the crop list and windows (and to print the block recall); blockfix itself never sees it."""
import json, os, sys, time
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import blockfix
from folds import fold_of
BASE = os.path.join(HERE, '..', 'base')


def main():
    a = sys.argv; td, fold, od = a[1], a[2], a[3]
    margin = int(a[a.index('--margin') + 1]) if '--margin' in a else 250
    opts = {}
    for i, v in enumerate(a):
        if v == '--set': k, val = a[i + 1].split('=', 1); opts[k] = json.loads(val)
    only = a[a.index('--crops') + 1].split(',') if '--crops' in a else None
    crops = json.load(open(os.path.join(td, 'crops.json')))
    os.makedirs(od, exist_ok=True); cache = {}; infos = {}
    for cid, c in sorted(crops.items()):
        if only and cid not in only: continue
        if not os.path.exists(os.path.join(td, f'{cid}_mask.png')): continue
        if fold != 'all' and fold_of(c['plate']) != fold: continue
        p = c['plate']
        if p not in cache: cache = {p: cv2.imread(os.path.join(BASE, f'{p}_text.png'), cv2.IMREAD_UNCHANGED)}
        full = cache[p]; Hh, Ww = full.shape
        x0, y0, x1, y1 = c['win']; X0, Y0, X1, Y1 = max(0, x0 - margin), max(0, y0 - margin), min(Ww, x1 + margin), min(Hh, y1 + margin)
        out, info = blockfix.apply(p, full[Y0:Y1, X0:X1], None, blockfix.scale_of(p), return_info=True, **opts)
        cut = out[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0]
        cv2.imwrite(os.path.join(od, f'{cid}_text.png'), cut)
        infos[cid] = dict(win=[X0, Y0, X1, Y1], changes=[ch for ch in info['changes']], why=info['why'])
    with open(os.path.join(od, 'devrun.json'), 'w', encoding='utf8', newline='\n') as f: json.dump(dict(opts=opts, margin=margin, crops=infos), f, indent=1)


if __name__ == '__main__':
    main()
