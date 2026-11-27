"""Survey a plate at 1/4 size for block numbers (dev_block, 26 Nov 2026). Scan only: no finder output, no bins.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/dev_block/scripts/survey.py N [N ...] [--tiles 2x2]

Writes dev_block/pics/survey/sv_N_rRcC.jpg: the plate at 1/4 size, cut into tiles, with a grid every 500 full px
(labelled every 1000 px in full-plate px). The old held-out windows H1-H4 are outlined red (no pick may overlap them),
the dev truth windows T1-T7 blue (their block words are listed apart)."""
import os, sys, json
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.normpath(os.path.join(HERE, '..'))
ROOT = os.path.normpath(os.path.join(DB, '..', '..', '..'))
OUT = os.path.join(DB, 'pics', 'survey'); os.makedirs(OUT, exist_ok=True)
SEALED = set('6 9 52 56 58 63 35 38 41 66 71 76 84 88 46 92'.split())
H = {'90': [[5640, 3950, 7140, 4950], [880, 2100, 2380, 3100]], '47': [[7040, 4560, 8540, 5560]], '54A': [[7190, 3950, 8690, 4950]]}
T = {'44': [[1500, 1500, 3000, 2500], [2700, 2500, 4200, 3500], [9000, 2400, 10500, 3400]], '1A': [[2000, 950, 3500, 1950]],
     '5': [[3900, 1550, 5400, 2550], [1700, 3500, 3200, 4500]]}


def survey(N, tr=2, tc=2):
    assert N not in SEALED, 'sealed plate'
    im = cv2.imread(os.path.join(ROOT, 'cufp', f'22-{N}.jpg'), cv2.IMREAD_REDUCED_COLOR_4)
    h, w = im.shape[:2]
    for gx in range(500, w * 4, 500):
        X = gx // 4; im[:, X] = (im[:, X].astype(int) * 0.6 + np.array([0, 160, 0]) * 0.4).astype(np.uint8)
    for gy in range(500, h * 4, 500):
        Y = gy // 4; im[Y, :] = (im[Y, :].astype(int) * 0.6 + np.array([0, 160, 0]) * 0.4).astype(np.uint8)
    for gx in range(1000, w * 4, 1000):
        for gy in range(1000, h * 4, 1000):
            cv2.putText(im, f'{gx},{gy}', (gx // 4 + 2, gy // 4 - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 120, 0), 1)
    for x0, y0, x1, y1 in H.get(N, []): cv2.rectangle(im, (x0 // 4, y0 // 4), (x1 // 4, y1 // 4), (0, 0, 255), 2)
    for x0, y0, x1, y1 in T.get(N, []): cv2.rectangle(im, (x0 // 4, y0 // 4), (x1 // 4, y1 // 4), (255, 0, 0), 2)
    ys = np.linspace(0, h, tr + 1).astype(int); xs = np.linspace(0, w, tc + 1).astype(int)
    for r in range(tr):
        for c in range(tc):
            y0, y1 = max(0, ys[r] - 20), min(h, ys[r + 1] + 20); x0, x1 = max(0, xs[c] - 20), min(w, xs[c + 1] + 20)
            f = os.path.join(OUT, f'sv_{N}_r{r}c{c}.jpg'); cv2.imwrite(f, im[y0:y1, x0:x1], [cv2.IMWRITE_JPEG_QUALITY, 90])
            print(f, x1 - x0, y1 - y0)


if __name__ == '__main__':
    t = next((a.split('=')[1] for a in sys.argv if a.startswith('--tiles=')), '2x2'); tr, tc = [int(v) for v in t.split('x')]
    for N in [a for a in sys.argv[1:] if not a.startswith('--')]: survey(N, tr, tc)
