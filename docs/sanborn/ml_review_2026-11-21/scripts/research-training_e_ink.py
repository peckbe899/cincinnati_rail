# read-only: how much of edgenet.ink_image's "ink" is saturated colour (fills), labelled plates vs the most tinted plates
import cv2, numpy as np, json, os
SP = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
OUT = r'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/research-training/'
rows = json.load(open(OUT + 'b_colour.json')); tint = {r['plate']: r['tinted_share'] for r in rows}
plates = ['43', '44', '45', '80', '82A'] + ['54B', '1A', '1B', '54A', '8B', '55B', '53', '12', '51', '68'] + ['83B', '60B', '31']
for N in plates:
    im = cv2.imread(SP + f'cufp/22-{N}.jpg', cv2.IMREAD_REDUCED_COLOR_2); h, w = im.shape[:2]
    alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h)) > 0.5
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV); S, V = hsv[:, :, 1], hsv[:, :, 2]
    ink = ((V < 120) | ((S < 90) & (V < 170))) & alpha
    sat_ink = ink & (S >= 90)
    print(f'{N:4s} tint {tint.get(N, 0):.2f} | ink share of paper {ink.sum() / alpha.sum():.3f} | of the ink, saturated (S>=90) {sat_ink.sum() / max(1, ink.sum()):.3f}')
