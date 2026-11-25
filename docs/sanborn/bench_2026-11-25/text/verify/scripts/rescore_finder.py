"""verify: independent rescoring of the finder's text codes against the CURRENT inventory truth masks (25 Nov 2026).

    cd data/sanborn; python -B bench_2026-11-25/text/verify/scripts/rescore_finder.py FINDER_DIR [TAG]

Written from scratch (does not import the finder's measure_truth.py). Scores text-pixel precision / recall on the truth's
1 (non-text ink) and 2 (text ink) pixels; 3 (don't care) and 0 (paper) are ignored. Finder text = codes 2, 3, 4.
Also: bin 8 of unet_data/N_bins.png on the same pixels, and pooled scores for the crops on which the finder was tuned
(T1-T3, plate 44) and the rest (T4 1A, T6 T7 5). Also: what the finder calls text on the truth's non-text ink, split by
the truth's own word boxes (is the false text inside a word box or out in the open) - for the over-claim check.
Writes verify/out/rescore_finder[_TAG].json."""
import json, os, sys
import numpy as np, cv2

V = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
TR = os.path.normpath(os.path.join(V, '..', 'inventory', 'truth'))
D = sys.argv[1]; TAG = sys.argv[2] if len(sys.argv) > 2 else ''
crops = json.load(open(os.path.join(TR, 'crops.json')))


def sc(pred, truth):
    t = truth == 2; nt = truth == 1
    tp = int((pred & t).sum()); fp = int((pred & nt).sum()); fn = int((~pred & t).sum())
    return dict(tp=tp, fp=fp, fn=fn)


def fin(d):
    P = d['tp'] / max(1, d['tp'] + d['fp']); R = d['tp'] / max(1, d['tp'] + d['fn'])
    return dict(d, precision=round(P, 4), recall=round(R, 4), f1=round(2 * P * R / max(1e-9, P + R), 4))


out = {}; codes = {}; bins = {}
for tid, c in sorted(crops.items()):
    f = os.path.join(TR, f'{tid}_mask.png')
    if not os.path.exists(f): continue
    N = c['plate']; x0, y0, x1, y1 = c['win']
    if N not in codes:
        codes[N] = cv2.imread(os.path.join(D, f'{N}_finder' + (f'_{TAG}' if TAG else '') + '.png'), 0)
        bins[N] = cv2.imread(f'unet_data/{N}_bins.png', 0)
    if codes[N] is None: continue
    truth = cv2.imread(f, 0); code = codes[N][y0:y1, x0:x1]; b = bins[N][y0:y1, x0:x1]
    fx = np.isin(code, (2, 3, 4)); b8 = b == 8
    # word boxes of the truth (any kind), to split false text into 'inside a word box' and 'in the open'
    W = json.load(open(os.path.join(TR, f'{tid}_words.json'), encoding='utf8'))['words']; wb = np.zeros(truth.shape, np.uint8)
    for w in W:
        p = w.get('poly')
        if p: cv2.fillPoly(wb, [np.round(np.array(p, float) - [x0, y0]).astype(np.int32)], 1)
    wbg = cv2.dilate(wb, np.ones((7, 7), np.uint8)) > 0
    fp_pix = fx & (truth == 1)
    r = dict(plate=N, finder=fin(sc(fx, truth)), finder_no_lone=fin(sc(np.isin(code, (2, 3)), truth)), bin8=fin(sc(b8, truth)),
             truth_px={str(v): int((truth == v).sum()) for v in range(4)},
             finder_fp_inside_wordbox_3px=int((fp_pix & wbg).sum()), finder_fp_open=int((fp_pix & ~wbg).sum()),
             ink_agree=round(float(((code > 0) == (truth > 0)).mean()), 5))
    out[tid] = r
    print(tid, N, 'finder', r['finder'], '| bin8', r['bin8'])
for name, ids in (('ALL', [t for t in out]), ('tuned_T1_T3_plate44', [t for t in out if out[t]['plate'] == '44']),
                  ('not_tuned_T4_T6_T7', [t for t in out if out[t]['plate'] != '44'])):
    for who in ('finder', 'finder_no_lone', 'bin8'):
        s = {k: sum(out[t][who][k] for t in ids) for k in ('tp', 'fp', 'fn')}
        out[f'{name}_{who}'] = fin(s); print(name, who, out[f'{name}_{who}'])
json.dump(out, open(os.path.join(V, 'out', f'rescore_finder{"_" + TAG if TAG else ""}{"_" + os.path.basename(os.path.normpath(D))}.json'), 'w'), indent=1)
