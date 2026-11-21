import cv2, numpy as np, glob, os, json
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
rows = {}
for f in sorted(glob.glob(SP + 'cufp/22-*.jpg')):
    N = os.path.basename(f)[3:-4]; a = cv2.imread(f, cv2.IMREAD_REDUCED_COLOR_8)
    if a is None: continue
    try: al = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (a.shape[1], a.shape[0])) > 0.5
    except Exception: continue
    hsv = cv2.cvtColor(a, cv2.COLOR_BGR2HSV)
    col = float(((hsv[:,:,1] > 60) & (hsv[:,:,2] > 120))[al].mean())
    # alternative definition: saturation > 50 (less strict)
    col2 = float((hsv[:,:,1] > 50)[al].mean())
    pf = U + f'{N}_pred_area_ng1.png'; pb = None; nb = None
    if os.path.exists(pf):
        p = cv2.imread(pf, 0)
        if p is not None:
            alp = cv2.resize(al.astype(np.uint8), (p.shape[1], p.shape[0]), interpolation=cv2.INTER_NEAREST) > 0; pb = float((p > 127)[alp].mean())
    bj = U + f'{N}_blocks_ng.json'
    if os.path.exists(bj): nb = json.load(open(bj))['blocks']
    rows[N] = (col, col2, pb, nb)
tr = ['43','44','45','80','82A']
T = np.array([rows[n][0] for n in tr]); T2 = np.array([rows[n][1] for n in tr])
allc = np.array([r[0] for r in rows.values()]); unpl = [n for n in rows if n not in tr]
print('plates', len(rows), 'placed col', np.round(T,3), 'col2', np.round(T2,3))
print('all: p5 %.3f median %.3f p95 %.3f' % tuple(np.percentile(allc, [5,50,95])))
out = [n for n in unpl if not (T.min() <= rows[n][0] <= T.max())]; print('unplaced outside placed range', len(out), 'of', len(unpl), '; below', sum(rows[n][0] < T.min() for n in unpl), 'above', sum(rows[n][0] > T.max() for n in unpl))
out2 = [n for n in unpl if not (T2.min() <= rows[n][1] <= T2.max())]; print('alt def: outside', len(out2))
x = np.array([(rows[n][0], rows[n][2]) for n in unpl if rows[n][2] is not None]); print('n with pred', len(x), 'corr', round(float(np.corrcoef(x.T)[0,1]),3))
for n in ['21','22','23','1A','54B']: print(n, rows.get(n))
nbs = [(n, rows[n][3], round(rows[n][2],3) if rows[n][2] else None, round(rows[n][0],3)) for n in unpl if rows[n][3] is not None]
print('blocks_ng counts:', sorted(nbs, key=lambda r: r[1]))
