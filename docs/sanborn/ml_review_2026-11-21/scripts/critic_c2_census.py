import json, os, glob, re
import numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = D + 'unet_data/'
rows = []
for f in sorted(glob.glob(D + 'cufp/22-*.jpg')):
    n = re.search(r'22-(\w+)\.jpg', f).group(1)
    W, H = Image.open(f).size
    a = D + f'cufp/{n}/png_alpha_s4.npy'
    al = np.load(a) if os.path.exists(a) else None
    src = D + f'cufp/{n}/source.json'; kind = 'pdf' if os.path.exists(src) else 'png'
    pp = U + f'{n}_pred_area_ng1.png'; bs = None; unsure = None
    if os.path.exists(pp) and al is not None:
        p = cv2.imread(pp, 0); m = cv2.resize(al.astype(np.uint8), (p.shape[1], p.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
        bs = float((p[m] > 127).mean()); unsure = float(((p[m] > 25) & (p[m] < 230)).mean())
    bj = U + f'{n}_blocks_ng.json'; b = json.load(open(bj)) if os.path.exists(bj) else {}
    rows.append(dict(n=n, W=W, H=H, kind=kind, paper=round(float(al.mean()), 3) if al is not None else None, block_share=None if bs is None else round(bs, 3), unsure=None if unsure is None else round(unsure, 3), blocks=b.get('blocks'), sides=b.get('sides'), guide=os.path.exists(U + f'{n}_guide.png')))
json.dump(rows, open(os.path.dirname(os.path.abspath(__file__)) + '/census.json', 'w'), indent=0)
for r in sorted(rows, key=lambda r: (r['W'] * r['H'])):
    print(f"{r['n']:4s} {r['kind']} {r['W']:6d}x{r['H']:5d} paper {r['paper']} block_share {r['block_share']} unsure {r['unsure']} blocks {r['blocks']} sides {r['sides']} guide {r['guide']}")
