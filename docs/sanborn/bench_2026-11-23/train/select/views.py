"""Selection agent (23 Nov 2026): contact sheets of the merged step's overlays, to look at every candidate by eye.

    python -B views.py sheets            -> views/sheet_XX.jpg (2 x 2 panels, 4 plates each), views/index.json
    python -B views.py one N [N ...]     -> views/one_N.jpg: the overlay with the blocks tinted, and beside it the
                                            confident area pseudo label (green block, red street, grey unsure)

Each panel is unet_data/N_outlines.jpg (half size: the merged step's sides, green on print, red not on a line, orange
unsettled, magenta on rail, grey paper edge) with each block of picks22_guided/22-N/outlines.json filled in its own
colour, so a merged block shows as one colour across several printed blocks. Read-only on the repo.
"""
import json, os, sys
import numpy as np
import cv2

SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'views'); os.makedirs(OUT, exist_ok=True)


def panel(N, width):
    vis = cv2.imread(U + f'{N}_outlines.jpg'); h, w = vis.shape[:2]
    polys = json.load(open(SP + f'picks22_guided/22-{N}/outlines.json', encoding='utf8'))
    ov = vis.copy(); rng = np.random.default_rng(7)
    for poly in polys:
        if poly[0].get('hole'): continue
        pts = (np.array([s['a'] for s in poly], float) * 0.5).round().astype(np.int32)
        cv2.fillPoly(ov, [pts], tuple(int(v) for v in rng.integers(40, 255, 3)))
    for poly in polys:
        if poly[0].get('hole'):
            pts = (np.array([s['a'] for s in poly], float) * 0.5).round().astype(np.int32); cv2.fillPoly(ov, [pts], (255, 255, 255))
    vis = cv2.addWeighted(vis, 0.6, ov, 0.4, 0)
    s = width / w; vis = cv2.resize(vis, (width, int(h * s)), interpolation=cv2.INTER_AREA)
    cv2.rectangle(vis, (0, 0), (150, 46), (255, 255, 255), -1); cv2.putText(vis, N, (6, 38), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 3, cv2.LINE_AA)
    return vis


def pseudo(N, width):
    pa = cv2.imread(U + f'{N}_pred_area_ng1.png', 0); h, w = pa.shape
    a4 = np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.uint8); paper = cv2.resize(a4, (w, h), interpolation=cv2.INTER_NEAREST) > 0
    img = np.full((h, w, 3), 245, np.uint8); img[paper] = (170, 170, 170)
    img[paper & (pa >= 243)] = (60, 170, 60); img[paper & (pa <= 12)] = (40, 40, 220)
    s = width / w; return cv2.resize(img, (width, int(h * s)), interpolation=cv2.INTER_AREA)


def sheet(plates, name, cols=2, width=780):
    ps = [panel(N, width) for N in plates]; hmax = max(p.shape[0] for p in ps)
    ps = [cv2.copyMakeBorder(p, 0, hmax - p.shape[0] + 6, 0, 6, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for p in ps]
    while len(ps) % cols: ps.append(np.full_like(ps[0], 255))
    rows = [np.hstack(ps[i:i + cols]) for i in range(0, len(ps), cols)]
    cv2.imwrite(os.path.join(OUT, name), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])


if __name__ == '__main__':
    if sys.argv[1] == 'sheets':
        R = json.load(open(os.path.join(os.path.dirname(OUT), 'plates.json'), encoding='utf8'))
        skip = {'43', '44', '45', '80', '82A'}
        order = sorted([r for r in R if r['plate'] not in skip], key=lambda r: (r['ft_per_inch'], r['source'], r['plate']))
        idx = {}; k = 0
        for g in [order[i:i + 4] for i in range(0, len(order), 4)]:
            k += 1; nm = f'sheet_{k:02d}.jpg'; sheet([r['plate'] for r in g], nm); idx[nm] = [r['plate'] for r in g]; print(nm, idx[nm], flush=True)
        json.dump(idx, open(os.path.join(OUT, 'index.json'), 'w', encoding='utf8', newline='\n'), indent=1)
    else:
        for N in sys.argv[2:]:
            a, b = panel(N, 1100), pseudo(N, 1100); hm = max(a.shape[0], b.shape[0])
            a = cv2.copyMakeBorder(a, 0, hm - a.shape[0], 0, 8, cv2.BORDER_CONSTANT, value=(255, 255, 255)); b = cv2.copyMakeBorder(b, 0, hm - b.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            cv2.imwrite(os.path.join(OUT, f'one_{N}.jpg'), np.hstack([a, b]), [cv2.IMWRITE_JPEG_QUALITY, 85]); print('one', N, flush=True)
