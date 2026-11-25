"""Measure the finder on plates with Ben's lines (44, 1A, 5): (a) Ben's street-line ink called text, (b) against
ink_bins' bin 8 (unet_data/N_bins.png). Reads a finder output N_finder[_TAG].png.

    cd data/sanborn
    python -B <this> FINDER_DIR TAG N [N ...]      (TAG '-' for none)

(a) true line ink = ink within 3 px of one of Ben's lines (printed, drawn, sheet edge; benlines.py). Also within 1 px.
    Text that touches a line has pixels inside 3 px of it, so this is an upper bound on line ink called text.
(b) bin 8 of ink_bins: share the finder calls text; what the finder calls text that ink_bins put in other bins."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import benlines
NAMES = {1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text and numbers', 9: 'not sorted'}
TEXT = (2, 3, 4)


def measure(N, code, bins=None):
    H, W = code.shape; ink = code > 0; text = np.isin(code, TEXT)
    m, info = benlines.raster(N, W, H)
    d = cv2.distanceTransform((m == 0).astype(np.uint8), cv2.DIST_L2, 5)
    r = dict(plate=N, ben_lines=info, ink_px=int(ink.sum()), text_px=int(text.sum()))
    for tol in (1, 3):
        z = ink & (d <= tol); t = z & text
        r[f'a_line_ink_{tol}px'] = dict(line_ink_px=int(z.sum()), called_text_px=int(t.sum()), share=round(float(t.sum()) / max(1, z.sum()), 5),
                                       by_code={str(c): int((z & (code == c)).sum()) for c in (1, 2, 3, 4, 5)})
    # per kind
    r['a_by_kind_3px'] = {}
    for kd in benlines.KINDS:
        mk, _ = benlines.raster(N, W, H, kinds=(kd,)); dk = cv2.distanceTransform((mk == 0).astype(np.uint8), cv2.DIST_L2, 5)
        z = ink & (dk <= 3); r['a_by_kind_3px'][kd] = dict(px=int(z.sum()), text=int((z & text).sum()), share=round(float((z & text).sum()) / max(1, z.sum()), 5))
    # (a') length: Ben's lines sampled every 2 px; where there is ink within 2 px, is ALL of it called text? (then taking the
    # text out would cut his line there)
    L, _ = benlines.lines(N, W, H); S = []
    for l in L:
        if l['kind'] not in benlines.KINDS: continue
        a, b = np.array(l['a'], float), np.array(l['b'], float); n = max(2, int(np.hypot(*(b - a)) / 2) + 1); S.append(a + np.linspace(0, 1, n)[:, None] * (b - a))
    q = np.vstack(S).round().astype(int); q = q[(q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H)]
    k5 = np.ones((5, 5), np.uint8); has = cv2.dilate(ink.astype(np.uint8), k5)[q[:, 1], q[:, 0]] > 0
    def lost(t):
        keep = cv2.dilate((ink & ~t).astype(np.uint8), k5)[q[:, 1], q[:, 0]] > 0; return int((has & ~keep).sum())
    r['a_length'] = dict(samples=int(len(q)), inked=int(has.sum()), finder_cut=lost(text), finder_cut_share=round(lost(text) / max(1, has.sum()), 5))
    if bins is not None:
        r['a_length'].update(bin8_cut=lost(bins == 8), bin8_cut_share=round(lost(bins == 8) / max(1, has.sum()), 5))
    if bins is not None:
        b8 = bins == 8; r['b_bin8_px'] = int(b8.sum()); r['b_bin8_found_px'] = int((b8 & text).sum()); r['b_bin8_recall'] = round(float((b8 & text).sum()) / max(1, b8.sum()), 4)
        r['b_bin8_finder_codes'] = {str(c): int((b8 & (code == c)).sum()) for c in (1, 2, 3, 4, 5)}
        r['b_finder_text_by_bin'] = {NAMES.get(k, str(k)): int((text & (bins == k)).sum()) for k in range(0, 10)}
        r['b_added_px'] = int((text & ~b8).sum()); r['b_added_share_of_text'] = round(float((text & ~b8).sum()) / max(1, text.sum()), 4)
        z = ink & (d <= 3); r['b_bin8_on_ben_lines_3px'] = dict(px=int((z & b8).sum()), share_of_line_ink=round(float((z & b8).sum()) / max(1, z.sum()), 5))
        z1 = ink & (d <= 1); r['b_bin8_on_ben_lines_1px'] = dict(px=int((z1 & b8).sum()), share_of_line_ink=round(float((z1 & b8).sum()) / max(1, z1.sum()), 5))
    return r, d


if __name__ == '__main__':
    D, TAG = sys.argv[1], sys.argv[2]; out = {}
    for N in sys.argv[3:]:
        code = cv2.imread(os.path.join(D, f'{N}_finder' + ('' if TAG == '-' else f'_{TAG}') + '.png'), 0)
        bins = cv2.imread(f'unet_data/{N}_bins.png', 0)
        r, _ = measure(N, code, bins); out[N] = r
        print(json.dumps(r, indent=None)[:3000])
    json.dump(out, open(os.path.join(D, f'measure_{TAG}.json'), 'w', encoding='utf8', newline='\n'), indent=1)
