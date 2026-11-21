"""verify-outline-quality: my own close-up overlays, batch (top) against the proposed change (bottom), from MY reruns
(plates_rerun/N_cur/outlines.json and plates_rerun/N_pat/outlines.json). Each goes through its own step 4 (batch:
blocks_noguide.py as it is; proposed: the patched step 4) and the editor's clean() (copied in bench44_vcopy.py).
Green = green in the editor, orange = orange, thin grey = sides step 4 leaves out (short / paper edge / not on a line),
cyan dot = bridge side, magenta dot = open end (no other shown line or sheet line within 10 px).
    python crops.py N x0,y0,x1,y1 SCALE [N x0,y0,x1,y1 SCALE ...]      -> crops/N_x0_y0.jpg"""
import json, os, sys
import numpy as np, cv2
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
sys.path.insert(0, HERE)
import bench44_vcopy as B  # noqa: E402
SP = B.SP


def st4(polys, patched):
    out, left = [], []
    for p in polys:
        for s in p:
            drop = s['state'] == 'short' or s.get('paper_edge') or (patched and s['state'] == 'not on a line')
            (left if drop else out).append(dict(src='read', name='', a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange'))
    return out, left


def open_ends(shown, SH):
    segs = [(np.array(e['a'], float), np.array(e['b'], float)) for e in shown] + [(np.array(e['a'], float), np.array(e['b'], float)) for e in SH]
    def dist(p, a, b):
        d = b - a; L2 = d @ d
        t = 0 if L2 == 0 else np.clip((p - a) @ d / L2, 0, 1); return np.hypot(*(a + t * d - p))
    pts = []
    for i, (a, b) in enumerate(segs[:len(shown)]):
        for p in (a, b):
            if not any(dist(p, *segs[j]) <= 10 for j in range(len(segs)) if j != i): pts.append(p)
    return pts


def panel(full, polys, patched, SH, box, sc):
    x0, y0, x1, y1 = box; im = cv2.resize(full[y0:y1, x0:x1], None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA); im = (im * 0.6 + 100).astype(np.uint8)
    P = lambda p: tuple(((np.array(p, float) - [x0, y0]) * sc).round().astype(int))
    edges, left = st4(polys, patched); shown = B.clean(edges)
    for e in left: cv2.line(im, P(e['a']), P(e['b']), (150, 150, 150), 1, cv2.LINE_AA)
    for e in shown: cv2.line(im, P(e['a']), P(e['b']), (0, 150, 0) if e['state'] == 'green' else (0, 130, 255), 2, cv2.LINE_AA)
    for p in polys:
        for s in p:
            if s.get('bridge') and not s.get('paper_edge'): cv2.circle(im, P((np.array(s['a']) + np.array(s['b'])) / 2), 4, (230, 200, 0), -1)
    for q in open_ends(shown, SH):
        if x0 <= q[0] < x1 and y0 <= q[1] < y1: cv2.circle(im, P(q), 4, (200, 0, 200), 2)
    cv2.putText(im, 'proposed' if patched else 'batch', (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    return im


os.makedirs(HERE + 'crops', exist_ok=True)
a = sys.argv[1:]
for k in range(0, len(a), 3):
    N, box, sc = a[k], [int(v) for v in a[k + 1].split(',')], float(a[k + 2])
    full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
    box = [max(0, box[0]), max(0, box[1]), min(W, box[2]), min(H, box[3])]
    m = (np.load(SP + f'cufp/{N}/png_alpha_s4.npy') > 0.5).astype(np.uint8); sx, sy = W / m.shape[1], H / m.shape[0]; SH = []
    for c in cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]:
        if cv2.contourArea(c) < 500: continue
        p = cv2.approxPolyDP(c, 2.0, True)[:, 0, :].astype(float) * [sx, sy]
        for i in range(len(p)):
            if np.hypot(*(p[(i + 1) % len(p)] - p[i])) >= 40: SH.append(dict(a=p[i].tolist(), b=p[(i + 1) % len(p)].tolist()))
    cur = json.load(open(HERE + f'plates_rerun/{N}_cur/outlines.json')); pat = json.load(open(HERE + f'plates_rerun/{N}_pat/outlines.json'))
    t, b = panel(full, cur, False, SH, box, sc), panel(full, pat, True, SH, box, sc)
    im = np.vstack([t, np.full((6, t.shape[1], 3), 255, np.uint8), b]) if t.shape[1] > t.shape[0] else np.hstack([t, np.full((t.shape[0], 6, 3), 255, np.uint8), b])
    f = HERE + f'crops/{N}_{box[0]}_{box[1]}.jpg'; cv2.imwrite(f, im, [cv2.IMWRITE_JPEG_QUALITY, 85]); print('wrote', f, im.shape)
