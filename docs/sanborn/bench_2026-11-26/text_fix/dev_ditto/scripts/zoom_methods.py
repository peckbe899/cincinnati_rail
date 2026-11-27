"""Zoom pictures of every ditto target (and of the negatives called text): scan | finder3 codes | finder2 codes | bin 8
(dev_ditto, 26 Nov 2026). Run after scoring (reads runs/cut/ and scores/summary.json).

    cd data/sanborn; python -B bench_2026-11-26/text_fix/dev_ditto/scripts/zoom_methods.py

Finder codes: 1 line grey, 2 text sure magenta, 3 text by context blue, 4 shared yellow, 5 other ink green (finder2's
overlay colours). bin 8: bin 8 red, other ink grey. The word box is drawn in cyan. Title: word id, style, text px,
then F = finder3 found px / B = bin 8 found px. Writes dev_ditto/pics/methods/ditto_<scale>_NN.png and negatives_hit.png."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import plate_img
DD = os.path.normpath(os.path.join(HERE, '..')); OUT = os.path.join(DD, 'pics', 'methods'); os.makedirs(OUT, exist_ok=True)
COL = {1: (170, 170, 170), 2: (220, 0, 220), 3: (255, 120, 0), 4: (0, 200, 230), 5: (0, 150, 0)}


def panel(P, kind, base):
    o = (base.astype(np.float32) * 0.25 + 255 * 0.75).astype(np.uint8)
    if kind == 'bin8':
        o[(P > 0) & (P != 8)] = (170, 170, 170); o[P == 8] = (0, 0, 230)
    else:
        for v, c in COL.items(): o[P == v] = c
    return o


def cell(TD, r, crops, k=5, pad=8):
    c = crops[r['crop']]; X0, Y0, X1, Y1 = c['win']; a0, b0, a1, b1 = r['aabb']
    x0, y0, x1, y1 = max(X0, a0 - pad), max(Y0, b0 - pad), min(X1, a1 + pad + 1), min(Y1, b1 + pad + 1)
    S = plate_img(c['plate'])[y0:y1, x0:x1]; ps = [S]
    for m in ('finder3', 'finder2', 'bin8'):
        P = cv2.imread(os.path.join(DD, 'runs', 'cut', m, f"{r['crop']}.png"), cv2.IMREAD_UNCHANGED)[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0]
        ps.append(panel(P, m, S))
    big = [cv2.resize(p, None, fx=k, fy=k, interpolation=cv2.INTER_NEAREST) for p in ps]
    for b in big[1:]: cv2.rectangle(b, ((a0 - x0) * k - 1, (b0 - y0) * k - 1), ((a1 - x0 + 1) * k, (b1 - y0 + 1) * k), (200, 200, 0), 1)
    row = np.hstack(sum([[b, np.full((b.shape[0], 2, 3), 255, np.uint8)] for b in big], [])[:-1])
    row = cv2.copyMakeBorder(row, 13, 1, 1, 1, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    t = f"{r['id']} {r['style'] or r['neg_type']} {r['px']}px F{r['finder3']} B{r['bin8']}{' U' if r['unsure'] else ''}"
    cv2.putText(row, t, (2, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 0, 0), 1)
    return row


def sheet(cells, name, per=32):
    if not cells: return
    CW = max(x.shape[1] for x in cells); CH = max(x.shape[0] for x in cells); cols = max(1, 1500 // (CW + 4))
    for s in range(0, len(cells), per):
        part = cells[s:s + per]; rows = (len(part) + cols - 1) // cols
        G = np.full((rows * (CH + 4), cols * (CW + 4), 3), 160, np.uint8)
        for i, x in enumerate(part):
            rr, cc = divmod(i, cols); G[rr * (CH + 4):rr * (CH + 4) + x.shape[0], cc * (CW + 4):cc * (CW + 4) + x.shape[1]] = x
        f = os.path.join(OUT, f'{name}_{s // per + 1:02d}.png'); cv2.imwrite(f, G); print(f, G.shape)


def main():
    S = json.load(open(os.path.join(DD, 'scores', 'summary.json')))
    TD = os.path.join(DD, 'truth'); crops = json.load(open(os.path.join(TD, 'crops.json')))
    for sc in (100, 200, 400):
        rows = [r for r in S['per_word'] if r['scale'] == sc]
        sheet([cell(TD, r, crops) for r in rows], f'ditto_{sc}ft')
    ND = os.path.join(DD, 'negatives'); nc = json.load(open(os.path.join(ND, 'crops.json')))
    hit = [r for r in S['per_negative'] if r['finder3'] or r['bin8'] or r['finder2']]
    sheet([cell(ND, r, nc) for r in hit], 'negatives_hit')
    sheet([cell(ND, r, nc) for r in S['per_negative'][:16]], 'negatives_sample', per=16)


if __name__ == '__main__':
    main()
