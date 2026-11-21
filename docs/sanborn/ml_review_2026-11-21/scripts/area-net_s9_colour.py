import cv2, numpy as np, glob, os, json
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
rows = []
for f in sorted(glob.glob(SP + 'cufp/22-*.jpg')):
    N = os.path.basename(f)[3:-4]
    a = cv2.imread(f, cv2.IMREAD_REDUCED_COLOR_8)
    if a is None: continue
    try: al = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (a.shape[1], a.shape[0])) > 0.5
    except Exception: al = np.ones(a.shape[:2], bool)
    hsv = cv2.cvtColor(a, cv2.COLOR_BGR2HSV); lab = cv2.cvtColor(a, cv2.COLOR_BGR2LAB)
    v = hsv[:, :, 2][al]; s = hsv[:, :, 1][al]
    paper = al & (hsv[:, :, 2] > np.percentile(v, 60))                  # brightest 40% of the paper: mostly bare paper
    L, A_, B_ = [float(np.median(lab[:, :, k][paper])) for k in range(3)]
    col = float(((hsv[:, :, 1] > 60) & (hsv[:, :, 2] > 120))[al].mean())  # share of paper that is coloured fill/band
    rows.append((N, a.shape[1] * 8, a.shape[0] * 8, round(L, 1), round(A_, 1), round(B_, 1), round(col, 3), round(float(np.median(s)), 1)))
tr = {'43', '44', '45', '80', '82A'}
R = np.array([r[3:] for r in rows], float); T = np.array([r[3:] for r in rows if r[0] in tr], float)
print('plates', len(rows))
names = ['paper L', 'paper a', 'paper b', 'coloured share', 'median sat']
for k, nm in enumerate(names):
    out = [r[0] for r in rows if r[0] not in tr and not (T[:, k].min() <= r[3 + k] <= T[:, k].max())]
    print(f'{nm:15s} placed {T[:, k].min():.2f}..{T[:, k].max():.2f} | all plates p5 {np.percentile(R[:, k], 5):.2f} median {np.median(R[:, k]):.2f} p95 {np.percentile(R[:, k], 95):.2f} | outside placed range: {len(out)} plates')
sz = np.array([r[1:3] for r in rows]); print('sizes (w,h) min', sz.min(0), 'max', sz.max(0), 'median', np.median(sz, 0))
json.dump(rows, open('s9_colour.json', 'w'))
