"""CHECK ONLY (integrate, 26 Nov 2026): a contact sheet of changes drawn at random, for a look by eye.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/integrate/code/sheet.py N BASE.png NEW.png OUT.png [--n 30] [--seed S] [--z 2]
           [--half 64] [--boxes BOXES.json] [--kind block|ditto|all]

Changes = pixels whose code differs between BASE and NEW, grouped into words (8-connected after growing 8 px). A word is
'ditto' when every changed px went 5 -> 3 (only the ditto step does that), else 'block'. --boxes: draw from these boxes
instead ([[x0, y0, x1, y1], ...] in plate px). Each tile: scan | BASE codes | NEW codes (changed px red), full
resolution, drawn z times (nearest neighbour, so every scan pixel shows). Words inside the old held-out windows H1-H4 are
never drawn. Writes OUT.png and OUT.json (the drawn words: box, px, kind, transitions).
"""
import json, os, sys, random
sys.dont_write_bytecode = True
import numpy as np, cv2
HWIN = {'90': [(5640, 3950, 7140, 4950), (880, 2100, 2380, 3100)], '47': [(7040, 4560, 8540, 5560)], '54A': [(7190, 3950, 8690, 4950)]}
SEALED = {'6', '9', '52', '56', '58', '63', '35', '38', '41', '66', '71', '76', '84', '88', '46', '92'}
COL = {1: (150, 150, 150), 2: (220, 0, 220), 3: (255, 120, 0), 4: (0, 200, 230), 5: (0, 150, 0)}


def arg(a, k, d, t=str): return t(a[a.index(k) + 1]) if k in a else d


def main():
    a = sys.argv; N, bp, np_, outp = a[1:5]
    if N in SEALED: raise SystemExit('sealed')
    n = arg(a, '--n', 30, int); seed = arg(a, '--seed', f'sheet-{N}'); z = arg(a, '--z', 2, int); half = arg(a, '--half', 64, int); kind = arg(a, '--kind', 'all')
    B = cv2.imread(bp, cv2.IMREAD_UNCHANGED); C = cv2.imread(np_, cv2.IMREAD_UNCHANGED); H, W = B.shape
    d = (B != C)
    if '--boxes' in a:
        boxes = json.load(open(arg(a, '--boxes', None))); words = []
        for b in boxes:
            x0, y0, x1, y1 = (int(round(v)) for v in b[:4]); sub = d[max(0, y0 - 8):y1 + 8, max(0, x0 - 8):x1 + 8]
            words.append(dict(box=[x0, y0, x1, y1], px=int(sub.sum())))
    else:
        g = cv2.dilate(d.astype(np.uint8), np.ones((17, 17), np.uint8))
        k, lb, st, _ = cv2.connectedComponentsWithStats(g, connectivity=8); words = []
        for i in range(1, k):
            x, y, w, h, _ = (int(v) for v in st[i]); sub = (lb[y:y + h, x:x + w] == i) & d[y:y + h, x:x + w]
            bs, cs = B[y:y + h, x:x + w][sub], C[y:y + h, x:x + w][sub]
            tr = {}
            for u, v in zip(bs.tolist(), cs.tolist()): tr[f'{u}>{v}'] = tr.get(f'{u}>{v}', 0) + 1
            kd = 'ditto' if set(tr) == {'5>3'} else 'block'
            words.append(dict(box=[x + 8, y + 8, x + w - 8, y + h - 8], px=int(sub.sum()), kind=kd, tr=tr))
        if kind != 'all': words = [w for w in words if w['kind'] == kind]
    def inH(b): return any(b[0] < q[2] + half and q[0] - half < b[2] and b[1] < q[3] + half and q[1] - half < b[3] for q in HWIN.get(N, []))
    words = [w for w in words if not inH(w['box'])]
    random.Random(seed).shuffle(words); pick = words[:n]
    im = cv2.imread(f'cufp/22-{N}.jpg'); tiles = []
    for j, w in enumerate(pick):
        x0, y0, x1, y1 = w['box']; cx, cy = (x0 + x1) // 2, (y0 + y1) // 2; hs = max(half, (x1 - x0) // 2 + 12, (y1 - y0) // 2 + 12)
        X0, Y0, X1, Y1 = max(0, cx - hs), max(0, cy - hs), min(W, cx + hs), min(H, cy + hs)
        sc = im[Y0:Y1, X0:X1]; pa = []
        for M in (B, C):
            o = np.full_like(sc, 250); cm = M[Y0:Y1, X0:X1]
            for v, c in COL.items(): o[cm == v] = c
            pa.append(o)
        ch = d[Y0:Y1, X0:X1]; pa[1][ch] = (0, 0, 255)
        sep = np.full((sc.shape[0], 3, 3), 60, np.uint8)
        t = np.concatenate([sc, sep, pa[0], sep, pa[1]], 1)
        t = cv2.resize(t, None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
        t = np.concatenate([np.full((16, t.shape[1], 3), 255, np.uint8), t], 0)
        cv2.putText(t, f"#{j} {N} {x0},{y0} px{w['px']} {w.get('kind', '')}", (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
        tiles.append(t); w['i'] = j
    if not tiles: print('no changes'); return
    cols = max(1, min(3, 1800 // max(t.shape[1] for t in tiles)))
    hh = max(t.shape[0] for t in tiles); ww = max(t.shape[1] for t in tiles); rows = (len(tiles) + cols - 1) // cols
    S = np.full((rows * (hh + 6), cols * (ww + 6), 3), 128, np.uint8)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols); S[r * (hh + 6):r * (hh + 6) + t.shape[0], c * (ww + 6):c * (ww + 6) + t.shape[1]] = t
    cv2.imwrite(outp, S)
    json.dump(dict(plate=N, base=bp, new=np_, seed=seed, n_words=len(words), drawn=pick), open(outp[:-4] + '.json', 'w', encoding='utf8', newline='\n'), indent=1)
    print(f'{N}: {len(words)} changed words, {len(pick)} drawn -> {outp}')


if __name__ == '__main__':
    main()
