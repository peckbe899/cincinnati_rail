"""review-labels, 24 Nov 2026: pictures of training labels (read only; writes only into review-labels/).

    python -B viz.py over  DIR N OUT.jpg [--sm STREETMAP.json] [--scale 0.25]
        the whole plate: block label green, street label blue, untaught none; with --sm, Ben's lines yellow and the
        label's errors against score_pseudo.py's truth (block on Ben's street red, street on Ben's block magenta)
    python -B viz.py crop  DIR N X0 Y0 X1 Y1 OUT.jpg [--sm STREETMAP.json]
        a full-resolution crop (box in full px), two panels: left the area label (block green, street blue, 255 none,
        edge.png white); right the line target (1 red, 0 cyan tint, 255 none); Ben's lines thin yellow with --sm
    python -B viz.py crops DIR N OUTPREFIX K [--seed S] [--sm ...]   K crops: random boxes with taught ground, 1200 x 900 full px
"""
import json, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'


def arg(k, d=None):
    return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d


def scan(N):
    f = SP + f'cufp/22-{N}.jpg'; return cv2.imread(f)


def ben_lines(sm, img, scale, ox=0, oy=0, col=(0, 230, 255), th=1):
    if sm is None: return
    for l in sm['lines']:
        a = (np.array(l['a']) - (ox, oy)) * scale; b = (np.array(l['b']) - (ox, oy)) * scale
        c = col if l['kind'] in ('printed', 'drawn') else (0, 140, 255)
        cv2.line(img, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), c, th, cv2.LINE_AA)


def tint(img, m, col, a):
    img[m] = (img[m] * (1 - a) + np.array(col, float) * a).astype(np.uint8)


def over(d, N, out, sm, sc):
    full = scan(N); H, W = full.shape[:2]; w, h = int(W * sc), int(H * sc)
    im = cv2.resize(full, (w, h), interpolation=cv2.INTER_AREA); del full
    lab = cv2.resize(cv2.imread(f'{d}/{N}/label.png', cv2.IMREAD_UNCHANGED), (w, h), interpolation=cv2.INTER_NEAREST)
    tint(im, lab == 1, (60, 200, 60), 0.35); tint(im, lab == 0, (230, 120, 30), 0.35)
    if sm is not None:
        import score_pseudo as S
        L = cv2.imread(f'{d}/{N}/label.png', cv2.IMREAD_UNCHANGED); hh, ww = L.shape; T = S.truth(N, sm, hh, ww, sm.get('ft_per_inch', 100))
        e1 = cv2.resize(((L == 1) & T['S'] & ~T['band']).astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0
        e2 = cv2.resize(((L == 0) & T['B'] & ~T['band']).astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0
        im[e1] = (0, 0, 255); im[e2] = (255, 0, 255)
        ben_lines(sm, im, sc)
    cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 88])


def crop(d, N, box, out, sm, full=None):
    x0, y0, x1, y1 = box; full = scan(N) if full is None else full
    a = full[y0:y1, x0:x1].copy(); b = a.copy()
    lab = cv2.imread(f'{d}/{N}/label.png', cv2.IMREAD_UNCHANGED); edge = cv2.imread(f'{d}/{N}/edge.png', 0)
    lf = cv2.resize(lab[y0 // 2:(y1 + 1) // 2 + 1, x0 // 2:(x1 + 1) // 2 + 1], None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)[y0 % 2:y0 % 2 + (y1 - y0), x0 % 2:x0 % 2 + (x1 - x0)]
    tint(a, lf == 1, (60, 200, 60), 0.35); tint(a, lf == 0, (230, 120, 30), 0.40)
    if edge is not None:
        ef = cv2.resize(edge[y0 // 2:(y1 + 1) // 2 + 1, x0 // 2:(x1 + 1) // 2 + 1], None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)[y0 % 2:y0 % 2 + (y1 - y0), x0 % 2:x0 % 2 + (x1 - x0)]
        a[ef > 0] = (255, 255, 255)
    t = cv2.imread(f'{d}/{N}/lines.png', cv2.IMREAD_UNCHANGED)[y0:y1, x0:x1]
    tint(b, t == 0, (230, 200, 0), 0.30); b[t == 1] = (0, 0, 255)
    ben_lines(sm, b, 1.0, x0, y0)
    for p, s in ((a, 'area label: block green, street blue, edge white'), (b, 'lines: 1 red, 0 cyan, 255 none' + (', Ben yellow' if sm else ''))):
        cv2.rectangle(p, (0, 0), (p.shape[1], 22), (255, 255, 255), -1); cv2.putText(p, f'{N} [{x0},{y0},{x1},{y1}] {s}', (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    sep = np.full((a.shape[0], 6, 3), 255, np.uint8)
    cv2.imwrite(out, np.hstack([a, sep, b]), [cv2.IMWRITE_JPEG_QUALITY, 90])


def crops(d, N, pre, k, seed, sm, cw=900, ch=700):
    full = scan(N); H, W = full.shape[:2]; lab = cv2.imread(f'{d}/{N}/label.png', cv2.IMREAD_UNCHANGED); t = cv2.imread(f'{d}/{N}/lines.png', cv2.IMREAD_UNCHANGED)
    rng = np.random.default_rng(seed); boxes = []
    while len(boxes) < k:
        x0 = int(rng.integers(0, W - cw)); y0 = int(rng.integers(0, H - ch))
        if (lab[y0 // 2:(y0 + ch) // 2, x0 // 2:(x0 + cw) // 2] != 255).mean() < 0.3: continue
        if (t[y0:y0 + ch, x0:x0 + cw] == 1).sum() < 2000: continue
        if any(abs(x0 - b[0]) < cw and abs(y0 - b[1]) < ch for b in boxes): continue
        boxes.append((x0, y0, x0 + cw, y0 + ch))
    for i, b in enumerate(boxes): crop(d, N, b, f'{pre}_{i}.jpg', sm, full)
    print(N, boxes)


if __name__ == '__main__':
    m = sys.argv[1]; smf = arg('--sm'); sm = json.load(open(smf, encoding='utf8')) if smf else None
    if m == 'over': over(sys.argv[2], sys.argv[3], sys.argv[4], sm, float(arg('--scale', 0.25)))
    elif m == 'crop': crop(sys.argv[2], sys.argv[3], [int(v) for v in sys.argv[4:8]], sys.argv[8], sm)
    else: crops(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), int(arg('--seed', 1)), sm)
