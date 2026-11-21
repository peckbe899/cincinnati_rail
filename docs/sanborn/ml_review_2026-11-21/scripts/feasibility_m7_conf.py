# read-only: share of paper interior that area_ng1 calls with p<0.05 or p>0.95, per plate, against tint
import cv2, numpy as np, glob, os, json
SP = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
RT = r'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/research-training/'
tint = {r['plate']: r['tinted_share'] for r in json.load(open(RT + 'b_colour.json'))}; rows = []
for f in sorted(glob.glob(U + '*_pred_area_ng1.png')):
    N = os.path.basename(f).split('_')[0]; q = cv2.imread(f, 0); h, w = q.shape; a = SP + f'cufp/{N}/png_alpha_s4.npy'
    al = cv2.resize(np.load(a).astype(np.float32), (w, h)) > 0.5 if os.path.exists(a) else np.ones((h, w), bool)
    al = cv2.erode(al.astype(np.uint8), np.ones((41, 41), np.uint8)) > 0; v = q[al]
    rows.append((N, tint.get(N), round(float(((v < 13) | (v > 242)).mean()), 3)))
x = np.array([r[1] for r in rows if r[1] is not None]); y = np.array([r[2] for r in rows if r[1] is not None])
print('n', len(rows), 'r(tint, confident share)', round(float(np.corrcoef(x, y)[0, 1]), 3))
hi = [r for r in rows if r[1] and r[1] > 0.40]; lo = [r for r in rows if r[1] and r[1] <= 0.26]
print('tint>0.40:', hi, 'mean conf', round(float(np.mean([r[2] for r in hi])), 3) if hi else None)
print('tint<=0.26 mean conf', round(float(np.mean([r[2] for r in lo])), 3), 'n', len(lo))
