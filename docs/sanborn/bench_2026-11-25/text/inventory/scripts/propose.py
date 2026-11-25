"""Word proposals for a truth crop: a starting point that is then read and corrected by eye (annotate_T*.txt).
python -B propose.py T1 [T2 ...]
Writes truth/work/T#_prop.json (groups with rotated boxes) and truth/work/T#_tile_RC.jpg (1:1 tiles with numbered boxes).
How: ink (as ink_bins) less straight runs of 71 px or more (line_mask) -> pieces 3..220 px -> pieces joined when within
~4 px (ellipse 9 dilation) -> each group's minimum-area rectangle. Proposals are NOT truth: every one is checked."""
import sys, os, json
import numpy as np, cv2
from common import INV, window, line_mask, jdump

CROPS = json.load(open(os.path.join(INV, 'truth', 'crops.json')))
WORK = os.path.join(INV, 'truth', 'work'); os.makedirs(WORK, exist_ok=True)
PAD = 80


def propose(tid):
    c = CROPS[tid]; p = c['plate']; X0, Y0, X1, Y1 = c['win']
    img, lab, ink, (wx0, wy0, wx1, wy1) = window(p, X0 - PAD, Y0 - PAD, X1 + PAD, Y1 + PAD)
    ln = line_mask(ink, 71)
    cand = ink & ~(cv2.dilate(ln.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
    n, lb, st, _ = cv2.connectedComponentsWithStats(cand.astype(np.uint8), connectivity=8)
    ext = np.maximum(st[:, 2], st[:, 3]); keep = (ext >= 3) & (ext <= 220) & (st[:, 4] >= 6); keep[0] = False
    km = keep[lb]
    g = cv2.dilate(km.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    ng, gl, gs, _ = cv2.connectedComponentsWithStats(g, connectivity=8)
    props = []
    for i in range(1, ng):
        x, y, w, h, a = gs[i]
        sub = (gl[y:y + h, x:x + w] == i) & km[y:y + h, x:x + w]
        ys, xs = np.nonzero(sub)
        if len(xs) < 10: continue
        pts = np.c_[xs + x + wx0, ys + y + wy0].astype(np.float32)
        (cx, cy), (rw, rh), ang = cv2.minAreaRect(pts)
        if rw < rh: rw, rh, ang = rh, rw, ang + 90
        ang = ((ang + 90) % 180) - 90
        if not (X0 <= cx < X1 and Y0 <= cy < Y1): continue
        props.append(dict(cx=round(float(cx), 1), cy=round(float(cy), 1), w=round(float(rw) + 2, 1), h=round(float(rh) + 2, 1), ang=round(float(ang), 1),
                          aabb=[int(pts[:, 0].min()), int(pts[:, 1].min()), int(pts[:, 0].max()) + 1, int(pts[:, 1].max()) + 1], npx=int(len(xs))))
    props.sort(key=lambda d: (round(d['cy'] / 100), d['cx']))
    for k, d in enumerate(props): d['id'] = k + 1
    jdump(dict(crop=tid, plate=p, win=c['win'], props=props), os.path.join(WORK, f'{tid}_prop.json'))
    draw(tid, img, (wx0, wy0), props)
    print(tid, len(props), 'proposals')


def draw(tid, img, off, props, tw=750, th=500):
    X0, Y0, X1, Y1 = CROPS[tid]['win']
    for r, ty in enumerate(range(Y0, Y1, th)):
        for cc, tx in enumerate(range(X0, X1, tw)):
            x0, y0 = tx - 20, ty - 20; x1, y1 = min(tx + tw, X1) + 20, min(ty + th, Y1) + 20
            t = img[y0 - off[1]:y1 - off[1], x0 - off[0]:x1 - off[0]].copy()
            t = (t * 0.8 + 255 * 0.2).astype(np.uint8)
            for gx in range((x0 // 50 + 1) * 50, x1, 50):
                cv2.line(t, (gx - x0, 0), (gx - x0, 6), (255, 120, 0), 1)
                if gx % 100 == 0: cv2.putText(t, str(gx), (gx - x0 + 1, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (255, 0, 0), 1)
            for gy in range((y0 // 50 + 1) * 50, y1, 50):
                cv2.line(t, (0, gy - y0), (6, gy - y0), (255, 120, 0), 1)
                if gy % 100 == 0: cv2.putText(t, str(gy), (1, gy - y0 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (255, 0, 0), 1)
            for d in props:
                box = cv2.boxPoints(((d['cx'], d['cy']), (d['w'], d['h']), d['ang'])) - [x0, y0]
                if box[:, 0].max() < 0 or box[:, 1].max() < 0 or box[:, 0].min() > x1 - x0 or box[:, 1].min() > y1 - y0: continue
                cv2.polylines(t, [np.round(box).astype(np.int32)], True, (0, 0, 255), 1)
                q = box[np.argmin(box[:, 1])]
                cv2.putText(t, str(d['id']), (int(q[0]), int(q[1]) - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 120, 0), 1)
            cv2.imwrite(os.path.join(WORK, f'{tid}_tile_{r}{cc}.jpg'), t, [cv2.IMWRITE_JPEG_QUALITY, 92])


if __name__ == '__main__':
    for t in sys.argv[1:]: propose(t)
