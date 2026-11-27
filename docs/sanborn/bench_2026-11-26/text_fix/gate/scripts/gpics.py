"""gpics.py (final gate): zoom pictures of finder4's misses and false text on the sealed set.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/gate/scripts/gpics.py GSCORE.npz BOOT.json OUT_DIR [--a finder3 --b finder4]

Sheets (each tile: scan | truth | finder3 | finder4, at 4-8x):
  truth:   magenta text, grey non-text ink, yellow don't care, white paper.
  finders: magenta text that is right, red text missed, blue non-text ink called text, grey line ink (code 1),
           green other ink (5), cyan shared ink (4); the word box is drawn in black.
  OUT_DIR/miss_block_*.png  every target block number finder4 misses (found < half) or finds only partly (< 0.9)
  OUT_DIR/miss_ditto_*.png  every target ditto mark finder4 misses
  OUT_DIR/fp_top20_*.png    the 20 biggest false-text spots of finder4 over all sealed crops (non-text truth ink
                            called text, grouped within 4 px), with finder3 beside it. fp_top20.json lists them.
"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2

TR = 'bench_2026-11-26/text_fix/sealed_final'
a = sys.argv[1:]; A = a[a.index('--a') + 1] if '--a' in a else 'finder3'; B = a[a.index('--b') + 1] if '--b' in a else 'finder4'
Z = np.load(a[0]); O = json.load(open(a[1], encoding='utf8')); out = a[2]; os.makedirs(out, exist_ok=True)
crops = json.load(open(os.path.join(TR, 'crops.json'), encoding='utf8')); scans = {}


def scan(pl):
    if pl not in scans:
        if len(scans) > 3: scans.clear()
        scans[pl] = cv2.imread(f'cufp/22-{pl}.jpg')
    return scans[pl]


def truth(cid): return cv2.imread(os.path.join(TR, f'{cid}_mask.png'), cv2.IMREAD_UNCHANGED)


def paint_truth(sc, T):
    o = np.full(sc.shape, 255, np.uint8); o[T == 1] = (150, 150, 150); o[T == 2] = (220, 0, 220); o[T == 3] = (0, 220, 255); o[T == 0] = (255, 255, 255)
    o[(T == 3) & (cv2.cvtColor(sc, cv2.COLOR_BGR2GRAY) > 200)] = (230, 250, 255)
    return o


def paint_codes(sc, T, C):
    t = np.isin(C, (2, 3)); o = (sc * 0.25 + 255 * 0.75).astype(np.uint8)
    o[C == 1] = (150, 150, 150); o[C == 5] = (0, 160, 0); o[C == 4] = (230, 200, 0)
    o[t] = (220, 0, 220); o[(T == 2) & ~t] = (0, 0, 255); o[(T == 1) & t] = (255, 80, 0)
    return o


def tile(cid, box, label, pad=18, maxw=1100):
    c = crops[cid]; x0, y0, x1, y1 = c['win']; T = truth(cid)
    bx0, by0, bx1, by1 = box; X0 = max(x0, bx0 - pad); Y0 = max(y0, by0 - pad); X1 = min(x1, bx1 + pad); Y1 = min(y1, by1 + pad)
    sl = (slice(Y0 - y0, Y1 - y0), slice(X0 - x0, X1 - x0)); sc = scan(c['plate'])[Y0:Y1, X0:X1]
    pa = paint_codes(sc, T[sl], Z[f'cut|{A}|{cid}'][sl]); pb = paint_codes(sc, T[sl], Z[f'cut|{B}|{cid}'][sl])
    ps = [sc.copy(), paint_truth(sc, T[sl]), pa, pb]
    for p in ps[1:]: cv2.rectangle(p, (bx0 - X0, by0 - Y0), (bx1 - X0, by1 - Y0), (0, 0, 0), 1)
    sep = np.full((sc.shape[0], 2, 3), 255, np.uint8)
    t = np.concatenate([ps[0], sep, ps[1], sep, ps[2], sep, ps[3]], 1)
    z = int(max(2, min(8, maxw // t.shape[1]))); t = cv2.resize(t, None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
    bar = np.full((18, t.shape[1], 3), 255, np.uint8); cv2.putText(bar, label + f'  (x{z})  scan | truth | {A} | {B}', (3, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
    return np.concatenate([bar, t], 0)


def sheets(tiles, stem, per=4):
    for s in range(0, len(tiles), per):
        part = tiles[s:s + per]; W = max(t.shape[1] for t in part)
        rows = [np.pad(t, ((0, 6), (0, W - t.shape[1]), (0, 0)), constant_values=255) for t in part]
        cv2.imwrite(f'{out}/{stem}_{s // per:02d}.png', np.concatenate(rows, 0))


for kind in ('block', 'ditto'):
    L = O[kind]['missed_by_B'] + (O[kind]['partial_by_B'] if kind == 'block' else [])
    tl = []
    for w in L:
        lab = f"{kind} {w['crop']} {w['id']} '{w['reading']}' plate {w['plate']} {w['ft']} ft: {B} {w['fB']}/{w['n']} px, {A} {w['fA']}/{w['n']}"
        tl.append(tile(w['crop'], w['aabb'], lab, pad=40 if kind == 'block' else 30))
    sheets(tl, f'miss_{kind}', per=3 if kind == 'block' else 4)
    print(kind, len(tl), 'tiles')

# false-text spots
spots = []
for cid, c in crops.items():
    T = truth(cid); C = Z[f'cut|{B}|{cid}']; Ca = Z[f'cut|{A}|{cid}']
    fp = (T == 1) & np.isin(C, (2, 3)); fpa = (T == 1) & np.isin(Ca, (2, 3))
    if not fp.any(): continue
    g = cv2.dilate(fp.astype(np.uint8), np.ones((9, 9), np.uint8))
    n, lb, st, _ = cv2.connectedComponentsWithStats(g, connectivity=8)
    for i in range(1, n):
        m = (lb == i) & fp; k = int(m.sum())
        if not k: continue
        ys, xs = np.nonzero(m); x0, y0 = c['win'][:2]
        spots.append(dict(crop=cid, plate=c['plate'], ft=c['scale_ft_per_inch'], px=k, finder3_same_px=int((m & fpa).sum()),
                          box=[int(xs.min() + x0), int(ys.min() + y0), int(xs.max() + x0 + 1), int(ys.max() + y0 + 1)]))
spots.sort(key=lambda s: -s['px']); top = spots[:20]
json.dump(dict(n_spots=len(spots), total_fp=sum(s['px'] for s in spots), top20=top), open(f'{out}/fp_top20.json', 'w'), indent=1)
tl = [tile(s['crop'], s['box'], f"#{i + 1} {s['crop']} plate {s['plate']} {s['ft']} ft at {s['box'][0]},{s['box'][1]}: {B} fp {s['px']} px, also {A} {s['finder3_same_px']}", pad=30)
      for i, s in enumerate(top)]
sheets(tl, 'fp_top20', per=4)
print('fp spots', len(spots), 'top20 px', [s['px'] for s in top])
