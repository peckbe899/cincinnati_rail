"""Score ink_bins' text bin (bin 8 of unet_data/N_bins.png, the plates' current bins) against the hand-checked text
truth, and count bin 8 on the eight inventory plates.
python -B bin8_eval.py      -> measure/bin8_eval.json, measure/bin8_eval.md, measure/bin8_err_T#.jpg

On ink only (truth mask 1 or 2; don't-care 3 left out): precision, recall, F1 of bin 8 as "text".
Misses (text not in bin 8): which bin took them, by word kind, and for words whose glyphs are joined to a line.
False text (bin 8 on non-text ink): each 8-connected piece is put in one class by its shape and its neighbours:
  dash      thin straight piece (thickness <= 7, length 8-75, length/thickness >= 3): dashes of sewer, lot and
            building lines, rail ticks
  bar       heavy straight piece (thickness 8-24, length 35-220): streetcar dashes
  blob      compact filled piece (area >= 150, fill >= 0.6, aspect <= 2): hydrants, solid dots
  stub      any other piece touching ink of another bin (line, outline, pipe, sewer, rail): a line end or corner
            cut off from its line
  mark      what is left: hook marks, symbols, X of stables, curved bits
Picture: text found (magenta), text missed (red), false text (green), other ink grey."""
import os, json
import numpy as np, cv2
from common import INV, ROOT, bins, plate_img, jdump

OUT = os.path.join(INV, 'measure'); os.makedirs(OUT, exist_ok=True)
NAMES = {0: 'no ink', 1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text', 9: 'not sorted'}


def shape(lab, n):
    ys, xs = np.nonzero(lab); l = lab[ys, xs]; A = np.bincount(l, minlength=n).astype(float); A[A == 0] = 1
    mx = np.bincount(l, xs, n) / A; my = np.bincount(l, ys, n) / A; dx = xs - mx[l]; dy = ys - my[l]
    sxx = np.bincount(l, dx * dx, n) / A; syy = np.bincount(l, dy * dy, n) / A; sxy = np.bincount(l, dx * dy, n) / A
    t = (sxx + syy) / 2; d = np.sqrt(np.maximum(((sxx - syy) / 2) ** 2 + sxy ** 2, 0))
    return A, np.sqrt(12 * (t + d) + 1), np.sqrt(12 * np.maximum(t - d, 0) + 1)


def evaluate():
    crops = json.load(open(os.path.join(INV, 'truth', 'crops.json')))
    tot = dict(tp=0, fp=0, fn=0); per = {}; fn_bins = {}; fp_cls = {}; kind_rec = {}; touch_rec = {'joined to a line': [0, 0], 'free': [0, 0]}
    words_missed = {}; dash_near = dict(sewer_or_pipe=0, other=0)
    for tid, c in crops.items():
        p = c['plate']; X0, Y0, X1, Y1 = c['win']
        M = cv2.imread(os.path.join(INV, 'truth', f'{tid}_mask.png'), 0)
        B = bins(p)[Y0:Y1, X0:X1]
        W = json.load(open(os.path.join(INV, 'truth', f'{tid}_words.json'), encoding='utf8'))['words']
        ink_m = M > 0; ink_b = B > 0
        agree = float((ink_m == ink_b).mean())
        scored = (M == 1) | (M == 2); text = M == 2; b8 = B == 8
        tp = int((b8 & text).sum()); fp = int((b8 & (M == 1)).sum()); fn = int((~b8 & text).sum())
        per[tid] = dict(plate=p, ink_px=int(ink_m.sum()), text_px=int(text.sum()), dont_care_px=int((M == 3).sum()), bin8_px_on_scored_ink=int((b8 & scored).sum()),
                        precision=round(tp / max(1, tp + fp), 3), recall=round(tp / max(1, tp + fn), 3), f1=round(2 * tp / max(1, 2 * tp + fp + fn), 3),
                        truth_text_share_of_ink=round(text.sum() / max(1, scored.sum()), 3), bin8_share_of_ink=round((b8 & scored).sum() / max(1, scored.sum()), 3),
                        ink_agreement_with_bins_png=round(agree, 4))
        tot['tp'] += tp; tot['fp'] += fp; tot['fn'] += fn
        for v in range(10):
            k = NAMES[v]; fn_bins[k] = fn_bins.get(k, 0) + int((text & ~b8 & (B == v)).sum())
        # per word: its text pixels and how many bin 8 has
        lab = np.zeros(M.shape, np.int32)
        for i, w in enumerate(W):
            cv2.fillPoly(lab, [np.round(np.array(w['poly']) - [X0, Y0]).astype(np.int32)], i + 1)
        lab = cv2.dilate(lab.astype(np.float32), np.ones((5, 5), np.uint8)).astype(np.int32)   # glyph edges the box grown 1.5 px reaches
        n_w = len(W) + 1
        wt = np.bincount(lab[text], minlength=n_w); w8 = np.bincount(lab[text & b8], minlength=n_w)
        for i, w in enumerate(W):
            if wt[i + 1] < 10: continue
            k = w['kind']; kr = kind_rec.setdefault(k, [0, 0, 0, 0]); kr[0] += int(w8[i + 1]); kr[1] += int(wt[i + 1])
            r = w8[i + 1] / wt[i + 1]; kr[2] += 1; kr[3] += int(r < 0.5)
            key = 'joined to a line' if w['touches_line'] else 'free'; touch_rec[key][0] += int(w8[i + 1]); touch_rec[key][1] += int(wt[i + 1])
            if r < 0.5: words_missed.setdefault(k, []).append(f"{tid} {w['reading']} ({r:.2f}{', joined to a line' if w['touches_line'] else ''})")
        # false text pieces
        fpm = (b8 & (M == 1)).astype(np.uint8)
        n, lb, st, _ = cv2.connectedComponentsWithStats(fpm, connectivity=8)
        A, lg, th = shape(lb, n); fill = st[:, 4] / np.maximum(1, st[:, 2] * st[:, 3]); asp = np.maximum(st[:, 2], st[:, 3]) / np.maximum(1, np.minimum(st[:, 2], st[:, 3]))
        other = ((B > 0) & (B != 8)).astype(np.uint8)
        touch_other = np.bincount(lb.ravel(), (cv2.dilate(other, np.ones((3, 3), np.uint8)) > 0).ravel(), minlength=n) > 0
        near_sp = np.bincount(lb.ravel(), (cv2.dilate(((B == 6) | (B == 7)).astype(np.uint8), np.ones((61, 61), np.uint8)) > 0).ravel(), minlength=n) > 0
        for k in range(1, n):
            a = int(st[k, 4])
            if th[k] <= 7 and 8 <= lg[k] <= 75 and lg[k] / th[k] >= 3: cls = 'dash'
            elif 8 <= th[k] <= 24 and 35 <= lg[k] <= 220 and lg[k] / th[k] >= 3: cls = 'bar'
            elif a >= 150 and fill[k] >= 0.6 and asp[k] <= 2: cls = 'blob'
            elif touch_other[k]: cls = 'stub'
            else: cls = 'mark'
            e = fp_cls.setdefault(cls, [0, 0]); e[0] += 1; e[1] += a
            if cls == 'dash': dash_near['sewer_or_pipe' if near_sp[k] else 'other'] += a
        # picture
        im = plate_img(p)[Y0:Y1, X0:X1]
        pic = (im * 0.25 + 190).astype(np.uint8); pic[(M == 1) & ~b8] = (150, 150, 150); pic[(M == 3)] = (0, 200, 255)
        pic[text & b8] = (200, 0, 200); pic[text & ~b8] = (0, 0, 230); pic[(M == 1) & b8] = (0, 170, 0)
        cv2.imwrite(os.path.join(OUT, f'bin8_err_{tid}.jpg'), pic, [cv2.IMWRITE_JPEG_QUALITY, 90])
    P = tot['tp'] / (tot['tp'] + tot['fp']); R = tot['tp'] / (tot['tp'] + tot['fn'])
    fn_tot = sum(fn_bins.values())
    res = dict(note='bin 8 of unet_data/N_bins.png against truth/T*_mask.png on scored ink (truth 1 or 2). Made by bin8_eval.py. Measured.',
               pooled=dict(tp=tot['tp'], fp=tot['fp'], fn=tot['fn'], precision=round(P, 3), recall=round(R, 3), f1=round(2 * P * R / (P + R), 3)),
               per_crop=per,
               missed_text_went_to={k: dict(px=v, share=round(v / max(1, fn_tot), 3)) for k, v in sorted(fn_bins.items(), key=lambda t: -t[1]) if v},
               recall_by_kind={k: dict(recall=round(v[0] / max(1, v[1]), 3), words=v[2], words_mostly_missed=v[3]) for k, v in sorted(kind_rec.items())},
               recall_joined_vs_free={k: dict(recall=round(v[0] / max(1, v[1]), 3), text_px=v[1]) for k, v in touch_rec.items()},
               false_text_pieces={k: dict(pieces=v[0], px=v[1], share_px=round(v[1] / max(1, tot['fp']), 3)) for k, v in sorted(fp_cls.items(), key=lambda t: -t[1][1])},
               false_dash_px_within_30px_of_pipe_or_sewer_bins=dash_near,
               words_mostly_missed={k: v for k, v in sorted(words_missed.items())})
    return res


def plates():
    out = {}
    for p in ['44', '1A', '5', '90', '30', '60B', '47', '54A']:
        j = json.load(open(os.path.join(ROOT, 'unet_data', f'{p}_bins.json')))
        b = j['bins']; ink = j['ink_px']
        out[p] = dict(ink_px=ink, bin8_px=b['8']['px'], bin8_share=round(b['8']['px'] / ink, 3), ground_from=j.get('ground_from'),
                      shares={v['name']: round(v['px'] / ink, 3) for v in b.values()})
        B = bins(p)
        n, lb, st, _ = cv2.connectedComponentsWithStats((B == 8).astype(np.uint8), connectivity=8)
        out[p]['bin8_pieces'] = int(n - 1); out[p]['bin8_piece_px_median'] = float(np.median(st[1:, 4])) if n > 1 else None
    return out


if __name__ == '__main__':
    r = evaluate(); r['plates'] = plates()
    jdump(r, os.path.join(OUT, 'bin8_eval.json'))
    print(json.dumps({k: r[k] for k in ('pooled', 'missed_text_went_to', 'recall_by_kind', 'recall_joined_vs_free', 'false_text_pieces', 'false_dash_px_within_30px_of_pipe_or_sewer_bins')}, indent=1))
    for t, v in r['per_crop'].items(): print(t, v)
    for p, v in r['plates'].items(): print(p, v['bin8_share'], v['bin8_pieces'], v['bin8_piece_px_median'], v['ground_from'])
