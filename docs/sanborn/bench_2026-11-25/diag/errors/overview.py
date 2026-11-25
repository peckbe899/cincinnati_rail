"""errors census: overview pictures of plate 44, grid 0 (the batch grid), one per pair, quarter size.
  thin blue      Ben's lines
  red            new false line (this pair, not the baseline)
  dark green     baseline false line this pair no longer shows (fixed)
  magenta, thick Ben's line the baseline found and this pair lost
  orange fill    new false block; yellow fill: false block shared with the baseline
  grey tone      ground Ben did not decide (void)
    python -B overview.py [GRID]  -> pics/overview_STEP_gG.jpg
"""
import json, os, sys
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
PAIRS = ['V1S1', 'V2S1', 'V1S2', 'V2S2']
g = int(sys.argv[1]) if len(sys.argv) > 1 else 0
sc = 0.25
os.makedirs(HERE + 'pics', exist_ok=True)
base_img = cv2.imread(SP + 'cufp/22-44.jpg', cv2.IMREAD_REDUCED_COLOR_4)
dec = cv2.imread(HERE + 'runs/decided_half.png', 0) > 0
dec4 = cv2.resize(dec.astype(np.uint8), (base_img.shape[1], base_img.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
ben = dict(np.load(HERE + 'runs/ben.npz'))
d = json.load(open(HERE + 'census.json'))
b = dict(np.load(HERE + f'runs/baseline_g{g}.npz'))


def dots(im, P, col, r):
    q = (P * sc).astype(int)
    for x, y in q: cv2.circle(im, (int(x), int(y)), r, col, -1)


for s in PAIRS:
    im = (base_img * 0.6 + 100).astype(np.uint8)
    im[~dec4] = (im[~dec4] * 0.75).astype(np.uint8)
    inst = cv2.imread(HERE + f'runs/{s}_g{g}_inst.png', cv2.IMREAD_UNCHANGED)
    o = d['runs'][f'{s}_g{g}']
    ov = im.copy()
    for f in o['false_blocks']:
        m = cv2.resize((inst == f['id']).astype(np.uint8), (im.shape[1], im.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
        ov[m] = (0, 140, 255) if f.get('new') else (0, 230, 230)
    im = cv2.addWeighted(ov, 0.35, im, 0.65, 0)
    r = dict(np.load(HERE + f'runs/{s}_g{g}.npz')); df = dict(np.load(HERE + f'runs/{s}_g{g}_diff.npz'))
    dots(im, ben['P'][::2], (200, 120, 0), 0)
    dots(im, b['P'][df['fixed']], (0, 120, 0), 1)
    dots(im, ben['P'][df['lost']], (200, 0, 200), 2)
    dots(im, r['P'][df['new']], (0, 0, 230), 1)
    for f in o['false_blocks']:
        if f.get('new'): cv2.putText(im, f"{f['id']}", (int(f['centroid'][0] * sc), int(f['centroid'][1] * sc)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(im, f'{s} grid {g}: red new false, magenta lost, green fixed, orange new false block, dark = void', (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    cv2.imwrite(HERE + f'pics/overview_{s}_g{g}.jpg', im, [cv2.IMREAD_REDUCED_COLOR_2 * 0 + cv2.IMWRITE_JPEG_QUALITY, 85])
    print(s, 'written')
