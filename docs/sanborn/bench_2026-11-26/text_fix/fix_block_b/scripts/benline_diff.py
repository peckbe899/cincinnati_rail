"""Where a new mask calls Ben's line ink text that finder3 did not (plates 44, 1A, 5; check only, nothing feeds back).
    python -B .../scripts/benline_diff.py BASE_DIR NEW_DIR OUT_STEM N [N ...]
Uses text/finder/scripts/benlines.py (read-only, as finder2/scripts/check_lines_rail.py does). Writes OUT_STEM_N.png:
per blockfix number with new text within 3 px of Ben's lines: scan | red = new text within 1 px, orange = within 3 px,
blue = Ben's line, grey = other ink; and OUT_STEM.json with the counts per number."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import numpy as np, cv2
import bfcommon as C
sys.path.insert(0, os.path.join(C.DS, 'bench_2026-11-25', 'text', 'finder', 'scripts'))
import benlines

bd, nd, stem, plates = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]; rep = {}
for N in plates:
    a = cv2.imread(os.path.join(bd, f'{N}_text.png'), 0); b = cv2.imread(os.path.join(nd, f'{N}_text.png'), 0); H, W = a.shape
    m, _ = benlines.raster(N, W, H); d = cv2.distanceTransform((m == 0).astype(np.uint8), cv2.DIST_L2, 5)
    new = np.isin(b, (2, 3)) & ~np.isin(a, (2, 3)); ink = b > 0
    n1, n3 = new & (d <= 1), new & (d <= 3)
    T = json.load(open(os.path.join(nd, f'{N}_text.json'))); items = []
    for c in T['changes']:
        bx = [int(v) for v in c['box']]; X0, Y0, X1, Y1 = max(0, bx[0] - 8), max(0, bx[1] - 8), min(W, bx[2] + 8), min(H, bx[3] + 8)
        k1, k3 = int(n1[Y0:Y1, X0:X1].sum()), int(n3[Y0:Y1, X0:X1].sum())
        if k3: items.append(dict(reading=c['reading'], box=bx, new_1px=k1, new_3px=k3, to_text=c['to_text']))
    rep[N] = dict(new_text_1px=int(n1.sum()), new_text_3px=int(n3.sum()), numbers=items)
    print(N, 'new text within 1 px of Ben lines', int(n1.sum()), 'within 3 px', int(n3.sum()), 'numbers', len(items))
    im = cv2.imread(f'cufp/22-{N}.jpg'); tiles = []
    for it in sorted(items, key=lambda q: -q['new_3px'])[:30]:
        bx = it['box']; cx, cy = (bx[0] + bx[2]) // 2, (bx[1] + bx[3]) // 2; r = 60; X0, Y0 = max(0, cx - r), max(0, cy - r)
        s = im[Y0:Y0 + 2 * r, X0:X0 + 2 * r]; o = np.full(s.shape, 255, np.uint8); sl = (slice(Y0, Y0 + 2 * r), slice(X0, X0 + 2 * r))
        o[ink[sl]] = (200, 200, 200); o[(m[sl] > 0)] = (255, 150, 0); o[n3[sl]] = (0, 140, 255); o[n1[sl]] = (0, 0, 255)
        t = cv2.resize(np.concatenate([s, o], 1), None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
        cv2.putText(t, f"{N} {it['reading']} 1px {it['new_1px']} 3px {it['new_3px']}", (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 200), 1); tiles.append(t)
    if tiles:
        cols = 3; h, w = tiles[0].shape[:2]; rows = (len(tiles) + cols - 1) // cols; S = np.zeros((rows * (h + 3), cols * (w + 3), 3), np.uint8)
        for i, t in enumerate(tiles): r_, c_ = divmod(i, cols); S[r_ * (h + 3):r_ * (h + 3) + h, c_ * (w + 3):c_ * (w + 3) + w] = t
        cv2.imwrite(f'{stem}_{N}.png', S)
json.dump(rep, open(stem + '.json', 'w'), indent=1)
