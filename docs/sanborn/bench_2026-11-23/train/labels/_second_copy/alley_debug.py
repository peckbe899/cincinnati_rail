# why an alley of 1A is not found: its long lines, and the pair tests (1A only)
import sys, json, numpy as np, cv2
sys.path.insert(0, 'bench_2026-11-23/train/staged/tools/sanborn/unet')
import make_labels_v2 as M
I = M.pseudo_inputs('1A'); A = M.ALLEY; pxft = 3.0; H, W, h, w = I['H'], I['W'], I['h'], I['w']
bg = cv2.resize(I['blockg'], (W, H), interpolation=cv2.INTER_NEAREST) > 0
inner = cv2.dilate(bg.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
lines = M.long_lines(I['ink'] & inner, pxft, A); print('long lines', len(lines))
boxes = dict(tiernan=(480, 3450, 580, 4160), fenwick=(3820, 2850, 3910, 3830), colby=(2420, 3000, 2500, 3800), cylmer=(3260, 1700, 3330, 2700), lurch=(220, 3760, 520, 3850))
for nm, (x0, y0, x1, y1) in boxes.items():
    sel = []
    for p, u, L in lines:
        m = p + u * L / 2
        if x0 <= m[0] <= x1 and y0 <= m[1] <= y1: sel.append((p.round().tolist(), (p + u * L).round().tolist(), round(L)))
    print(nm, len(sel), sel[:8])
# raw hough pieces in the tiernan box
m = (I['ink'] & inner).astype(np.uint8)
x0, y0, x1, y1 = boxes['tiernan']; sub = m[y0:y1, x0:x1]
print('ink share in tiernan box', round(float(sub.mean()), 3), 'block ground share', round(float(bg[y0:y1, x0:x1].mean()), 3))
cv2.imwrite('bench_2026-11-23/train/labels/tune/tiernan_ink.png', sub * 255)
# the tests on the Fenwick and Cylmer pairs
hink = cv2.resize(I['ink'].astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0
lab_ = cv2.cvtColor(I['img'], cv2.COLOR_BGR2LAB)[:, :, 1:].astype(np.float32); open_ = I['ground_h'] & (I['blockg'] == 0) & ~hink
ref = np.median(lab_[open_], 0); tint = (np.hypot(lab_[:, :, 0] - ref[0], lab_[:, :, 1] - ref[1]) > A['tint']) & ~hink
print('paper ref a*b*', ref)
def test(p, u, L, p2, u2, L2, nm):
    n = np.array([-u[1], u[0]]); off = ((p2 + u2 * L2 / 2) - p) @ n
    t0, t1 = sorted(((p2 - p) @ u, (p2 + u2 * L2 - p) @ u)); s0, s1 = max(0.0, t0), min(L, t1); a0, a1 = p + u * s0, p + u * s1
    g = a0[None, None] + np.linspace(0.05, 0.95, 24)[:, None, None] * (a1 - a0) + np.linspace(0.2, 0.8, 5)[None, :, None] * off * n
    gx = np.clip((g[..., 0] / 2).round().astype(int), 0, w - 1); gy = np.clip((g[..., 1] / 2).round().astype(int), 0, h - 1)
    tm = tint[gy, gx].mean()
    g = a0[None, None] + np.arange(0, s1 - s0, 2.0)[:, None, None] * u + np.linspace(0.15, 0.85, 8)[None, :, None] * off * n
    gx = np.clip(g[..., 0].round().astype(int), 0, W - 1); gy = np.clip(g[..., 1].round().astype(int), 0, H - 1); cr = I['ink'][gy, gx].mean(1)
    print(nm, 'off', round(off, 1), 'overlap', round(s1 - s0), 'tint share', round(float(tm), 3), 'crossings >=0.99', int((cr >= 0.99).sum()), 'at', (np.where(cr >= 0.99)[0][:10] * 2).tolist())
    mid0, mid1 = a0 + n * off / 2, a1 + n * off / 2
    for m0, d in ((mid0, -u), (mid1, u)):
        q = m0 + np.outer(np.arange(0, A['reach_ft'] * pxft, 2.0), d); x = (q[:, 0] / 2).round().astype(int); y = (q[:, 1] / 2).round().astype(int)
        xc, yc = np.clip(x, 0, w - 1), np.clip(y, 0, h - 1); ob = I['blockg'][yc, xc] == 0
        print('   end', m0.round().tolist(), 'leaves block at', int(ob.argmax()) * 2 if ob.any() else None)
L_ = {nm: [l for l in lines if boxes[nm][0] <= (l[0] + l[1] * l[2] / 2)[0] <= boxes[nm][2] and boxes[nm][1] <= (l[0] + l[1] * l[2] / 2)[1] <= boxes[nm][3]] for nm in boxes}
test(*L_['fenwick'][0], *L_['fenwick'][1], 'fenwick'); test(*L_['cylmer'][0], *L_['cylmer'][1], 'cylmer'); test(*L_['tiernan'][0], *L_['tiernan'][1], 'tiernan')
