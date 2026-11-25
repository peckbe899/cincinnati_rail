"""verify (25 Nov 2026): is there coloured lettering that the black-ink threshold (Lab L < 140) never sees?

    cd data/sanborn; python -B bench_2026-11-25/text/verify/scripts/colour_text.py N [N ...]

For each plate: pixels that are NOT ink (L >= 140) but strongly coloured and darker than the fills around them:
chroma = hypot(a-128, b-128) >= 28 and L < 175, inside the paper mask. Fills (pink brick, yellow frame, blue stone, grey)
are wide; lettering is thin, so the coloured pixels are kept only where a 9 px opening removes them (strokes under about
9 px), then joined into pieces; pieces 8-80 px tall with 30-2000 px are 'coloured glyph-sized pieces'. Each plate gets a
count by hue and a contact sheet of up to 48 of them (random, seed 3), 3x context, for looking.
Also the same on the ink side: ink pieces whose median chroma is >= 20 (coloured ink dark enough to pass L < 140).
Writes verify/out/colour_text.json and verify/pics/colour_<N>.jpg."""
import json, os, sys
import numpy as np, cv2
T = os.path.join(os.getcwd(), 'bench_2026-11-25', 'text'); V = os.path.join(T, 'verify'); rng = np.random.default_rng(3)
res = json.load(open(os.path.join(V, 'out', 'colour_text.json'))) if os.path.exists(os.path.join(V, 'out', 'colour_text.json')) else {}
for N in sys.argv[1:]:
    im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
    paper = cv2.resize(np.load(f'cufp/{N}/png_alpha_s4.npy').astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB); L = lab[..., 0]; a = lab[..., 1].astype(np.int16) - 128; b = lab[..., 2].astype(np.int16) - 128
    ch = np.hypot(a, b)
    col = ((ch >= 28) & (L >= 140) & (L < 175) & paper).astype(np.uint8)
    thin = col & ~cv2.morphologyEx(col, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    thin = cv2.morphologyEx(thin, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, lb, st, cen = cv2.connectedComponentsWithStats(thin, connectivity=8)
    hh = np.maximum(st[:, 2], st[:, 3]); ok = (hh >= 8) & (hh <= 80) & (st[:, 4] >= 30) & (st[:, 4] <= 2000); ok[0] = False
    idx = np.nonzero(ok)[0]
    hue = {}
    for i in idx:
        x, y, w, h = st[i, :4]; m = lb[y:y + h, x:x + w] == i
        aa, bb = float(np.median(a[y:y + h, x:x + w][m])), float(np.median(b[y:y + h, x:x + w][m]))
        k = 'red' if aa > 15 and aa > abs(bb) else ('yellow' if bb > 15 and bb >= aa else ('blue' if bb < -10 else 'other'))
        hue[k] = hue.get(k, 0) + 1
    # coloured INK pieces (pass the threshold but are coloured)
    ink = ((L < 140) & paper).astype(np.uint8); ni, li, si, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    chs = np.zeros(ni); cnt = np.bincount(li.ravel(), minlength=ni)
    ys, xs = np.nonzero(ink); l = li[ys, xs]; sumch = np.bincount(l, ch[ys, xs], minlength=ni); chs = sumch / np.maximum(cnt, 1)
    hi = np.maximum(si[:, 2], si[:, 3]); cink = np.nonzero((chs >= 20) & (hi >= 8) & (hi <= 80) & (si[:, 4] >= 30))[0]; cink = cink[cink > 0]
    res[N] = dict(coloured_thin_pieces=int(len(idx)), by_hue=hue, coloured_px=int(thin[lb > 0].sum()) if n > 1 else 0,
                  coloured_ink_pieces_glyph_sized=int(len(cink)), ink_pieces=int(ni - 1))
    print(N, res[N], flush=True)
    sel = list(rng.permutation(idx)[:36]) + list(rng.permutation(cink)[:12])
    tiles = []
    for j, i in enumerate(sel):
        S = si if j >= min(36, len(idx)) else st
        x, y, w, h = S[i, :4]; cx, cy = x + w // 2, y + h // 2; r = 60
        X0, Y0 = max(0, cx - r), max(0, cy - r); t = im[Y0:Y0 + 2 * r, X0:X0 + 2 * r].copy()
        t = cv2.copyMakeBorder(t, 0, 2 * r - t.shape[0], 0, 2 * r - t.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255))
        t = cv2.resize(t, (180, 180), interpolation=cv2.INTER_NEAREST)
        cv2.rectangle(t, (0, 0), (179, 179), (0, 0, 255) if j < min(36, len(idx)) else (255, 0, 0), 2); tiles.append(t)
    while len(tiles) % 8: tiles.append(np.full((180, 180, 3), 255, np.uint8))
    if tiles:
        rows = [np.hstack(tiles[k:k + 8]) for k in range(0, len(tiles), 8)]
        cv2.imwrite(os.path.join(V, 'pics', f'colour_{N}.jpg'), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
json.dump(res, open(os.path.join(V, 'out', 'colour_text.json'), 'w'), indent=1)
