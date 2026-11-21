"""A copy of tools/sanborn/unet/outlines.py (15 Nov 2026) with only the I/O changed: inputs are given as paths, every
output goes to the scratch folder. The algorithm and its constants are unchanged.

    python outlines_light.py N AREA_PNG LINES_PNG OUT_PREFIX
"""
import json, os, sys
import numpy as np
import cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
N, AREA_PNG, LINES_PNG, OUTP = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
SEED_B, SEED_S, TOL, MINLEN, SLIDE, TURN, CORNER, MIN_AREA, CUT = 14, 8, 8.0, 60.0, 12, 5, 120.0, 6000, 130.0
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
pa = cv2.resize(cv2.imread(AREA_PNG, 0), (W, H), interpolation=cv2.INTER_LINEAR)
pl = cv2.imread(LINES_PNG, 0)
alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170))
g = cv2.GaussianBlur(np.where(ink, cv2.cvtColor(full, cv2.COLOR_BGR2GRAY), 255).astype(np.uint8), (3, 3), 0).astype(np.float32)
lp = cv2.GaussianBlur(pl, (5, 5), 0).astype(np.float32)
blk = (pa > 127) & alpha; stt = (pa <= 127) & alpha
el = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
mk = np.zeros((H, W), np.int32)
mk[cv2.erode(stt.astype(np.uint8), el(SEED_S)) > 0] = 1
mk[cv2.erode(blk.astype(np.uint8), el(SEED_B)) > 0] = 2
mk[~alpha] = 1
mk[(pl > 127) & (mk == 2)] = 0
ws = cv2.watershed(cv2.cvtColor(cv2.GaussianBlur(pl, (3, 3), 0), cv2.COLOR_GRAY2BGR), mk.copy())
block = ((ws == 2) & alpha).astype(np.uint8)
block = cv2.morphologyEx(block, cv2.MORPH_OPEN, el(3))
n, cc, st, _ = cv2.connectedComponentsWithStats(block, connectivity=4)
for i in range(1, n):
    if st[i, cv2.CC_STAT_AREA] < MIN_AREA: block[cc == i] = 0

def along(img, a, b, o=0.0):
    d = b - a; L = np.hypot(*d); nrm = np.array([-d[1], d[0]]) / (L or 1); t = np.linspace(0.06, 0.94, max(10, int(L))); q = a + np.outer(t, d) + nrm * o
    x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1); return img[y, x]
def on_ink(a, b):
    d = b - a; nrm = np.array([-d[1], d[0]]) / np.hypot(*d)
    return bool(max(np.mean([along(g, a + nrm * s, b + nrm * s, o).mean() for o in (-6, -3, 3, 6)]) - along(g, a + nrm * s, b + nrm * s).mean() for s in (-2, -1, 0, 1, 2)) > 25)

def straighten(c):
    c = c.astype(np.float32); ap = cv2.approxPolyDP(c.reshape(-1, 1, 2), TOL, True)[:, 0, :]
    if len(ap) < 3: return None
    idx = sorted({int(np.argmin(np.hypot(*(c - v).T))) for v in ap}); lines = []
    for k in range(len(idx)):
        i, j = idx[k], idx[(k + 1) % len(idx)]; seg = c[i:j + 1] if j > i else np.r_[c[i:], c[:j + 1]]
        a, b = seg[0].astype(float), seg[-1].astype(float); L = float(np.hypot(*(b - a)))
        if L < MINLEN or len(seg) < 8: lines.append(dict(kind='short', a=a, b=b)); continue
        vx, vy, x0, y0 = cv2.fitLine(seg, cv2.DIST_HUBER, 0, 0.01, 0.01)[:, 0]; dv = np.array([vx, vy], float); p0 = np.array([x0, y0], float)
        a2, b2 = p0 + dv * ((a - p0) @ dv), p0 + dv * ((b - p0) @ dv); nrm = np.array([-dv[1], dv[0]])
        best = max(((along(lp, a2 + nrm * i_, b2 + nrm * j_).mean() - 0.6 * (abs(i_) + abs(j_)) / 2, i_, j_) for i_ in range(-SLIDE, SLIDE + 1, 2) for j_ in range(-SLIDE, SLIDE + 1, 2) if abs(i_ - j_) <= TURN * 2))
        a3, b3 = a2 + nrm * best[1], b2 + nrm * best[2]
        if along(lp, a3, b3).mean() > 90: a2, b2 = a3, b3
        lines.append(dict(kind='line' if (np.hypot(*(b2 - a2)) >= CUT or on_ink(a2, b2)) else 'short', a=a2, b=b2))
    def meet(p, q):
        d1, d2 = p['b'] - p['a'], q['b'] - q['a']; den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 0.2 * np.hypot(*d1) * np.hypot(*d2): return None
        return p['a'] + ((q['a'][0] - p['a'][0]) * d2[1] - (q['a'][1] - p['a'][1]) * d2[0]) / den * d1
    st_ = next((i for i, l in enumerate(lines) if l['kind'] == 'line'), None)
    if st_ is None: return None
    order = lines[st_:] + lines[:st_]; out = []; k = 0; n_ = len(order)
    while k < n_:
        l = order[k]
        if l['kind'] != 'line': out.append(l); k += 1; continue
        j = k + 1; run = []
        while j < n_ and order[j]['kind'] == 'short': run.append(order[j]); j += 1
        nxt = order[j % n_]; out.append(l)
        if nxt['kind'] == 'line' and nxt is not l:
            x = meet(l, nxt)
            if x is not None and np.hypot(*(x - l['b'])) < CORNER and np.hypot(*(x - nxt['a'])) < CORNER: l['b'] = x; nxt['a'] = x
            else: out += run
        else: out += run
        k = j
    return out

cs, _ = cv2.findContours(block, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
polys = []; cnt = dict(sides=0, on_printed_line=0, on_detected_line=0, len_all=0.0, len_ink=0.0, len_det=0.0, short_pieces=0)
inner = cv2.erode(alpha.astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
for c in cs:
    sides = straighten(c[:, 0, :])
    if not sides or len(sides) < 3: continue
    rec = []
    for s in sides:
        a, b = s['a'], s['b']; L = float(np.hypot(*(b - a))); m = ((a + b) / 2).astype(int)
        inside = 0 <= m[0] < W and 0 <= m[1] < H and inner[m[1], m[0]]
        if s['kind'] != 'line' or L < 28:
            cnt['short_pieces'] += 1; rec.append(dict(a=a.round(1).tolist(), b=b.round(1).tolist(), state='short')); continue
        ik = on_ink(a, b); dt = bool(along(lp, a, b).mean() > 90)
        if inside:
            cnt['sides'] += 1; cnt['on_printed_line'] += ik; cnt['on_detected_line'] += dt; cnt['len_all'] += L; cnt['len_ink'] += L * ik; cnt['len_det'] += L * dt
        rec.append(dict(a=a.round(1).tolist(), b=b.round(1).tolist(), state='on print' if ik else ('on detected line only' if dt else 'not on a line'), paper_edge=not inside))
    polys.append(rec)
json.dump(polys, open(OUTP + '_outlines.json', 'w', encoding='utf8'))
cv2.imwrite(OUTP + '_blockmask.png', block * 255)
rep = dict(plate=N, area=AREA_PNG, lines=LINES_PNG, blocks=len(polys), sides=cnt['sides'], on_printed_line=cnt['on_printed_line'], on_detected_line=cnt['on_detected_line'], short_pieces=cnt['short_pieces'],
           share_on_printed_line_by_length=round(cnt['len_ink'] / max(1.0, cnt['len_all']), 3), share_on_detected_line_by_length=round(cnt['len_det'] / max(1.0, cnt['len_all']), 3))
json.dump(rep, open(OUTP + '_outlines_rep.json', 'w', encoding='utf8'), indent=1)
print(json.dumps(rep))
