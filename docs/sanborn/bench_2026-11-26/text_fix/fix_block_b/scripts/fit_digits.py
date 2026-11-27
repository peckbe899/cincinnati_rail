"""More real figures for training: survey numbers that extract_digits.py could not cut apart (crossed by or joined to
lines and walls, figures merged), placed by fitting the known reading's digit models in a row near the survey point.
    python -B .../scripts/fit_digits.py TMPL_NAME OUT.npy [plates...]
Skips candidates inside a dev truth window (grown 60 px) or an H window (grown 50 px), as extract_digits.py does.
A number is kept when every figure's normalised correlation (thick ink, as blockfix) is >= 0.5 and their mean >= 0.6,
the figures stand in a row (same height, gap -0.1 to 0.5 h, same baseline +-0.12 h). Reads no truth mask."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import numpy as np, cv2
import bfcommon as C, blockfix as B

tn, out = sys.argv[1], sys.argv[2]; plates = sys.argv[3:] or C.FOLD['A'] + C.FOLD['B']
crops = C.dev_crops(); p = dict(B.P); KN = B.Kern(B.load_templates(os.path.join(B.MOD, f'tmpl_{tn}.npz')), p)
log = json.load(open(os.path.join(B.MOD, 'real_digits_log.json')))
done = {(l[0], l[1], l[2]) for l in log if l[4] == 'ok'}
HS = [44, 47, 50, 53, 56, 60, 64, 68, 72]
rec = []
for N in plates:
    codes = cv2.imread(C.f3_path(N), 0); I = (codes > 0).astype(np.uint8); K = B.thick(I, 5).astype(np.float32); H, W = K.shape
    wins = [c['win'] for c in crops.values() if c['plate'] == N]; fold = 'A' if N in C.FOLD['A'] else 'B'; nk = 0
    for x, y, r, note in C.candidates(N):
        if (N, x, y) in done: continue
        b = (x - 130, y - 110, x + 130, y + 110)
        if C.in_hwin(N, b, 50) or any(b[0] < w[2] + 60 and b[2] > w[0] - 60 and b[1] < w[3] + 60 and b[3] > w[1] - 60 for w in wins): continue
        if not r.isdigit() or len(r) > 3: continue
        X0, Y0, X1, Y1 = max(0, x - 160), max(0, y - 130), min(W, x + 160), min(H, y + 130)
        win = K[Y0:Y1, X0:X1]; best = None
        for h in HS:
            maps = []
            for d in r:
                k = KN.get(d, h)
                if k['kh'] >= win.shape[0] or k['kw'] >= win.shape[1]: maps = None; break
                R = cv2.matchTemplate(win, k['w'], cv2.TM_CCOEFF_NORMED); maps.append((R, k))
            if not maps: continue
            R0, k0 = maps[0]
            # top peaks of the first figure near the survey point
            Rm = R0.copy(); cand = []
            for _ in range(6):
                _, s, _, (bx, by) = cv2.minMaxLoc(Rm)
                if s < 0.45: break
                cand.append((s, bx, by)); cv2.rectangle(Rm, (bx - 6, by - 6), (bx + 6, by + 6), -1, -1)
            for s0, bx, by in cand:
                cx0, cy0 = X0 + bx + k0['ox'], Y0 + by + k0['oy']
                if abs(cx0 - x) > 110 or abs(cy0 - y) > 80: continue
                figs = [(r[0], s0, cx0, cy0)]; ok = True; right = cx0 + k0['ww'] / 2
                for (R, k), d in zip(maps[1:], r[1:]):
                    # next figure: its box starts -0.1 h to 0.5 h after the last one ends, same centre line +-0.12 h
                    xa = right - 0.1 * h + k['ww'] / 2; xb = right + 0.5 * h + k['ww'] / 2
                    ia, ib = int(xa - X0 - k['ox']), int(xb - X0 - k['ox']) + 1; ja, jb = int(cy0 - 0.12 * h - Y0 - k['oy']), int(cy0 + 0.12 * h - Y0 - k['oy']) + 1
                    ia, ja = max(0, ia), max(0, ja); ib, jb = min(R.shape[1], ib), min(R.shape[0], jb)
                    if ia >= ib or ja >= jb: ok = False; break
                    sub = R[ja:jb, ia:ib]; j, i = np.unravel_index(np.argmax(sub), sub.shape); s = float(sub[j, i])
                    cx, cy = X0 + ia + i + k['ox'], Y0 + ja + j + k['oy']; figs.append((d, s, cx, cy)); right = cx + k['ww'] / 2
                if not ok: continue
                sc = [f[1] for f in figs]
                if min(sc) >= 0.5 and np.mean(sc) >= 0.6 and (best is None or np.mean(sc) > best[0]): best = (float(np.mean(sc)), h, figs)
        if best:
            nk += 1
            for d, s, cx, cy in best[2]:
                rec.append(dict(plate=N, fold=fold, digit=d, reading=r, cx=float(cx), cy=float(cy), h=best[1], s=s, src='fit'))
    print(N, 'numbers fitted', nk, flush=True)
np.save(out, np.array(rec, dtype=object), allow_pickle=True)
from collections import Counter
print(len(rec), Counter(q['digit'] for q in rec))
