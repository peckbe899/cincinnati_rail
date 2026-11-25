"""verify (25 Nov 2026): random windows of the finder's output on plates it was NOT tuned on (no truth there), for looking.
Windows are drawn at random (seed 7) among 600 x 400 windows whose ink is 8-30% of the paper (so not blank, not a
solid building); I did not choose them. Left: the scan. Right: finder text magenta, line ink grey, other ink green.

    cd data/sanborn; python -B bench_2026-11-25/text/verify/scripts/unseen_windows.py 90 30 60B 54A 47 93A
Writes verify/pics/unseen_<N>_<x>_<y>.jpg and verify/out/unseen_windows.json."""
import json, os, sys
import numpy as np, cv2
T = os.path.join(os.getcwd(), 'bench_2026-11-25', 'text'); V = os.path.join(T, 'verify'); rng = np.random.default_rng(7)
out = {}
for N in sys.argv[1:]:
    code = cv2.imread(os.path.join(T, 'finder', 'out', f'{N}_finder.png'), 0); im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = code.shape
    ink = (code > 0).astype(np.float32); ii = cv2.integral(ink)
    pick = []
    for _ in range(2000):
        x = int(rng.integers(0, W - 600)); y = int(rng.integers(0, H - 400))
        s = ii[y + 400, x + 600] - ii[y, x + 600] - ii[y + 400, x] + ii[y, x]
        if 0.08 <= s / (600 * 400) <= 0.30: pick.append((x, y))
        if len(pick) == 2: break
    for x, y in pick:
        a = im[y:y + 400, x:x + 600]; c = code[y:y + 400, x:x + 600]
        o = (a.astype(np.float32) * 0.3 + 255 * 0.7).astype(np.uint8)
        o[c == 1] = (150, 150, 150); o[c == 5] = (0, 160, 0); o[np.isin(c, (2, 3, 4))] = (220, 0, 220)
        pic = np.hstack([a, np.full((400, 6, 3), 255, np.uint8), o])
        cv2.putText(pic, f'{N} x{x} y{y}', (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        cv2.imwrite(os.path.join(V, 'pics', f'unseen_{N}_{x}_{y}.jpg'), pic, [cv2.IMWRITE_JPEG_QUALITY, 90])
        out.setdefault(N, []).append([x, y])
    print(N, out.get(N))
json.dump(out, open(os.path.join(V, 'out', 'unseen_windows.json'), 'w'), indent=1)
