"""Read-only experiment: outlines.py steps 1-2 (seeds from the area map + watershed over the line map) on plate 44 with
different area maps / elevations, scored by panoptic quality against Ben's closed blocks (streetmap/22-44.json).
Mirrors tools/sanborn/unet/outlines.py:26-47. Writes nothing outside this scratch folder."""
import json, sys, time
import numpy as np, cv2
from pq44 import gt_instances, pq, D, S
U = D + 'unet_data/'
SEED_B, SEED_S, MIN_AREA = 14, 8, 6000
full = cv2.imread(D + 'cufp/22-44.jpg'); H, W = full.shape[:2]
alpha = cv2.resize(np.load(D + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
def area(name): return cv2.resize(cv2.imread(U + f'44_pred_{name}.png', 0), (W, H), interpolation=cv2.INTER_LINEAR)
pl = cv2.imread(U + '44_lines_lines_v2.png', 0)
hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170))
inkdark = np.where(ink, 255 - cv2.cvtColor(full, cv2.COLOR_BGR2GRAY), 0).astype(np.uint8); del hsv
el = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
gt, ng, shape = gt_instances()

def blocks(pa, lines, seed_b=SEED_B, seed_s=SEED_S, thr=127):
    blk = (pa > thr) & alpha; stt = (pa <= thr) & alpha
    mk = np.zeros((H, W), np.int32)
    mk[cv2.erode(stt.astype(np.uint8), el(seed_s)) > 0] = 1
    mk[cv2.erode(blk.astype(np.uint8), el(seed_b)) > 0] = 2
    mk[~alpha] = 1
    mk[(lines > 127) & (mk == 2)] = 0
    ws = cv2.watershed(cv2.cvtColor(cv2.GaussianBlur(lines, (3, 3), 0), cv2.COLOR_GRAY2BGR), mk)
    b = ((ws == 2) & alpha).astype(np.uint8); b = cv2.morphologyEx(b, cv2.MORPH_OPEN, el(3))
    n, cc, st, _ = cv2.connectedComponentsWithStats(b, connectivity=4)
    keep = np.where(st[:, cv2.CC_STAT_AREA] >= MIN_AREA)[0]; keep = keep[keep > 0]
    remap = np.zeros(n, np.int32); remap[keep] = np.arange(1, len(keep) + 1); inst = remap[cc]
    return cv2.resize(inst, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST), len(keep)

if __name__ == '__main__':
    e1, ng1 = area('edge_v1'), area('area_ng1')
    runs = [('A edge_v1 + lines_v2 (outlines.py as is)', e1, pl, {}),
            ('B area_ng1 + lines_v2', ng1, pl, {}),
            ('C min(edge_v1, area_ng1) + lines_v2  (street if either says street)', np.minimum(e1, ng1), pl, {}),
            ('D mean(edge_v1, area_ng1) + lines_v2', ((e1.astype(np.uint16) + ng1) // 2).astype(np.uint8), pl, {}),
            ('E area_ng1 + ink darkness as elevation (no line network)', ng1, inkdark, {}),
            ('F area_ng1 + max(lines_v2, ink) elevation', ng1, np.maximum(pl, inkdark), {})]
    sel = sys.argv[1:] or [r[0][0] for r in runs]
    for nm, pa, ln, kw in runs:
        if nm[0] not in sel: continue
        t0 = time.time(); inst, n = blocks(pa, ln, **kw); r = pq(gt, ng, inst, n, nm); r['sec'] = round(time.time() - t0); print(json.dumps(r), flush=True)
