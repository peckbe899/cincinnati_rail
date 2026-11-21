"""verify-inference: where do the batch and the area-TTA x8 setting differ on a batch plate? (truth-free, by eye)

    python verify_overlay_diff.py N [--win 2400x1600] [--k 2] [--scale 0.4]

Reads (read only) the inference agent's qa outputs: inference/qa/batch/N/N_edges.json and qa/atta8/N/N_edges.json
(both from the same outline step, so only the maps differ), and the maps unet_data/N_pred_area_ng1.png (batch) and
inference/maps_plates/atta8/N_area.png.
Each exported side is sampled every 2 px; a sample is 'shared' if the other setting has a side within 8 px.
Writes, in this folder, pics/N_diff_overview.jpg (whole plate, scale 0.1) and pics/N_diff_crop{i}.jpg for the K
windows with the most unshared side length:
  grey = shared side, magenta = batch-only side, blue = atta8-only side;
  red tint = block only in the batch map, cyan tint = block only in the atta8 map (P > 0.5).
Prints the unshared lengths.
"""
import json, os, sys
import numpy as np, cv2
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/verify-inference/'
INF = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/inference/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
a = sys.argv[1:]; n = a[0]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
ww, wh = [int(v) for v in opt('--win', '2400x1600').split('x')]; K = int(opt('--k', 2)); sc = float(opt('--scale', 0.4))
full = cv2.imread(SP + f'cufp/22-{n}.jpg'); H, W = full.shape[:2]
E = {s: json.load(open(INF + f'qa/{s}/{n}/{n}_edges.json', encoding='utf8')) for s in ('batch', 'atta8')}
def raster(es):
    m = np.zeros((H, W), np.uint8)
    for e in es: cv2.line(m, tuple(int(round(v)) for v in e['a']), tuple(int(round(v)) for v in e['b']), 255, 1)
    return m
R = {s: raster(E[s]) for s in E}
D = {s: cv2.distanceTransform(255 - R[s], cv2.DIST_L2, 3) for s in R}
def samples(es):
    out = []
    for e in es:
        p, q = np.array(e['a'], float), np.array(e['b'], float); L = np.hypot(*(q - p)); k = max(2, int(L / 2) + 1)
        t = np.linspace(0, 1, k); out.append(np.c_[p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])])
    return np.vstack(out) if out else np.zeros((0, 2))
S = {s: samples(E[s]) for s in E}
uniq = {}
for s, o in (('batch', 'atta8'), ('atta8', 'batch')):
    xy = np.clip(np.round(S[s]).astype(int), 0, [W - 1, H - 1]); far = D[o][xy[:, 1], xy[:, 0]] > 8
    uniq[s] = xy[far]; print(n, s, 'side length', round(len(S[s]) * 2), 'unshared length (8 px)', int(far.sum()) * 2, f'({100 * far.mean():.0f}%)')
pa_b = cv2.resize(cv2.imread(SP + f'unet_data/{n}_pred_area_ng1.png', 0), (W, H), interpolation=cv2.INTER_LINEAR) > 127
pa_t = cv2.resize(cv2.imread(INF + f'maps_plates/atta8/{n}_area.png', 0), (W, H), interpolation=cv2.INTER_LINEAR) > 127
print(n, 'area decision differs on', f'{100 * (pa_b != pa_t).mean():.2f}% of the image', '| block only batch', f'{100 * (pa_b & ~pa_t).mean():.2f}%', '| only atta8', f'{100 * (pa_t & ~pa_b).mean():.2f}%')


def draw(x0, y0, x1, y1, s):
    v = full[y0:y1, x0:x1].astype(np.float32) * 0.8 + 50
    ob, ot = (pa_b & ~pa_t)[y0:y1, x0:x1], (pa_t & ~pa_b)[y0:y1, x0:x1]
    v[ob] = v[ob] * 0.55 + np.array([60, 60, 255], np.float32) * 0.45; v[ot] = v[ot] * 0.55 + np.array([255, 220, 0], np.float32) * 0.45
    v = cv2.resize(v.clip(0, 255).astype(np.uint8), None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    th = max(1, int(round(6 * s)))
    shared = lambda e, o: None
    for name, col in (('batch', (200, 0, 200)), ('atta8', (255, 80, 0))):
        o = 'atta8' if name == 'batch' else 'batch'
        for e in E[name]:
            p, q = np.array(e['a'], float), np.array(e['b'], float); mid = ((p + q) / 2).astype(int)
            mid = np.clip(mid, 0, [W - 1, H - 1]); sh = D[o][mid[1], mid[0]] <= 8
            c = (120, 120, 120) if sh else col
            cv2.line(v, (int((p[0] - x0) * s), int((p[1] - y0) * s)), (int((q[0] - x0) * s), int((q[1] - y0) * s)), c, th, cv2.LINE_AA)
    return v


os.makedirs(V + 'pics', exist_ok=True)
cv2.imwrite(V + f'pics/{n}_diff_overview.jpg', draw(0, 0, W, H, 0.1), [cv2.IMWRITE_JPEG_QUALITY, 88])
# windows with the most unshared length (both kinds together)
acc = np.zeros((H // 50 + 1, W // 50 + 1), np.float32)
for s in uniq:
    for x, y in uniq[s]: acc[y // 50, x // 50] += 2
box = cv2.boxFilter(acc, -1, (ww // 50, wh // 50), normalize=False, anchor=(0, 0), borderType=cv2.BORDER_CONSTANT)
for i in range(K):
    yb, xb = np.unravel_index(np.argmax(box), box.shape); x0, y0 = int(min(xb * 50, W - ww)), int(min(yb * 50, H - wh))
    x0, y0 = max(0, x0), max(0, y0)
    cv2.imwrite(V + f'pics/{n}_diff_crop{i}.jpg', draw(x0, y0, x0 + ww, y0 + wh, sc), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(n, f'crop{i}', (x0, y0, x0 + ww, y0 + wh), 'unshared px in window', int(box[yb, xb]))
    box[max(0, yb - wh // 50):yb + wh // 50, max(0, xb - ww // 50):xb + ww // 50] = -1
