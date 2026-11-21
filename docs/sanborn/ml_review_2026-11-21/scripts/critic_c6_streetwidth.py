"""scale proxy: width of the streets the area network (area_ng1) found, measured on the street skeleton (full-size px)"""
import json, os, glob, re
import numpy as np, cv2
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = D + 'unet_data/'
cen = {r['n']: r for r in json.load(open(os.path.dirname(os.path.abspath(__file__)) + '/census.json'))}
out = {}
for f in sorted(glob.glob(U + '*_pred_area_ng1.png')):
    n = re.search(r'([0-9A-Z]+)_pred_area_ng1', os.path.basename(f)).group(1)
    p = cv2.imread(f, 0); al = np.load(D + f'cufp/{n}/png_alpha_s4.npy').astype(np.uint8)
    m = cv2.resize(al, (p.shape[1], p.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    m = cv2.erode(m.astype(np.uint8), np.ones((41, 41), np.uint8)) > 0     # away from the paper edge
    st = ((p <= 127) & m).astype(np.uint8)
    st = cv2.morphologyEx(st, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    dt = cv2.distanceTransform(st, cv2.DIST_L2, 5)
    sk = cv2.ximgproc.thinning(st * 255) > 0
    v = dt[sk] * 2 * 2            # diameter, back to full-size px
    v = v[(v > 8)]
    # streets are long strips: keep skeleton pixels whose width is below the 70th percentile (drop open ground blobs)
    res = dict(median=float(np.median(v)), p25=float(np.percentile(v, 25)), n=int(v.size))
    lab = U + f'{n}_label.png'
    if os.path.exists(lab):
        L = cv2.imread(lab, 0); s2 = ((L == 0) & m).astype(np.uint8); s2 = cv2.morphologyEx(s2, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        d2 = cv2.distanceTransform(s2, cv2.DIST_L2, 5); k2 = cv2.ximgproc.thinning(s2 * 255) > 0; w2 = d2[k2] * 4; w2 = w2[w2 > 8]
        res['label_median'] = float(np.median(w2)); res['label_p25'] = float(np.percentile(w2, 25))
    out[n] = res
json.dump(out, open(os.path.dirname(os.path.abspath(__file__)) + '/streetwidth.json', 'w'), indent=1)
def key(n): m = re.match(r'(\d+)(.*)', n); return int(m.group(1)), m.group(2)
for n in sorted(out, key=key):
    r = out[n]; c = cen.get(n, {})
    print(f"{n:4s} {c.get('kind')} median {r['median']:6.1f} p25 {r['p25']:6.1f}" + (f"  label median {r['label_median']:6.1f} p25 {r['label_p25']:6.1f}" if 'label_median' in r else '') + f"  blocks {c.get('blocks')}")
