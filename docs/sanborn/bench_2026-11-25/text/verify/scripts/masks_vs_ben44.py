"""verify (25 Nov 2026): the text masks of plate 44 against Ben's street lines and the truth crops T1-T3.

    cd data/sanborn; python -B bench_2026-11-25/text/verify/scripts/masks_vs_ben44.py

Ben's lines: streetmap/22-44.json, every line whose kind is not 'no_printed_line', drawn 1 px (my own raster).
For each mask (effect agent: Sref, S1 (map ground), I2, I2p, B2, B2L, nomap S0; finder: F = codes 2-4):
  line_ink_1px    ink within 1 px of his lines that the mask covers (px and share)
  cut_share       his lines sampled every 2 px; of the samples with ink within 2 px, the share whose ink is ALL masked
  truth T1-T3     text-pixel precision / recall on the inventory truth (1 and 2 pixels only)
  uses_truth      what of Ben's truth went into making the mask (from the makers' docstrings)
Writes verify/out/masks_vs_ben44.json."""
import json, os
import numpy as np, cv2
SP = os.getcwd(); T = os.path.join(SP, 'bench_2026-11-25', 'text'); V = os.path.join(T, 'verify')
im = cv2.imread('cufp/22-44.jpg'); H, W = im.shape[:2]
L = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0]; del im
paper = cv2.resize(np.load('cufp/44/png_alpha_s4.npy').astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
ink = (L < 140) & paper; del L
SM = json.load(open('streetmap/22-44.json', encoding='utf8'))
ben = np.zeros((H, W), np.uint8); S = []
for l in SM['lines']:
    if l.get('kind') == 'no_printed_line': continue
    a, b = np.array(l['a'], float), np.array(l['b'], float); cv2.line(ben, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), 1, 1)
    n = max(2, int(np.hypot(*(b - a)) / 2) + 1); S.append(a + np.linspace(0, 1, n)[:, None] * (b - a))
q = np.vstack(S).round().astype(int); q = q[(q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H)]
d = cv2.distanceTransform((ben == 0).astype(np.uint8), cv2.DIST_L2, 5); z1 = ink & (d <= 1)
k5 = np.ones((5, 5), np.uint8); has = cv2.dilate(ink.astype(np.uint8), k5)[q[:, 1], q[:, 0]] > 0
crops = json.load(open(os.path.join(T, 'inventory', 'truth', 'crops.json')))
MK = os.path.join(T, 'effect', 'masks')
masks = {'Sref': (os.path.join(MK, '44_map_Sref.png'), 'bin 8 of unet_data/44_bins.png: sorted with Ben street map + Ben rail'),
         'S1_map': (os.path.join(MK, '44_map_S1.png'), 'bin 8, sorted with Ben street map, rail result dropped'),
         'S0_nomap': (os.path.join(MK, '44_nomap_S0.png'), 'bin 8, sorted with no street map, rail rule own'),
         'I2': (os.path.join(MK, '44_map_I2.png'), 'from Sref (Ben map + rail), minus 16 px band round Ben rail'),
         'I2r': (os.path.join(MK, '44_map_I2r.png'), 'from S1_map (Ben map), minus 16 px band round Ben rail'),
         'I2p': (os.path.join(MK, '44_map_I2p.png'), 'I2 minus 3 px keep-out round long lines'),
         'B2': (os.path.join(MK, '44_map_B2.png'), 'word boxes from I2'),
         'B2L': (os.path.join(MK, '44_map_B2L.png'), 'B2 minus long-line ink'),
         'F_finder': (None, 'finder codes 2-4; no truth used in the run (rules tuned on 44, 1A, 5)')}
out = {}
for k, (f, why) in masks.items():
    if f is None:
        m = np.isin(cv2.imread(os.path.join(T, 'finder', 'out', '44_finder.png'), 0), (2, 3, 4))
    else:
        m = cv2.imread(f, 0) > 0
    m &= ink
    cut = cv2.dilate((ink & ~m).astype(np.uint8), k5)[q[:, 1], q[:, 0]] > 0
    r = dict(uses_truth=why, mask_ink_px=int(m.sum()), line_ink_1px=int((z1 & m).sum()), line_ink_1px_share=round(float((z1 & m).sum() / z1.sum()), 4),
             cut_share=round(float((has & ~cut).sum() / has.sum()), 4))
    tp = fp = fn = 0
    for tid in ('T1', 'T2', 'T3'):
        x0, y0, x1, y1 = crops[tid]['win']; t = cv2.imread(os.path.join(T, 'inventory', 'truth', f'{tid}_mask.png'), 0); p = m[y0:y1, x0:x1]
        tp += int((p & (t == 2)).sum()); fp += int((p & (t == 1)).sum()); fn += int((~p & (t == 2)).sum())
    r['truth_T1_T3'] = dict(precision=round(tp / max(1, tp + fp), 4), recall=round(tp / max(1, tp + fn), 4))
    out[k] = r; print(f"{k:9s} ink {r['mask_ink_px']:8d} | Ben line ink (1 px) taken {r['line_ink_1px']:6d} = {100*r['line_ink_1px_share']:.2f}% | Ben line cut at {100*r['cut_share']:.2f}% of samples | T1-T3 P {r['truth_T1_T3']['precision']} R {r['truth_T1_T3']['recall']} | {why}", flush=True)
out['_ben_line_ink_1px'] = int(z1.sum()); out['_samples_inked'] = int(has.sum())
json.dump(out, open(os.path.join(V, 'out', 'masks_vs_ben44.json'), 'w'), indent=1)
