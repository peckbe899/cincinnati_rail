"""Debug picture of blockfix's figure ink and line cores on a dev crop (crop of the plate +150 px, fresh proposals).
    python -B .../scripts/debug_fig.py OUT.png MODEL_FOLD TMPL_NAME DB## [DB## ...] [--opt k=v]
Panels: scan | figure ink G (red) and line cores (blue), segments (green) | new codes."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import numpy as np, cv2
import bfcommon as C, blockfix as B

a = sys.argv[1:]; opts = {}
if '--opt' in a:
    i = a.index('--opt')
    for kv in a[i + 1].split(','):
        k, v = kv.split('='); opts[k] = (v in ('1', 'True', 'true')) if isinstance(B.P[k], bool) else type(B.P[k])(v)
    a = a[:i] + a[i + 2:]
out, mf, tn, ids = a[0], a[1], a[2], a[3:]
crops = C.dev_crops(); rows = []
CC = {0: (255, 255, 255), 1: (150, 150, 150), 2: (220, 0, 220), 3: (255, 120, 0), 4: (0, 200, 230), 5: (0, 160, 0)}
for tid in ids:
    c = crops[tid]; N = c['plate']; x0, y0, x1, y1 = c['win']; g = 150
    codes = cv2.imread(C.f3_path(N), 0); im = cv2.imread(f'cufp/22-{N}.jpg')
    X0, Y0 = max(0, x0 - g), max(0, y0 - g); X1, Y1 = x1 + g, y1 + g
    cc = codes[Y0:Y1, X0:X1].copy(); p = dict(B.P, **opts)
    KN = B.Kern(B.load_templates(os.path.join(B.MOD, f'tmpl_{tn}.npz')), p); M = B.load_model(os.path.join(B.MOD, f'cls_{mf}.npz'))
    K, I, nums, rej, props, figs, cnt, T = B.recognise(cc, p, KN, M)
    new = B.apply(N, cc, None, None, tmpl=os.path.join(B.MOD, f'tmpl_{tn}.npz'), model=os.path.join(B.MOD, f'cls_{mf}.npz'), **opts)
    dbg = np.full(cc.shape + (3,), 255, np.uint8); dbg[cc > 0] = (190, 190, 190)
    for n in nums:
        for f in n['figs']:
            G, gx, gy = B.figure_ink(f, K, I, KN, p); Lc, (LX, LY), used = B.line_core(G, gx, gy, I, p)
            h, w = G.shape; sub = dbg[gy:gy + h, gx:gx + w]; sub[G] = (0, 0, 230)
            ys, xs = np.nonzero(Lc); dbg[ys + LY, xs + LX] = (230, 80, 0)
            for u in used:
                for s in u['segs']: cv2.line(dbg, (s[0], s[1]), (s[2], s[3]), (0, 170, 0), 1)
            k = KN.get(f['d'], f['h']); cv2.rectangle(dbg, (f['kx'], f['ky']), (f['kx'] + k['kw'], f['ky'] + k['kh']), (0, 120, 255), 1)
        print(tid, n['reading'], [(f['d'], f['s'], f['p'], f['h']) for f in n['figs']])
    for r in rej:
        if r['box'][0] < x1 - X0 and r['box'][2] > x0 - X0 and r['box'][1] < y1 - Y0 and r['box'][3] > y0 - Y0: print(tid, 'rejected', r['reading'], r['why_not'])
    cn = np.zeros(cc.shape + (3,), np.uint8)
    for v, col in CC.items(): cn[new == v] = col
    sl = (slice(y0 - Y0, y1 - Y0), slice(x0 - X0, x1 - X0))
    row = np.concatenate([im[y0:y1, x0:x1], dbg[sl], cn[sl]], 1); rows.append(cv2.resize(row, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST))
Wm = max(r.shape[1] for r in rows)
cv2.imwrite(out, np.concatenate([cv2.copyMakeBorder(r, 0, 6, 0, Wm - r.shape[1], cv2.BORDER_CONSTANT, value=(0, 0, 0)) for r in rows], 0))
