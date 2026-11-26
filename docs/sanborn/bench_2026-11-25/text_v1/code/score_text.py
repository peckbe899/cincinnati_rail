"""score_text.py - score a text mask against the hand-checked text truth crops (25 Nov 2026, text_v1).

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/code/score_text.py MASK (--codes 2,3,4 | --binary) [options]

MASK   a PNG path. It may hold {plate} (44, 5, 1A ...) and/or {crop} (T1 ...), filled in per truth crop, e.g.
         bench_2026-11-25/text/finder/out/{plate}_finder.png --codes 2,3,4      (finder v1: 2 glyph, 3 taken in, 4 lone stroke)
         unet_data/{plate}_bins.png --codes 8                                   (ink_bins' bin 8)
         some/dir/{plate}_text.png --codes 2,3                                  (hand-off codes: 4 = shared ink, owned by the line)
         some/dir/{crop}_text.png --binary                                      (a 0/255 text mask cut to the crop window)
       The mask is either the size of the whole plate (the crop window is cut out of it) or the size of the crop window.
--codes  the mask values that count as text.   --binary  any value > 0 is text.
--truth DIR   the truth folder (default: text_v1/truth = truth v2). Each crop has T#_mask.png (0 paper, 1 ink that is
              not text, 2 text ink, 3 don't care), T#_words.json (words with kind and box) and crops.json (plate, window).
--crops T1,T2 only these crops (default: every crop in crops.json that has a <id>_mask.png, whatever the id).
--group NAME=T1,T2,T3   also pool these crops under NAME (repeatable). ALL and one pool per plate are always made.
--out FILE.json         write every number there (default: print only).   --quiet  print only the pooled lines.

What is scored (the same rules as verify/scripts/rescore_finder.py and finder/scripts/measure_truth.py):
- Pixels: only ink the truth calls 1 (not text) or 2 (text). tp = text called text, fp = non-text ink called text,
  fn = text not called text. precision = tp/(tp+fp), recall = tp/(tp+fn), F1. Pools add tp, fp, fn over crops.
- Don't care (truth 3) is skipped: its count and how much of it the mask calls text are reported, not scored.
  Paper (truth 0) is skipped too; text called on paper is reported (it should be 0 for a mask built on the same ink).
- Non-text ink called text = fp / (pixels the truth calls 1), split into fp inside a word box (grown 3 px) and in the open.
- Recall by word kind: for each word, its text pixels are the truth-2 pixels inside its box (poly in T#_words.json, not
  grown); found = those the mask calls text. Summed over the words of a kind (a pixel in two boxes counts for both).
  Also words found = words with at least half their text pixels found (the inventory README's word rule).
- For a code mask, a confusion table: for each mask value, how many pixels the truth calls 0, 1, 2, 3.
Measured numbers only; nothing here is an estimate.

Checked (25 Nov 2026): on truth v1 (--truth bench_2026-11-25/text/inventory/truth) it gives the same tp, fp and fn on all
6 crops as verify/scripts/rescore_finder.py: finder P 0.9486 R 0.8684 F1 0.9067, bin 8 P 0.8541 R 0.8465 F1 0.8502
(text_v1/truth-fix/scores/reproduce_verify_v1.txt). A crop-sized --binary mask scores the same as the plate-sized code
mask it was cut from."""
import argparse, glob, json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__))
DEF_TRUTH = os.path.normpath(os.path.join(HERE, '..', 'truth'))


def fin(d):
    tp, fp, fn = d['tp'], d['fp'], d['fn']
    P = tp / max(1, tp + fp); R = tp / max(1, tp + fn)
    return dict(d, precision=round(P, 4), recall=round(R, 4), f1=round(2 * P * R / max(1e-9, P + R), 4))


def poly_fill(shape, poly, off):
    m = np.zeros(shape, np.uint8)
    cv2.fillPoly(m, [np.round(np.array(poly, float) - off).astype(np.int32)], 1)
    return m > 0


def load_pred(pattern, plate, crop, win, cache):
    path = pattern.replace('{plate}', plate).replace('{crop}', crop)
    if path not in cache:
        if not os.path.exists(path): raise SystemExit(f'no mask file {path}')
        cache[path] = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if cache[path].ndim == 3: cache[path] = cache[path][..., 0]
    m = cache[path]; x0, y0, x1, y1 = win
    if m.shape == (y1 - y0, x1 - x0): return m, path          # cut to the crop window already (plates are far bigger)
    if m.shape[0] >= y1 and m.shape[1] >= x1: return m[y0:y1, x0:x1], path
    raise SystemExit(f'{path}: shape {m.shape} is neither the plate nor the crop window {win}')


def score_crop(tid, crop, truth, code, is_text, words, codes_mode):
    x0, y0, x1, y1 = crop['win']
    pred = is_text(code)
    t2 = truth == 2; t1 = truth == 1; t3 = truth == 3; t0 = truth == 0
    r = dict(plate=crop['plate'], win=crop['win'],
             pix=fin(dict(tp=int((pred & t2).sum()), fp=int((pred & t1).sum()), fn=int((~pred & t2).sum()))),
             truth_px={str(v): int((truth == v).sum()) for v in range(4)},
             dont_care=dict(px=int(t3.sum()), called_text=int((pred & t3).sum())),
             text_on_paper=int((pred & t0).sum()))
    r['nontext_called_text'] = dict(px=r['pix']['fp'], of=int(t1.sum()), share=round(r['pix']['fp'] / max(1, int(t1.sum())), 5))
    wb = np.zeros(truth.shape, np.uint8); kinds = {}; inbox = np.zeros(truth.shape, bool)
    for w in words:
        p = w.get('poly')
        if not p: continue
        pm = poly_fill(truth.shape, p, np.array([x0, y0])); cv2.fillPoly(wb, [np.round(np.array(p, float) - [x0, y0]).astype(np.int32)], 1)
        pt = pm & t2; inbox |= pt; n = int(pt.sum())
        if not n: continue
        f = int((pt & pred).sum()); k = kinds.setdefault(w['kind'], dict(words=0, text_px=0, found_px=0, words_found=0))
        k['words'] += 1; k['text_px'] += n; k['found_px'] += f; k['words_found'] += int(f >= 0.5 * n)
    wbg = cv2.dilate(wb, np.ones((7, 7), np.uint8)) > 0
    fp = pred & t1
    r['nontext_called_text'].update(inside_wordbox_3px=int((fp & wbg).sum()), open=int((fp & ~wbg).sum()))
    r['text_px_outside_every_box'] = int((t2 & ~inbox).sum())
    r['by_kind'] = kinds
    if codes_mode:
        r['confusion'] = {str(int(v)): {str(c): int(((code == v) & (truth == c)).sum()) for c in range(4)} for v in np.unique(code)}
    return r


def pool(res, ids):
    s = {k: sum(res[t]['pix'][k] for t in ids) for k in ('tp', 'fp', 'fn')}
    o = dict(crops=list(ids), pix=fin(s))
    of = sum(res[t]['nontext_called_text']['of'] for t in ids)
    o['nontext_called_text'] = dict(px=s['fp'], of=of, share=round(s['fp'] / max(1, of), 5),
                                    inside_wordbox_3px=sum(res[t]['nontext_called_text']['inside_wordbox_3px'] for t in ids),
                                    open=sum(res[t]['nontext_called_text']['open'] for t in ids))
    o['dont_care'] = {k: sum(res[t]['dont_care'][k] for t in ids) for k in ('px', 'called_text')}
    o['text_on_paper'] = sum(res[t]['text_on_paper'] for t in ids)
    kinds = {}
    for t in ids:
        for k, v in res[t]['by_kind'].items():
            a = kinds.setdefault(k, dict(words=0, text_px=0, found_px=0, words_found=0))
            for q in a: a[q] += v[q]
    o['by_kind'] = kinds
    return o


def add_recall(d):
    for k, v in d['by_kind'].items():
        v['recall'] = round(v['found_px'] / max(1, v['text_px']), 4); v['words_found_share'] = round(v['words_found'] / max(1, v['words']), 4)
    d['by_kind'] = dict(sorted(d['by_kind'].items()))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('mask'); g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--codes'); g.add_argument('--binary', action='store_true')
    ap.add_argument('--truth', default=DEF_TRUTH); ap.add_argument('--crops'); ap.add_argument('--group', action='append', default=[])
    ap.add_argument('--out'); ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    crops = json.load(open(os.path.join(a.truth, 'crops.json')))
    ids = a.crops.split(',') if a.crops else sorted(k for k in crops if os.path.exists(os.path.join(a.truth, f'{k}_mask.png')))   # any crop id in crops.json with a mask
    ids = [t for t in ids if os.path.exists(os.path.join(a.truth, f'{t}_mask.png'))]
    if a.binary: is_text = lambda c: c > 0; cm = False
    else:
        tc = [int(v) for v in a.codes.split(',')]; is_text = lambda c: np.isin(c, tc); cm = True
    cache = {}; res = {}
    for tid in ids:
        c = crops[tid]; truth = cv2.imread(os.path.join(a.truth, f'{tid}_mask.png'), 0)
        code, path = load_pred(a.mask, c['plate'], tid, c['win'], cache)
        assert code.shape == truth.shape, (tid, code.shape, truth.shape)
        W = json.load(open(os.path.join(a.truth, f'{tid}_words.json'), encoding='utf8'))['words']
        r = score_crop(tid, c, truth, code, is_text, W, cm); r['mask_file'] = path; add_recall(r); res[tid] = r
        if not a.quiet:
            p = r['pix']
            print(f"{tid:4s} {c['plate']:>4s}  P {p['precision']:.4f}  R {p['recall']:.4f}  F1 {p['f1']:.4f}   non-text ink called text {r['nontext_called_text']['share']:.4f}"
                  f"   don't care skipped {r['dont_care']['px']} (called text {r['dont_care']['called_text']})")
    pools = {'ALL': ids}
    for t in ids: pools.setdefault(f"plate_{crops[t]['plate']}", []).append(t)
    for s in a.group:
        n, v = s.split('='); pools[n] = [t for t in v.split(',') if t in res]
    out = dict(mask=a.mask, text=('binary >0' if a.binary else f'codes {a.codes}'), truth=os.path.abspath(a.truth), crops=res, pools={})
    for n, v in pools.items():
        if not v: continue
        o = pool(res, v); add_recall(o); out['pools'][n] = o; p = o['pix']
        print(f"{n:22s} P {p['precision']:.4f}  R {p['recall']:.4f}  F1 {p['f1']:.4f}   non-text ink called text {o['nontext_called_text']['share']:.4f}"
              f"   don't care skipped {o['dont_care']['px']}")
    o = out['pools']['ALL']
    print('recall by kind (ALL):  ' + '  '.join(f"{k} {v['recall']:.3f} ({v['words_found']}/{v['words']} words)" for k, v in o['by_kind'].items()))
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, 'w', encoding='utf8', newline='\n') as f: json.dump(out, f, indent=1)


if __name__ == '__main__':
    main()
