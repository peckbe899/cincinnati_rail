# read-only: area_ng1 uncertainty per processed plate (single pass, the saved PNGs), and on 44 how much of the error it finds
import cv2, numpy as np, glob, os, json
SP = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
OUT = r'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/research-training/'
tint = {r['plate']: r['tinted_share'] for r in json.load(open(OUT + 'b_colour.json'))}
lab = cv2.imread(U + '44_label.png', 0); p = cv2.imread(U + '44_pred_area_ng1.png', 0).astype(np.float32) / 255; ok = lab != 255
err = ((p > 0.5) != (lab == 1)) & ok
for lo, hi in ((0.1, 0.9), (0.2, 0.8)):
    u = (p > lo) & (p < hi) & ok; print(f'44 single pass, p in ({lo},{hi}): {u.sum() / ok.sum():.3f} of ground, holds {err[u].sum() / err.sum():.3f} of errors')
rows = []
for f in sorted(glob.glob(U + '*_pred_area_ng1.png')):
    N = os.path.basename(f).split('_')[0]; q = cv2.imread(f, 0).astype(np.float32) / 255; h, w = q.shape
    a = SP + f'cufp/{N}/png_alpha_s4.npy'; al = cv2.resize(np.load(a).astype(np.float32), (w, h)) > 0.5 if os.path.exists(a) else np.ones_like(q, bool)
    al = cv2.erode(al.astype(np.uint8), np.ones((41, 41), np.uint8)) > 0
    rows.append((round(float(((q > 0.1) & (q < 0.9))[al].mean()), 3), N, tint.get(N), round(float((q > 0.5)[al].mean()), 2)))
rows.sort(reverse=True)
print('plate ranking by unsure share (p in 0.1-0.9, paper interior) [unsure, plate, tint, block share]:')
for r in rows: print('  ', r)
x = np.array([r[0] for r in rows if r[2] is not None]); y = np.array([r[2] for r in rows if r[2] is not None])
print('Pearson r(unsure, tint) =', round(float(np.corrcoef(x, y)[0, 1]), 3), 'n =', len(x))
