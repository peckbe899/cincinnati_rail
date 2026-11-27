"""Random sample of blockfix's changes on a whole plate, at 1:1, for checking by eye.
    python -B .../scripts/sample_sheet.py RUN_DIR BASE_DIR N K SEED OUT.png
Each tile (160 x 160 px of the plate, 1:1): scan | changes: red = ink made text, yellow = ink made shared (4),
pink = finder3's text already, grey = other ink. Numbered in the sample's order; the list goes to OUT.json."""
import sys, os, json, random
import numpy as np, cv2
rd, bd, N, K, seed, out = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
T = json.load(open(os.path.join(rd, f'{N}_text.json'))); ch = [c for c in T['changes'] if c['to_text'] + c['to_shared'] > 0]
idx = list(range(len(ch))); random.Random(seed).shuffle(idx); idx = idx[:K]
im = cv2.imread(f'cufp/22-{N}.jpg'); b0 = cv2.imread(os.path.join(bd, f'{N}_text.png'), 0); b1 = cv2.imread(os.path.join(rd, f'{N}_text.png'), 0)
tiles = []; lst = []
for k, i in enumerate(idx):
    c = ch[i]; bx = [int(v) for v in c['box']]; cx, cy = (bx[0] + bx[2]) // 2, (bx[1] + bx[3]) // 2; X0, Y0 = max(0, cx - 80), max(0, cy - 80)
    s = im[Y0:Y0 + 160, X0:X0 + 160]; a0 = b0[Y0:Y0 + 160, X0:X0 + 160]; a1 = b1[Y0:Y0 + 160, X0:X0 + 160]
    o = np.full(s.shape, 255, np.uint8); o[a1 > 0] = (190, 190, 190); o[np.isin(a0, (2, 3))] = (215, 170, 235)
    d = a0 != a1; o[d & (a1 == 2)] = (0, 0, 255); o[d & (a1 == 4)] = (0, 200, 230)
    t = np.concatenate([s, np.full((s.shape[0], 3, 3), 0, np.uint8), o], 1)
    cv2.putText(t, f"{k + 1}: {c['reading']} +{c['to_text']}", (3, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 220), 1)
    tiles.append(cv2.copyMakeBorder(t, 0, 160 - t.shape[0], 0, 323 - t.shape[1], cv2.BORDER_CONSTANT, value=(0, 0, 0)))
    lst.append(dict(n=k + 1, reading=c['reading'], box=bx, to_text=c['to_text'], to_shared=c['to_shared']))
cols = 3; rows = (len(tiles) + cols - 1) // cols; S = np.zeros((rows * 163, cols * 326, 3), np.uint8)
for i, t in enumerate(tiles): r_, c_ = divmod(i, cols); S[r_ * 163:r_ * 163 + 160, c_ * 326:c_ * 326 + 323] = t
cv2.imwrite(out, S); json.dump(dict(plate=N, changed_numbers=len(ch), sample=lst, seed=seed), open(out[:-4] + '.json', 'w'), indent=1)
print(N, 'numbers with changes', len(ch), 'sampled', len(lst))
