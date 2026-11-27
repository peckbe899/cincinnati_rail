"""Dev pictures (fix_block_a): scan | codes A | codes B [| truth] for dev crops, zoomed.
    cd data/sanborn; python -B .../code/viz.py OUT.png ZOOM CROPID[,CROPID..] PATTERN_A [PATTERN_B] [--truth DIR]
Codes colours: 1 grey, 2 magenta, 3 blue, 4 yellow, 5 green; truth: 2 magenta, 1 grey, 3 cyan. Dev only."""
import json, os, sys
import numpy as np, cv2
sys.dont_write_bytecode = True
COL = {1: (150, 150, 150), 2: (220, 0, 220), 3: (255, 120, 0), 4: (0, 200, 230), 5: (0, 160, 0)}
TCOL = {1: (150, 150, 150), 2: (220, 0, 220), 3: (230, 220, 0)}
CACHE = {}


def plate_img(p):
    if p not in CACHE: CACHE[p] = cv2.imread(f'cufp/22-{p}.jpg')
    return CACHE[p]


def mask(pat, p, cid, win):
    k = pat.replace('{plate}', p).replace('{crop}', cid or '')
    if k not in CACHE: CACHE[k] = cv2.imread(k, cv2.IMREAD_UNCHANGED)
    m = CACHE[k]; x0, y0, x1, y1 = win
    return m if m.shape == (y1 - y0, x1 - x0) else m[y0:y1, x0:x1]


def paint(base, code, cols):
    o = (base * 0.25 + 255 * 0.75).astype(np.uint8)
    for v, c in cols.items(): o[code == v] = c
    return o


def panel(plate, win, pats, truth=None, z=3, label='', cid=None):
    x0, y0, x1, y1 = win; im = plate_img(plate)[y0:y1, x0:x1]
    ps = [im] + [paint(im, mask(p, plate, cid, win), COL) for p in pats]
    if truth is not None: ps.append(paint(im, truth, TCOL))
    r = np.concatenate([np.pad(p, ((0, 0), (0, 4), (0, 0)), constant_values=255) for p in ps], 1)
    r = cv2.resize(r, None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
    r = np.pad(r, ((18, 4), (0, 0), (0, 0)), constant_values=255); cv2.putText(r, label, (3, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    return r


def stack(rows):
    W = max(r.shape[1] for r in rows)
    return np.concatenate([np.pad(r, ((0, 0), (0, W - r.shape[1]), (0, 0)), constant_values=255) for r in rows], 0)


if __name__ == '__main__':
    a = sys.argv; out, z, ids = a[1], float(a[2]), a[3].split(',')
    td = a[a.index('--truth') + 1] if '--truth' in a else None
    pats = [x for x in a[4:] if not x.startswith('--') and x != td]
    crops = json.load(open(os.path.join(td, 'crops.json')))
    rows = []
    for cid in ids:
        c = crops[cid]; tr = cv2.imread(os.path.join(td, f'{cid}_mask.png'), 0)
        rows.append(panel(c['plate'], c['win'], pats, tr, z, f"{cid} plate {c['plate']} {c.get('scale_ft_per_inch','')} {c['win']}", cid))
    cv2.imwrite(out, stack(rows))
