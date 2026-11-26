"""finder2 look sheets (25 Nov 2026): for each plate, 3 windows of 600 x 400 px at 1:1, picked at random (seed 7) among the
windows with more ink than the plate's median, never inside a truth crop T1-T7; scan beside finder2's codes (line grey,
text sure magenta, text by context blue, shared yellow, other green). For looking only; nothing is tuned on these.
    cd data/sanborn; python -B <this> MASK_PATTERN OUTDIR N [N ...]"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); TRUTH = os.path.normpath(os.path.join(HERE, '..', '..', 'truth'))
COL = {1: (150, 150, 150), 2: (220, 0, 220), 3: (255, 120, 0), 4: (0, 200, 230), 5: (0, 160, 0)}
pat, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True); crops = json.load(open(os.path.join(TRUTH, 'crops.json')))
picked = {}
for N in sys.argv[3:]:
    code = cv2.imread(pat.replace('{plate}', N), 0); im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = code.shape; w, h = 600, 400
    cand = [(x, y) for y in range(0, H - h, 200) for x in range(0, W - w, 200)]
    dens = np.array([(code[y:y + h, x:x + w] > 0).mean() for x, y in cand]); ok = [c for c, d in zip(cand, dens) if d > np.median(dens)]
    tw = [c['win'] for c in crops.values() if c['plate'] == N]
    ok = [(x, y) for x, y in ok if not any(x < X1 and x + w > X0 and y < Y1 and y + h > Y0 for X0, Y0, X1, Y1 in tw)]
    rng = np.random.default_rng(7); sel = [ok[i] for i in rng.choice(len(ok), 3, replace=False)]; picked[N] = [[x, y, x + w, y + h] for x, y in sel]
    rows = []
    for x, y in sel:
        a = im[y:y + h, x:x + w]; c = code[y:y + h, x:x + w]; o = (a * 0.3 + 255 * 0.7).astype(np.uint8)
        for v, col in COL.items(): o[c == v] = col
        r = np.concatenate([a, np.zeros((h, 4, 3), np.uint8), o], 1); cv2.putText(r, f'{N} {x},{y}', (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1); rows.append(r)
    for i, r in enumerate(rows): cv2.imwrite(os.path.join(out, f'look_{N}_{i}.png'), r)
json.dump(picked, open(os.path.join(out, 'look_windows.json'), 'w'), indent=1); print(picked)
