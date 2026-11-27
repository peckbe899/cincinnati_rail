"""Two-fold tuning of blockfix (fix_block_a). Each setting of a small grid is run on the dev block crops of both folds
(windows round the crops, as devrun.py), scored with score_text.py's own functions, and the best setting on one fold is
scored on the other.
    cd data/sanborn; python -B .../code/tune.py OUT.json
Objective: pooled in-scope F1 of text px (codes 2, 3) on the fold's block crops. Also kept: block recall (px, words) and
non-text ink called text. Dev only (reads truth)."""
import itertools, json, os, sys, subprocess
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import blockfix
from folds import fold_of
SC = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'bench_2026-11-25', 'text_v1', 'code')); sys.path.insert(0, SC)
import score_text as ST
TD = 'bench_2026-11-26/text_fix/dev_block/truth'
GRID = dict(anchor=[0.25, 0.4], strip_m=[0.5, 1.0], touch_r=[1, 2], free=[True, False])


def run(opts, crops, base):
    res = {}
    for cid, c in crops.items():
        full = base[c['plate']]; Hh, Ww = full.shape; x0, y0, x1, y1 = c['win']; M = 250
        X0, Y0, X1, Y1 = max(0, x0 - M), max(0, y0 - M), min(Ww, x1 + M), min(Hh, y1 + M)
        out, _ = blockfix.apply(c['plate'], full[Y0:Y1, X0:X1], None, blockfix.scale_of(c['plate']), return_info=True, **opts)
        res[cid] = out[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0]
    return res


def score(masks, crops):
    r = {}
    for cid, c in crops.items():
        truth = cv2.imread(os.path.join(TD, f'{cid}_mask.png'), 0); W = json.load(open(os.path.join(TD, f'{cid}_words.json'), encoding='utf8'))['words']
        r[cid] = ST.score_crop(cid, c, truth, masks[cid], lambda m: np.isin(m, (2, 3)), W, False)
    o = ST.pool(r, list(r)); ST.add_recall(o); b = o['by_kind'].get('block', {})
    return dict(f1=o['pix']['f1'], P=o['pix']['precision'], R=o['pix']['recall'], nontext=o['nontext_called_text']['share'],
                block_px=b.get('recall'), block_words=f"{b.get('words_found')}/{b.get('words')}")


def main():
    outp = sys.argv[1]
    crops = json.load(open(os.path.join(TD, 'crops.json')))
    folds = {f: {k: v for k, v in crops.items() if fold_of(v['plate']) == f} for f in 'AB'}
    base = {p: cv2.imread(os.path.join(HERE, '..', 'base', f'{p}_text.png'), 0) for p in set(c['plate'] for c in crops.values())}
    table = []
    keys = list(GRID)
    base_sc = {f: score({k: base[c['plate']][c['win'][1]:c['win'][3], c['win'][0]:c['win'][2]] for k, c in folds[f].items()}, folds[f]) for f in 'AB'}
    print('finder3', base_sc, flush=True)
    for vals in itertools.product(*[GRID[k] for k in keys]):
        opts = dict(zip(keys, vals)); row = dict(opts=opts)
        for f in 'AB': row[f] = score(run(opts, folds[f], base), folds[f])
        table.append(row); print(opts, row['A'], row['B'], flush=True)
    best = {f: max(table, key=lambda r: r[f]['f1']) for f in 'AB'}
    out = dict(objective='pooled in-scope F1 (codes 2,3) on the fold block crops', grid=GRID, finder3=base_sc, table=table,
               tuned_on_A=dict(opts=best['A']['opts'], A=best['A']['A'], B_heldout=best['A']['B']),
               tuned_on_B=dict(opts=best['B']['opts'], B=best['B']['B'], A_heldout=best['B']['A']))
    json.dump(out, open(outp, 'w'), indent=1)
    print('tuned on A:', out['tuned_on_A']); print('tuned on B:', out['tuned_on_B'])


if __name__ == '__main__':
    main()
