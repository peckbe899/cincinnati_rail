"""merge/v-eye: the ink bins drawn as the line editor colours them (ink_bins.COL), and random samples for the eye count
(21 Nov 2026). Reads only; writes into merge/v-eye/bins/.

    python -B bins_view.py thumb N            -> bins/N_thumb.jpg   before (unet_data/N_bins.png) | after (bins/N_bins.png), 1/6 size,
                                                 each bin max-pooled so thin lines stay visible
    python -B bins_view.py crop N X0 Y0 [S] [NAME]  -> bins/N_crop_NAME.jpg  before | after at full size (S px, default 1000)
    python -B bins_view.py sample N K SEED   -> bins/samples/N_bB_k.jpg and bins/samples/N.json: K random ink pixels of each
                                                of bins 1 block line, 2 lot line, 6 water pipe, 7 sewer (uniform over the
                                                bin's pixels), each shown as a 360 px crop of the scan (faded) with every
                                                ink pixel in its bin's colour and a ring round the sampled pixel; 9 per image
"""
import json, os, sys
import numpy as np
import cv2
import common as C
COL = {1: (0, 150, 0), 2: (255, 140, 0), 3: (20, 70, 120), 4: (0, 0, 230), 5: (0, 150, 255), 6: (160, 0, 0), 7: (160, 170, 0), 8: (255, 0, 255), 9: (120, 120, 120)}   # = staged ink_bins.COL (checked below)
NAMES = {1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text and numbers', 9: 'not sorted'}
src = open(C.SU + 'ink_bins.py', encoding='utf8').read()
assert "COL = {1: (0, 150, 0), 2: (255, 140, 0), 3: (20, 70, 120), 4: (0, 0, 230), 5: (0, 150, 255), 6: (160, 0, 0), 7: (160, 170, 0), 8: (255, 0, 255), 9: (120, 120, 120)}" in src
O = C.ME + 'bins/'


def paint(im, B):
    c = (im * 0.35 + 255 * 0.65).astype(np.uint8)
    for k in COL: c[B == k] = COL[k]
    return c


def legend(img, y0=8):
    x = 8
    for k in (1, 2, 3, 4, 5, 6, 7, 8, 9):
        cv2.rectangle(img, (x, y0), (x + 16, y0 + 16), COL[k], -1); cv2.putText(img, NAMES[k], (x + 20, y0 + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
        x += 30 + 9 * len(NAMES[k])
    return img


def load(n):
    full = cv2.imread(C.DATA + f'cufp/22-{n}.jpg'); before = cv2.imread(C.U + f'{n}_bins.png', cv2.IMREAD_UNCHANGED); after = cv2.imread(O + f'{n}_bins.png', cv2.IMREAD_UNCHANGED)
    return full, before, after


def thumb(n, f=6):
    full, before, after = load(n); H, W = full.shape[:2]; h, w = H // f, W // f
    base = (cv2.resize(full, (w, h), interpolation=cv2.INTER_AREA) * 0.35 + 255 * 0.65).astype(np.uint8)
    outs = []
    for B, t in ((before, f'{n} BEFORE: unet_data/{n}_bins.png'), (after, f'{n} AFTER: staged ink_bins.py fallback (merged block step)')):
        c = base.copy()
        for k in (8, 3, 9, 2, 6, 7, 5, 4, 1):   # later wins: block lines on top
            m = cv2.resize((B == k).astype(np.uint8), (w, h), interpolation=cv2.INTER_AREA) if False else cv2.dilate((B == k).astype(np.uint8), np.ones((f, f), np.uint8))[::f, ::f][:h, :w]
            c[m > 0] = COL[k]
        cv2.rectangle(c, (0, 0), (w, 54), (255, 255, 255), -1); cv2.putText(c, t, (8, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA); legend(c)
        outs.append(c)
    cv2.imwrite(C.must_be_mine(O + f'{n}_thumb.jpg'), np.hstack([outs[0], np.full((h, 6, 3), 255, np.uint8), outs[1]]), [cv2.IMWRITE_JPEG_QUALITY, 85])


def crop(n, x0, y0, S=1000, name=None):
    full, before, after = load(n); H, W = full.shape[:2]; x0 = max(0, min(W - S, x0)); y0 = max(0, min(H - S, y0))
    im = full[y0:y0 + S, x0:x0 + S]; ts = []
    for B, t in ((before, 'before'), (after, 'after')):
        c = paint(im, B[y0:y0 + S, x0:x0 + S]); cv2.rectangle(c, (0, 0), (S, 54), (255, 255, 255), -1)
        cv2.putText(c, f'{n} {t} x{x0} y{y0}', (8, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA); legend(c); ts.append(c)
    f = O + f'{n}_crop_{name or f"{x0}_{y0}"}.jpg'; cv2.imwrite(C.must_be_mine(f), np.hstack([ts[0], np.full((S, 6, 3), 255, np.uint8), ts[1]]), [cv2.IMWRITE_JPEG_QUALITY, 88]); return f


def sample(n, K, seed):
    full, _, after = load(n); H, W = full.shape[:2]; rng = np.random.default_rng(seed); S = 360; rec = []
    os.makedirs(O + 'samples', exist_ok=True)
    for b in (1, 2, 6, 7):
        ys, xs = np.nonzero(after == b); idx = rng.choice(len(ys), size=min(K, len(ys)), replace=False); tiles = []
        for j, i in enumerate(idx):
            y, x = int(ys[i]), int(xs[i]); x0 = max(0, min(W - S, x - S // 2)); y0 = max(0, min(H - S, y - S // 2))
            c = paint(full[y0:y0 + S, x0:x0 + S], after[y0:y0 + S, x0:x0 + S])
            cv2.circle(c, (x - x0, y - y0), 14, (0, 0, 0), 2, cv2.LINE_AA); cv2.circle(c, (x - x0, y - y0), 2, (0, 0, 255), -1)
            cv2.rectangle(c, (0, 0), (S, 22), (255, 255, 255), -1); cv2.putText(c, f'{n} {NAMES[b]} #{j}  ({x},{y})', (5, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
            tiles.append(c); rec.append(dict(plate=n, bin=b, name=NAMES[b], i=j, x=x, y=y))
        for k in range(0, len(tiles), 9):
            ts = tiles[k:k + 9] + [np.full((S, S, 3), 255, np.uint8)] * (9 - len(tiles[k:k + 9]))
            sv = np.full((S, 6, 3), 255, np.uint8); row = lambda a: np.hstack([a[0], sv, a[1], sv, a[2]]); sh = np.full((6, 3 * S + 12, 3), 255, np.uint8)
            cv2.imwrite(C.must_be_mine(O + f'samples/{n}_b{b}_{k // 9}.jpg'), np.vstack([row(ts[:3]), sh, row(ts[3:6]), sh, row(ts[6:])]), [cv2.IMWRITE_JPEG_QUALITY, 88])
    json.dump(dict(plate=n, K=K, seed=seed, sample=rec), open(C.must_be_mine(O + f'samples/{n}.json'), 'w'), indent=1)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'thumb': thumb(a[1])
    elif a[0] == 'crop': print(crop(a[1], int(a[2]), int(a[3]), int(a[4]) if len(a) > 4 else 1000, a[5] if len(a) > 5 else None))
    elif a[0] == 'sample': sample(a[1], int(a[2]), int(a[3]))
