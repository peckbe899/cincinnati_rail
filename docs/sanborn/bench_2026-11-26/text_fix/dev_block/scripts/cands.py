"""Contact sheet of block-number candidates (dev_block, 26 Nov 2026). Scan only.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/dev_block/scripts/cands.py PLATE [--half 200] [--scale 0.5] [--cols 6] [--name X]

Reads dev_block/candidates/PLATE.txt (lines 'x y reading [note]', full-plate px, from the 1/4-size survey) and writes
dev_block/pics/survey/cand_PLATE.jpg: a cell of the scan round each candidate (half-size `half` px), numbered as in the file."""
import os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.normpath(os.path.join(HERE, '..'))
ROOT = os.path.normpath(os.path.join(DB, '..', '..', '..'))
SEALED = set('6 9 52 56 58 63 35 38 41 66 71 76 84 88 46 92'.split())


def opt(n, d):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def read_cands(N):
    out = []
    for s in open(os.path.join(DB, 'candidates', f'{N}.txt'), encoding='utf8'):
        s = s.strip()
        if not s or s.startswith('#'): continue
        f = s.split(); out.append(dict(x=int(f[0]), y=int(f[1]), reading=f[2], note=' '.join(f[3:])))
    return out


if __name__ == '__main__':
    N = sys.argv[1]; assert N not in SEALED
    half = int(opt('--half', '200')); sc = float(opt('--scale', '0.5')); cols = int(opt('--cols', '6'))
    im = cv2.imread(os.path.join(ROOT, 'cufp', f'22-{N}.jpg')); H, W = im.shape[:2]
    C = read_cands(N); cells = []
    for i, c in enumerate(C):
        x0, y0 = max(0, c['x'] - half), max(0, c['y'] - half); x1, y1 = min(W, c['x'] + half), min(H, c['y'] + half)
        cell = np.full((2 * half, 2 * half, 3), 255, np.uint8); cell[y0 - (c['y'] - half):y1 - (c['y'] - half), x0 - (c['x'] - half):x1 - (c['x'] - half)] = im[y0:y1, x0:x1]
        cell = cv2.resize(cell, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
        cell = cv2.copyMakeBorder(cell, 14, 2, 2, 2, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        cv2.putText(cell, f"#{i} {c['reading']} {c['x']},{c['y']}", (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 200), 1)
        cells.append(cell)
    ch, cw = cells[0].shape[:2]; rows = (len(cells) + cols - 1) // cols
    G = np.full((rows * ch, cols * cw, 3), 200, np.uint8)
    for i, c in enumerate(cells):
        r, k = divmod(i, cols); G[r * ch:(r + 1) * ch, k * cw:(k + 1) * cw] = c
    f = os.path.join(DB, 'pics', 'survey', f"cand_{N}{opt('--name', '')}.jpg"); cv2.imwrite(f, G, [cv2.IMWRITE_JPEG_QUALITY, 90]); print(f, G.shape)
