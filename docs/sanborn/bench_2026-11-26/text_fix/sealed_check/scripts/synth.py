"""Synthetic masks for the format check of sealed_final (sealed cross-check). No method output is used.
    cd data/sanborn
    python -B .../synth.py
Writes crop-sized 0/255 PNGs to sealed_check/synthetic/<kind>/<crop>.png for kind = truth (the truth's own text pixels,
mask == 2), allink (every ink pixel of the window, ink_bins' rule) and nothing (all 0). score_text.py is then run with
--binary on each (see the README)."""
import os, sys, json
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import FINAL, window
crops = json.load(open(os.path.join(FINAL, 'crops.json'), encoding='utf8'))
OUT = os.path.join(HERE, '..', 'synthetic')
for k in ('truth', 'allink', 'nothing'): os.makedirs(os.path.join(OUT, k), exist_ok=True)
for tid in sorted(crops, key=lambda t: (crops[t]['plate'], t)):
    c = crops[tid]; X0, Y0, X1, Y1 = c['win']
    M = cv2.imread(os.path.join(FINAL, f'{tid}_mask.png'), 0)
    _, _, ink, _ = window(c['plate'], X0, Y0, X1, Y1)
    cv2.imwrite(os.path.join(OUT, 'truth', f'{tid}.png'), ((M == 2) * 255).astype(np.uint8))
    cv2.imwrite(os.path.join(OUT, 'allink', f'{tid}.png'), (ink * 255).astype(np.uint8))
    cv2.imwrite(os.path.join(OUT, 'nothing', f'{tid}.png'), np.zeros(M.shape, np.uint8))
print(len(crops), 'crops x 3 synthetic masks')
