import cv2, numpy as np, glob, os, json
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'; SP = U[:-10]
col = {r[0]: r[6] for r in json.load(open('s9_colour.json'))}
rows = []
for f in sorted(glob.glob(U + '*_pred_area_ng1.png')):
    N = os.path.basename(f).split('_')[0]; p = cv2.imread(f, 0)
    al = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (p.shape[1], p.shape[0])) > 0.5
    pb = p > 127; unsure = ((p > 64) & (p < 192))[al].mean()
    bj = U + f'{N}_blocks_ng.json'; nb = json.load(open(bj))['blocks'] if os.path.exists(bj) else None
    rows.append((N, col.get(N), round(float(pb[al].mean()), 3), round(float(unsure), 3), nb))
for r in sorted(rows, key=lambda r: r[1] or 0): print(r)
x = np.array([(r[1], r[2]) for r in rows if r[1] is not None]); print('corr(colour share, block share on paper)', round(float(np.corrcoef(x.T)[0, 1]), 3))
