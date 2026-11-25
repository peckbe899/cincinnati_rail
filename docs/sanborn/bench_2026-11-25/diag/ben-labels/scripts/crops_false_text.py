"""Pictures for Q2 (ben-labels, 25 Nov 2026): false editor lines on 44 whose ink is mostly text (bin 8), and the false
line-net pixels on 1A's held-out region, so the 'text' reading can be checked by eye.
    cd data/sanborn; python -B bench_2026-11-25/diag/ben-labels/scripts/crops_false_text.py
Colours: Ben's street map lines green; the false editor line magenta; text ink (bin 8) tinted blue; on 1A the line net's
false pixels (P > 0.5, > 6 px from his lines) red, the training target's unscored ground grey hatch is not drawn (see the
numbers instead).
"""
import sys, os, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa
EV = SP + 'train_v2_runs/eval/'
def pts(a, b, step=2.0):
    a, b = np.asarray(a, float), np.asarray(b, float); L = np.hypot(*(b - a)); n = max(2, int(L / step) + 1)
    return a + np.linspace(0, 1, n)[:, None] * (b - a)
full = scan('44'); H, W = full.shape[:2]; bins = cv2.imread(SP + 'unet_data/44_bins.png', 0)
sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8')); fin = raster([(l['a'], l['b']) for l in sm['lines']], (H, W), 1.0, 1)
dfin = cv2.distanceTransform((fin == 0).astype(np.uint8), cv2.DIST_L2, 5)
vis = full.copy(); vis[bins == 8] = (vis[bins == 8] * 0.4 + np.array([255, 120, 0]) * 0.6).astype(np.uint8)
for l in sm['lines']: cv2.line(vis, tuple(np.round(l['a']).astype(int)), tuple(np.round(l['b']).astype(int)), (0, 170, 0), 2)
for step in ('baseline', 'V2S1'):
    E = json.load(open(EV + f'{step}/runs44/v2__grid0/44_edges.json', encoding='utf8')); tiles = []
    for e in E:
        q = pts(e['a'], e['b']); x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1)
        if (dfin[y, x] <= 8).mean() >= 0.2: continue
        m = (raster([(e['a'], e['b'])], (H, W), 1.0, WRONG_PX) > 0) & (bins > 0)
        if not m.any() or np.bincount(bins[m], minlength=10)[1:].argmax() + 1 != 8: continue
        c = ((np.array(e['a']) + np.array(e['b'])) / 2).round().astype(int); hf = 160
        x0, y0 = max(0, c[0] - hf), max(0, c[1] - hf); x1, y1 = min(W, x0 + 2 * hf), min(H, y0 + 2 * hf)
        t = vis[y0:y1, x0:x1].copy(); cv2.line(t, tuple((np.array(e['a']) - [x0, y0]).round().astype(int)), tuple((np.array(e['b']) - [x0, y0]).round().astype(int)), (255, 0, 255), 2)
        t = cv2.copyMakeBorder(t, 0, 2 * hf - t.shape[0], 0, 2 * hf - t.shape[1], cv2.BORDER_CONSTANT, value=(60, 60, 60))
        cv2.putText(t, f"{int(dfin[c[1], c[0]])}px", (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2); tiles.append(t)
        if len(tiles) == 16: break
    while len(tiles) % 4: tiles.append(np.full((320, 320, 3), 60, np.uint8))
    cv2.imwrite(os.path.join(DIAG, f'false_text_lines_44_{step}.jpg'), np.vstack([np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]), [cv2.IMWRITE_JPEG_QUALITY, 85])
del full, vis, bins, dfin
# 1A held-out: false pixels of V2S1 and baseline
full = scan('1A'); H, W = full.shape[:2]; bins = cv2.imread(DIAG + '/bins_1A_now.png', 0)
sm = json.load(open(SP + 'train_v2/1A/streetmap.json', encoding='utf8')); fin = raster([(l['a'], l['b']) for l in sm['lines']], (H, W), 1.0, 1)
dfin = cv2.distanceTransform((fin == 0).astype(np.uint8), cv2.DIST_L2, 5); t = cv2.imread(SP + 'train_v2/1A/lines.png', 0)
for step in ('baseline', 'V2S1'):
    p = cv2.imread(EV + f'{step}/maps1A/1A_lines.png', 0); F = (p > 127) & (dfin > 6)
    vis = full.copy(); vis[bins == 8] = (vis[bins == 8] * 0.4 + np.array([255, 120, 0]) * 0.6).astype(np.uint8)
    vis[(t == 255) & ~F] = (vis[(t == 255) & ~F] * 0.75 + 40).astype(np.uint8)          # unscored ground: lighter
    for l in sm['lines']: cv2.line(vis, tuple(np.round(l['a']).astype(int)), tuple(np.round(l['b']).astype(int)), (0, 170, 0), 1)
    vis[F] = (0, 0, 255)
    x0, y0 = 3000, 1500; crop = vis[y0:y0 + 1100, x0:x0 + 1500]
    cv2.imwrite(os.path.join(DIAG, f'false_px_1A_heldout_{step}.jpg'), crop, [cv2.IMWRITE_JPEG_QUALITY, 88])
print('ok')
