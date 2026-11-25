"""calib.py (diag/verify, 25 Nov 2026): is the new area maps' loss on 44 only a matter of where P = 0.5 falls?

For each new area map (the best checkpoints of V1S1, V1S2, V2S1, V2S2, as the run made them) and each tile grid, find the
8-bit threshold t at which the map calls the same share of the PAPER block as area_ng1's map of that grid does at 127
(no truth is used: only area_ng1's own map), then remap the map monotonically so that t lands on 127 ([0, t] -> [0, 127],
[t, 255] -> [128, 255]). The outline step and bench44 only read the area map through P > 0.5 (outlines.py blk/stt,
bench44 stage 0), so this is the same as moving their threshold to t for that map.
Writes diag/verify/mix/<S>_cal1/maps44/gridK/{44_area.png, 44_lines.png, source.txt}: the remapped area map with the
pair's own line map ('cal1', the pair as it ran, only the outline threshold moved), and <S>_cal0: the remapped area map
with the baseline's line map (like swap's m100). Prints the shares and thresholds; writes diag/verify/calib.json.
    python -B calib.py
"""
import json, os
import numpy as np
import cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
OUT = SP + 'bench_2026-11-25/diag/verify/'
BASE = SP + 'bench44_maps/grid{g}/'
paper = cv2.resize(np.load(SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (5384, 3609)) > 0.5
R = {}
for s in ('V1S1', 'V1S2', 'V2S1', 'V2S2'):
    R[s] = []
    for g in range(6):
        b = cv2.imread(BASE.format(g=g) + '44_area.png', 0)
        pair = SP + f'train_v2_runs/eval/{s}/maps44/grid{g}/'
        a = cv2.imread(pair + '44_area.png', 0)
        assert a.shape == b.shape == paper.shape
        target = float((b[paper] > 127).mean())
        h = np.bincount(a[paper].ravel(), minlength=256).astype(np.float64); above = h[::-1].cumsum()[::-1] / h.sum()   # above[t] = share with P >= t
        # threshold t: share(P > t) = above[t + 1]; pick t whose share is closest to the target
        shares = np.r_[above[1:], 0.0]
        t = int(np.argmin(np.abs(shares - target)))
        t = min(max(t, 1), 254)
        lut = np.zeros(256, np.float64); x = np.arange(256)
        lut[x <= t] = x[x <= t] * 127.0 / t
        lut[x > t] = 128.0 + (x[x > t] - (t + 1)) * 127.0 / max(1, 254 - t)
        lut = np.clip(np.round(lut), 0, 255).astype(np.uint8)
        a2 = lut[a]
        row = dict(grid=g, base_share=round(target, 4), own_share=round(float((a[paper] > 127).mean()), 4), t=t, t_P=round(t / 255, 3), cal_share=round(float((a2[paper] > 127).mean()), 4))
        R[s].append(row)
        for code, lines in (('cal1', pair + '44_lines.png'), ('cal0', BASE.format(g=g) + '44_lines.png')):
            d = OUT + f'mix/{s}_{code}/maps44/grid{g}/'; os.makedirs(d, exist_ok=True)
            cv2.imwrite(d + '44_area.png', a2)
            open(d + '44_lines.png', 'wb').write(open(lines, 'rb').read())
            open(d + 'source.txt', 'w').write(f'area {pair}44_area.png remapped so that P > {t}/255 -> > 127 (block share of paper {row["own_share"]} -> {row["cal_share"]}, area_ng1 {row["base_share"]})\nlines {lines}\n')
    print(s, R[s])
json.dump(R, open(OUT + 'calib.json', 'w'), indent=1)
