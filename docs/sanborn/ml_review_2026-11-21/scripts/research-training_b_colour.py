# read-only: per-plate paper / ink colour across all scans, at 1/8 decode
import cv2, numpy as np, glob, os, json, time
SP = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
OUT = r'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/research-training/'
LAB = {'43', '44', '45', '80', '82A'}; rows = []; t0 = time.time()
for f in sorted(glob.glob(SP + 'cufp/22-*.jpg')):
    N = os.path.basename(f)[3:-4]; im = cv2.imread(f, cv2.IMREAD_REDUCED_COLOR_8)
    if im is None: continue
    h, w = im.shape[:2]; a = SP + f'cufp/{N}/png_alpha_s4.npy'
    alpha = cv2.resize(np.load(a).astype(np.float32), (w, h)) > 0.5 if os.path.exists(a) else np.ones((h, w), bool)
    alpha = cv2.erode(alpha.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    px = im[alpha].reshape(-1, 3)[:, ::-1].astype(np.float32)   # RGB
    lum = px.mean(1); hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)[alpha].reshape(-1, 3).astype(np.float32)
    paper = px[(lum > np.percentile(lum, 60)) & (hsv[:, 1] < np.percentile(hsv[:, 1], 50))]
    pw = np.median(paper, 0); ink = np.percentile(lum, 2)
    sat = hsv[:, 1]; tint = float((sat > 60).mean())      # share of coloured (tinted) ground
    hist = cv2.calcHist([cv2.cvtColor(im, cv2.COLOR_BGR2HSV)], [0, 1], alpha.astype(np.uint8), [18, 8], [0, 180, 0, 256]).ravel(); hist /= hist.sum()
    rows.append(dict(plate=N, labelled=N in LAB, paper_r=round(float(pw[0]), 1), paper_g=round(float(pw[1]), 1), paper_b=round(float(pw[2]), 1),
                     paper_lum=round(float(pw.mean()), 1), paper_yellow=round(float(pw[0] + pw[1] - 2 * pw[2]) / 2, 1), ink_lum_p2=round(float(ink), 1), tinted_share=round(tint, 3), hist=hist.tolist()))
json.dump(rows, open(OUT + 'b_colour.json', 'w'))
print('plates', len(rows), 'in', round(time.time() - t0), 's')
import statistics as S
for k in ('paper_lum', 'paper_yellow', 'paper_r', 'paper_g', 'paper_b', 'ink_lum_p2', 'tinted_share'):
    allv = [r[k] for r in rows]; lv = [r[k] for r in rows if r['labelled']]
    print(f'{k:14s} all: min {min(allv):7.2f} p10 {np.percentile(allv,10):7.2f} median {np.median(allv):7.2f} p90 {np.percentile(allv,90):7.2f} max {max(allv):7.2f} | labelled: {sorted(lv)}')
# histogram distance of each unlabelled plate to its nearest labelled plate (chi-square on HS histogram)
H = {r['plate']: np.array(r['hist']) for r in rows}
def chi(a, b): return float(0.5 * ((a - b) ** 2 / (a + b + 1e-9)).sum())
d = sorted(((min(chi(H[p], H[q]) for q in LAB if q in H), p) for p in H if p not in LAB), reverse=True)
print('labelled-to-labelled nearest:', {p: round(min(chi(H[p], H[q]) for q in LAB if q in H and q != p), 3) for p in LAB if p in H})
print('farthest unlabelled from any labelled plate (chi2 HS hist):', [(p, round(v, 3)) for v, p in d[:12]])
print('median unlabelled distance', round(float(np.median([v for v, _ in d])), 3))
