"""Text-pixel precision and recall of the finder, and of ink_bins' bin 8, on the inventory agent's hand-checked truth
crops (text/inventory/truth/T#_mask.png: 0 paper, 1 ink not text, 2 text ink, 3 don't care; crops.json gives plate and
window). Scored on the pixels the truth calls 1 or 2.

    cd data/sanborn
    python -B <this> FINDER_DIR TAG [T1 T2 ...]     (default: every T#_mask.png there is)

Also: recall per word kind (share of each kind's text ink found), from T#_words.json, and the words with less than half
their ink found."""
import json, os, sys, glob
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
TR = os.path.normpath(os.path.join(HERE, '..', '..', 'inventory', 'truth'))
TEXT = (2, 3, 4)


def score(pred, truth):
    m = (truth == 1) | (truth == 2); t = truth == 2; p = pred & m
    tp = int((p & t).sum()); fp = int((p & ~t).sum()); fn = int((t & ~pred).sum())
    P = tp / max(1, tp + fp); R = tp / max(1, tp + fn)
    return dict(tp=tp, fp=fp, fn=fn, precision=round(P, 4), recall=round(R, 4), f1=round(2 * P * R / max(1e-9, P + R), 4))


def poly_mask(shape, corners, off):
    m = np.zeros(shape, np.uint8); cv2.fillPoly(m, [np.round(np.array(corners, float) - off).astype(np.int32)], 1); return m > 0


if __name__ == '__main__':
    D, TAG = sys.argv[1], sys.argv[2]; crops = json.load(open(os.path.join(TR, 'crops.json')))
    ids = sys.argv[3:] or sorted(os.path.basename(f).split('_')[0] for f in glob.glob(os.path.join(TR, 'T*_mask.png')))
    out = {}; codes = {}
    for tid in ids:
        c = crops[tid]; N = c['plate']; x0, y0, x1, y1 = c['win']
        truth = cv2.imread(os.path.join(TR, f'{tid}_mask.png'), 0)
        if N not in codes: codes[N] = cv2.imread(os.path.join(D, f'{N}_finder' + ('' if TAG == '-' else f'_{TAG}') + '.png'), 0)
        code = codes[N][y0:y1, x0:x1]; bins = cv2.imread(f'unet_data/{N}_bins.png', 0)[y0:y1, x0:x1]
        assert truth.shape == code.shape, (truth.shape, code.shape)
        fx = np.isin(code, TEXT); b8 = bins == 8
        r = dict(plate=N, win=c['win'], truth_px={str(v): int((truth == v).sum()) for v in (1, 2, 3)},
                 finder=score(fx, truth), finder_no_lone=score(np.isin(code, (2, 3)), truth), bin8=score(b8, truth),
                 ink_agree=round(float(((code > 0) == (truth > 0)).mean()), 4))
        # recall by word kind
        W = json.load(open(os.path.join(TR, f'{tid}_words.json'), encoding='utf8')); kinds = {}; low = []
        for w in W['words']:
            box = w.get('poly') or w.get('box')
            if box is None: continue
            pm = poly_mask(truth.shape, box, np.array([x0, y0])) & (truth == 2)
            n = int(pm.sum())
            if not n: continue
            f = int((pm & fx).sum()); g = int((pm & b8).sum()); k = kinds.setdefault(w['kind'], [0, 0, 0, 0]); k[0] += n; k[1] += f; k[2] += g; k[3] += 1
            if f < 0.5 * n: low.append((w['reading'], w['kind'], round(f / n, 2)))
        r['by_kind'] = {k: dict(words=v[3], text_px=v[0], finder_recall=round(v[1] / v[0], 3), bin8_recall=round(v[2] / v[0], 3)) for k, v in sorted(kinds.items())}
        r['words_under_half_found'] = low
        out[tid] = r; print(tid, N, 'finder', r['finder'], '| bin8', r['bin8'], '| ink agree', r['ink_agree']); print('   ', r['by_kind']); print('    low:', low[:30])
    if len(out) > 1:
        T = [o for o in out.values()]
        for who in ('finder', 'finder_no_lone', 'bin8'):
            tp = sum(o[who]['tp'] for o in T); fp = sum(o[who]['fp'] for o in T); fn = sum(o[who]['fn'] for o in T)
            P = tp / max(1, tp + fp); R = tp / max(1, tp + fn); out[f'ALL_{who}'] = dict(tp=tp, fp=fp, fn=fn, precision=round(P, 4), recall=round(R, 4), f1=round(2 * P * R / (P + R), 4))
            print('ALL', who, out[f'ALL_{who}'])
    json.dump(out, open(os.path.join(D, f'truth_{TAG}.json'), 'w', encoding='utf8', newline='\n'), indent=1)
