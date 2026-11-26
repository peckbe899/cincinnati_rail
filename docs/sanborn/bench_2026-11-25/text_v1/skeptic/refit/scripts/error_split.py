"""Where does finder v2 go wrong on truth v2 (T1-T7), and how much of it could a second opinion on PIECES fix?
(classifier step, 26 Nov 2026; dev analysis on T1-T7 only, never the held-out crops)

    cd data/sanborn; python -B bench_2026-11-25/text_v1/classifier/scripts/error_split.py

For each crop: text missed (truth 2 not called 2/3) split by finder2's final code (1 line, 4 shared, 5 other) and, for
code 5, by the finder kind of the piece; non-text called text (truth 1 called 2/3) split by code and piece kind (or 'big'
for big-letter ink outside any piece). A piece is 'mostly text' when 60% or more of its scored pixels are truth 2."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from dump_pieces import load  # noqa
TRUTH = os.path.join('bench_2026-11-25', 'text_v1', 'truth')


def main():
    crops = json.load(open(os.path.join(TRUTH, 'crops.json'))); out = {}
    tot = {}
    for tid in ('T1', 'T2', 'T3', 'T4', 'T6', 'T7'):
        c = crops[tid]; x0, y0, x1, y1 = c['win']; D = load(c['plate'])
        tr = cv2.imread(os.path.join(TRUTH, f'{tid}_mask.png'), 0); fin = D['final'][y0:y1, x0:x1]
        # piece label image in the window
        lab = np.zeros(tr.shape, np.int32); kind = D['kind']
        bb = D['bbox']; sel = np.nonzero((bb[:, 0] < x1) & (bb[:, 1] < y1) & (bb[:, 0] + bb[:, 2] > x0) & (bb[:, 1] + bb[:, 3] > y0))[0]
        from dump_pieces import mask
        for i in sel:
            x, y, w, h = bb[i]; m = mask(D, i) > 0
            X0, Y0, X1, Y1 = max(x, x0), max(y, y0), min(x + w, x1), min(y + h, y1)
            sub = m[Y0 - y:Y1 - y, X0 - x:X1 - x]; lab[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0][sub] = i + 1
        text = np.isin(fin, (2, 3)); t2 = tr == 2; t1 = tr == 1
        r = dict(tp=int((text & t2).sum()), fp=int((text & t1).sum()), fn=int((~text & t2).sum()))
        fn = ~text & t2; fp = text & t1
        r['fn_by_code'] = {str(v): int((fn & (fin == v)).sum()) for v in (0, 1, 4, 5)}
        def bykind(sel_):
            d = {}
            ks = np.where(lab[sel_] > 0, kind[np.maximum(lab[sel_] - 1, 0)], 'nopiece')
            for k_, n_ in zip(*np.unique(ks, return_counts=True)): d[str(k_)] = int(n_)
            return d
        r['fn5_by_kind'] = bykind(fn & (fin == 5))
        r['fp_by_code'] = {str(v): int((fp & (fin == v)).sum()) for v in (2, 3)}
        r['fp_by_kind'] = bykind(fp)
        # piece-level: pieces that are mostly text but code 5, and mostly non-text but code 2/3
        ids = np.unique(lab[lab > 0])
        pt2 = np.bincount(lab[t2], minlength=lab.max() + 1); pt1 = np.bincount(lab[t1], minlength=lab.max() + 1)
        ptx = np.bincount(lab[text], minlength=lab.max() + 1); pall = np.bincount(lab[lab > 0], minlength=lab.max() + 1)
        flip_to_text = flip_to_junk = 0; nft = nfj = 0
        for j in ids:
            sc = pt2[j] + pt1[j]
            if sc == 0: continue
            istext = ptx[j] >= 0.5 * pall[j]
            if pt2[j] >= 0.6 * sc and not istext: flip_to_text += pt2[j] - pt1[j]; nft += 1
            if pt1[j] >= 0.6 * sc and istext: flip_to_junk += pt1[j] - pt2[j]; nfj += 1
        r['ideal_piece_flips'] = dict(to_text_pieces=nft, to_text_net_tp=int(flip_to_text), to_junk_pieces=nfj, to_junk_net_fp=int(flip_to_junk))
        out[tid] = r
        for k_ in ('tp', 'fp', 'fn'): tot[k_] = tot.get(k_, 0) + r[k_]
        for k_ in ('fn_by_code', 'fn5_by_kind', 'fp_by_code', 'fp_by_kind'):
            for a, b in r[k_].items(): tot.setdefault(k_, {}); tot[k_][a] = tot[k_].get(a, 0) + b
        for a, b in r['ideal_piece_flips'].items(): tot.setdefault('ideal', {}); tot['ideal'][a] = tot['ideal'].get(a, 0) + b
        print(tid, json.dumps(r))
    P = tot['tp'] / (tot['tp'] + tot['fp']); R = tot['tp'] / (tot['tp'] + tot['fn'])
    print('ALL', f'P {P:.4f} R {R:.4f} F1 {2*P*R/(P+R):.4f}', json.dumps({k: v for k, v in tot.items() if k not in ('tp', 'fp', 'fn')}, indent=0))
    i = tot['ideal']; tp = tot['tp'] + i['to_text_net_tp']; fp = tot['fp'] - i['to_junk_net_fp']; fn = tot['fn'] - i['to_text_net_tp']
    P = tp / (tp + fp); R = tp / (tp + fn); print(f'with every piece flipped right (an upper bound): P {P:.4f} R {R:.4f} F1 {2*P*R/(P+R):.4f}')
    json.dump(dict(crops=out, all=tot), open(os.path.join(HERE, '..', 'out', 'error_split_finder2.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
