"""Built-up mask and seeded random windows (sealed builder A, 26 Nov 2026). Scan and paper mask only.

Built-up: building colour on the paper. On the scan at 1/8 size, a pixel is building fill when it is on the paper
(cufp/N/png_alpha_s4.npy) and either pink/red (hue H < 12 or H > 160 of 180, HSV saturation at least the plate's median
paper saturation + 12) or yellow (12 <= H <= 35, saturation at least the median + 30). The paper itself is yellowish
(median S 37-61, H 18-20 on these plates), hence the plate-relative thresholds. Fill must also be light (HSV V >= 150):
the dark scanner border that the paper mask takes in on plates 41 and 46 is not a building. Fill is counted only 200 full
px or more inside the paper (the paper mask eroded by 25 px at 1/8), so the coloured sheet edge and the sheet tab do not count. A window is built up when building fill covers 10% or more of it and paper 97% or more.

    python -B scripts/builtup.py ditto     -> truth/annot/ditto_windows.json (12 windows of 500 x 500 px per plate,
                                              seed 'ditto-N', in draw order)
    python -B scripts/builtup.py full      -> truth/annot/full_window.json (SA-F1: plate drawn with seed 'SA-F1' from
                                              the 200 ft plates 35 38 41 66, then the window 1500 x 1000 with seed 'SA-F1-N')
Centres are drawn uniformly over the plate (random.Random(seed).randint) and kept when the window is built up; the
first ones kept are the windows, in that order."""
import os, sys, json, random
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import plate_img, ROOT
ANN = os.path.join(HERE, '..', 'truth', 'annot')
F = 8


def maps(N):
    im = plate_img(N); H, W = im.shape[:2]
    sm = cv2.resize(im, (W // F, H // F), interpolation=cv2.INTER_AREA)
    al = np.load(os.path.join(ROOT, 'cufp', N, 'png_alpha_s4.npy'))
    pap = cv2.resize(al.astype(np.uint8), (W // F, H // F), interpolation=cv2.INTER_NEAREST) > 0
    hsv = cv2.cvtColor(sm, cv2.COLOR_BGR2HSV); h, s = hsv[..., 0].astype(int), hsv[..., 1].astype(int)
    med = float(np.median(s[pap]))
    v = hsv[..., 2].astype(int)
    pin = cv2.erode(pap.astype(np.uint8), np.ones((51, 51), np.uint8)) > 0
    fill = pin & (v >= 150) & ((((h < 12) | (h > 160)) & (s >= med + 12)) | ((h >= 12) & (h <= 35) & (s >= med + 30)))
    return W, H, pap, fill


def draw(N, seed, ww, wh, n, avoid=None):
    avoid = list(avoid or [])
    W, H, pap, fill = maps(N); r = random.Random(seed); out = []; tries = 0
    ip = cv2.integral(pap.astype(np.uint8)); ifl = cv2.integral(fill.astype(np.uint8))
    S = lambda I, x0, y0, x1, y1: int(I[y1, x1] - I[y0, x1] - I[y1, x0] + I[y0, x0])
    while len(out) < n and tries < 20000:
        tries += 1
        cx, cy = r.randint(ww // 2, W - ww // 2 - 1), r.randint(wh // 2, H - wh // 2 - 1)
        x0, y0 = cx - ww // 2, cy - wh // 2; x1, y1 = x0 + ww, y0 + wh
        a, b, c, d = x0 // F, y0 // F, x1 // F, y1 // F; area = (c - a) * (d - b)
        pf, ff = S(ip, a, b, c, d) / area, S(ifl, a, b, c, d) / area
        if pf < 0.97 or ff < 0.10: continue
        if any(not (x1 <= q[0] or x0 >= q[2] or y1 <= q[1] or y0 >= q[3]) for q in avoid + [o['win'] for o in out]): continue
        out.append(dict(win=[x0, y0, x1, y1], paper=round(pf, 3), fill=round(ff, 3), draw=tries))
    return out


if __name__ == '__main__':
    if sys.argv[1] == 'full':
        N = random.Random('SA-F1').choice(['35', '38', '41', '66'])
        w = draw(N, f'SA-F1-{N}', 1500, 1000, 1)[0]
        rec = dict(plate=N, seed_plate='SA-F1', seed_window=f'SA-F1-{N}', **w)
        json.dump(rec, open(os.path.join(ANN, 'full_window.json'), 'w'), indent=1); print(rec)
    else:
        full = json.load(open(os.path.join(ANN, 'full_window.json')))
        res = {}
        for N in ['6', '9', '52', '35', '38', '41', '66', '46']:
            avoid = [full['win']] if N == full['plate'] else []
            res[N] = draw(N, f'ditto-{N}', 500, 500, 12, avoid)
            print(N, len(res[N]), [o['win'] for o in res[N]])
        json.dump(res, open(os.path.join(ANN, 'ditto_windows.json'), 'w'), indent=1)
