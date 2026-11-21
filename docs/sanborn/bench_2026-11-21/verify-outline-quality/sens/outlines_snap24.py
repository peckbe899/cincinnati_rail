"""Block outlines of a plate from the two networks (15 November 2026; markers, green gate and closed rings 21 November 2026).

    cd data/sanborn
    python ../../tools/sanborn/unet/outlines.py N AREA LINES        e.g. 44 edge_v1 lines_v2

The area network (unet.py, unet_data/N_pred_AREA.png) says which ground is block and which is street; the line network
(edgenet.py, unet_data/N_lines_LINES.png) says where the printed block lines are. Neither alone gives an outline: the
area's edge is a few pixels off the line, and the lines are not joined up.
1. Seeds: ground the area network is sure of (block: P > 0.5, SEED_B px in from its edge; street likewise SEED_S px).
   Every block seed is cut by the detected lines (dilated MK_CUT px) and each piece of MK_SEED_MIN px or more is a marker
   of its own, so two blocks the area network joins across an alley stay apart where the line network drew the line
   between them (one marker per closed basin, Chen et al. 2021).
2. The ground between the seeds is shared out by a watershed over the line map, so the boundary between block and
   street (or between two blocks) settles on the ridge of the detected line where there is one. Each block is then
   opened, size-checked and traced on its own.
3. Each block's boundary is cut into sides; a straight line is fitted to every side of MINLEN px or more, then slid
   (up to SLIDE px) and turned onto the strongest detected line beside it. Ben, 14 November 2026: a street is never wavy.
   The sides are closed into a ring, so a block closes in the line editor: neighbouring sides on one straight line are
   joined into one side (and slid again); each side runs on to meet the next where their lines cross (within
   RING_CORNER px); where they do not cross, ends within SNAP_JOIN px are joined and a wider gap gets a bridging side.
4. Check, as the label was checked: every side is tested against the print's black/grey ink (on a printed line or not),
   and against the line network (the detected line runs under it or not). A side is 'on print' (green in the editor)
   only when both hold; on ink alone it is 'on print only' (shown as not settled).
Writes picks22_guided/22-N/outlines.json (polygons, plate px, each side flagged; bridging sides carry 'bridge'),
unet_data/N_outlines.jpg and N_outlines.json (the counts).
"""
import json, os, sys
import numpy as np
import cv2
N, AREA, LINES = sys.argv[1], sys.argv[2], sys.argv[3]; SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'; OUT = os.path.abspath(sys.argv[4]).replace(chr(92), '/') + '/'; os.makedirs(OUT, exist_ok=True)
SEED_B, SEED_S, TOL, MINLEN, SLIDE, TURN, CORNER, MIN_AREA, CUT = 14, 8, 8.0, 60.0, 12, 5, 120.0, 6000, 130.0
MK_CUT, MK_SEED_MIN = 3, 2000                                                  # block markers: seeds cut by the detected lines
RING_CORNER, COLIN_ANG, COLIN_OFF, COLIN_GAP, SNAP_JOIN = 400.0, 4.0, 12.0, 250.0, 24.0   # closing the rings
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
pa = cv2.resize(cv2.imread(AREA if AREA.endswith('.png') else U + f'{N}_pred_{AREA}.png', 0), (W, H), interpolation=cv2.INTER_LINEAR)
pl = cv2.imread(LINES if LINES.endswith('.png') else U + f'{N}_lines_{LINES}.png', 0)
alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170))
g = cv2.GaussianBlur(np.where(ink, cv2.cvtColor(full, cv2.COLOR_BGR2GRAY), 255).astype(np.uint8), (3, 3), 0).astype(np.float32)
lp = cv2.GaussianBlur(pl, (5, 5), 0).astype(np.float32)
# 1, 2: seeds, one marker per block, and the watershed over the line map
blk = (pa > 127) & alpha; stt = (pa <= 127) & alpha
el = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
mk = np.zeros((H, W), np.int32)
mk[cv2.erode(stt.astype(np.uint8), el(SEED_S)) > 0] = 1
seed = (cv2.erode(blk.astype(np.uint8), el(SEED_B)) > 0) & (cv2.dilate((pl > 127).astype(np.uint8), el(MK_CUT)) == 0)   # a detected line cuts the seed
n, cc, st, _ = cv2.connectedComponentsWithStats(seed.astype(np.uint8), connectivity=4)
lut = np.where(st[:, cv2.CC_STAT_AREA] >= MK_SEED_MIN, np.arange(n) + 1, 0).astype(np.int32); lut[0] = 0   # markers 2 .. n; crumbs left to the watershed
lab = lut[cc]; mk[lab > 0] = lab[lab > 0]
mk[~alpha] = 1                                           # off the paper counts with the street side: a block ends at the paper's edge
ws = cv2.watershed(cv2.cvtColor(cv2.GaussianBlur(pl, (3, 3), 0), cv2.COLOR_GRAY2BGR), mk)
# the watershed puts a -1 line between two blocks, so opening the union opens each block on its own (a block's core is
# >= 4 px from any other block, the 3 px dilation cannot cross); its 4-connected pieces are the blocks
block = cv2.morphologyEx(((ws >= 2) & alpha).astype(np.uint8), cv2.MORPH_OPEN, el(3))
n4, cc4 = cv2.connectedComponents(block, connectivity=4)
wl = np.where(block > 0, ws, 0)
mix = np.unique(np.r_[cc4[:, 1:][(cc4[:, 1:] == cc4[:, :-1]) & (wl[:, 1:] != wl[:, :-1])], cc4[1:, :][(cc4[1:, :] == cc4[:-1, :]) & (wl[1:, :] != wl[:-1, :])]])
mix = mix[mix > 0]
if len(mix):                                             # a piece holding two blocks (not seen so far): split it by block
    m = np.isin(cc4, mix); u, inv = np.unique(cc4[m].astype(np.int64) * 10_000_000 + wl[m], return_inverse=True); cc4[m] = n4 + inv.astype(np.int32); n4 += len(u)
area = np.bincount(cc4.ravel(), minlength=n4); keep = np.nonzero(area >= MIN_AREA)[0]; keep = keep[keep > 0]
lut = np.zeros(len(area), np.int32); lut[keep] = np.arange(1, len(keep) + 1); inst = lut[cc4]; block = (inst > 0).astype(np.uint8)
del cc, lab, ws, cc4, wl, seed

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
        if along(lp, a3, b3).mean() > 90: a2, b2 = a3, b3            # only onto a line the network actually drew
        # a fitted side under CUT px that is not on a printed line is the cut corner of the area's rounded shape, not a side
        lines.append(dict(kind='line' if (np.hypot(*(b2 - a2)) >= CUT or on_ink(a2, b2)) else 'short', a=a2, b=b2))
    def meet(p, q):
        d1, d2 = p['b'] - p['a'], q['b'] - q['a']; den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 0.2 * np.hypot(*d1) * np.hypot(*d2): return None
        return p['a'] + ((q['a'][0] - p['a'][0]) * d2[1] - (q['a'][1] - p['a'][1]) * d2[0]) / den * d1
    def colinear(p, q):                                  # q carries p on: same direction, each end near the other's line
        d1, d2 = p['b'] - p['a'], q['b'] - q['a']; L1, L2 = np.hypot(*d1), np.hypot(*d2)
        if L1 < 1 or L2 < 1: return False
        u1, u2 = d1 / L1, d2 / L2
        if u1 @ u2 < np.cos(np.radians(COLIN_ANG)): return False
        n1, n2 = np.array([-u1[1], u1[0]]), np.array([-u2[1], u2[0]])
        if max(abs((q['a'] - p['a']) @ n1), abs((q['b'] - p['a']) @ n1), abs((p['a'] - q['a']) @ n2), abs((p['b'] - q['a']) @ n2)) > COLIN_OFF: return False
        return -0.5 * min(L1, L2) <= (q['a'] - p['b']) @ u1 <= COLIN_GAP
    def join(p, q):                                      # one side through both, slid onto the detected line as above
        d1, d2 = p['b'] - p['a'], q['b'] - q['a']; L1, L2 = np.hypot(*d1), np.hypot(*d2)
        u = d1 + d2; u = u / np.hypot(*u); c_ = (((p['a'] + p['b']) / 2) * L1 + ((q['a'] + q['b']) / 2) * L2) / (L1 + L2)
        a2, b2 = c_ + u * ((p['a'] - c_) @ u), c_ + u * ((q['b'] - c_) @ u); nrm = np.array([-u[1], u[0]])
        best = max(((along(lp, a2 + nrm * i_, b2 + nrm * j_).mean() - 0.6 * (abs(i_) + abs(j_)) / 2, i_, j_) for i_ in range(-SLIDE, SLIDE + 1, 2) for j_ in range(-SLIDE, SLIDE + 1, 2) if abs(i_ - j_) <= TURN * 2))
        a3, b3 = a2 + nrm * best[1], b2 + nrm * best[2]
        if along(lp, a3, b3).mean() > 90: a2, b2 = a3, b3
        return dict(kind='line', a=a2, b=b2)
    # close the ring: short pieces are dropped, the fitted sides are joined, cornered or bridged
    Ls = [dict(kind='line', a=l['a'].copy(), b=l['b'].copy()) for l in lines if l['kind'] == 'line']
    if len(Ls) < 2: return None
    changed = True
    while changed and len(Ls) > 2:
        changed = False
        for k in range(len(Ls)):
            if colinear(Ls[k], Ls[(k + 1) % len(Ls)]): Ls[k] = join(Ls[k], Ls[(k + 1) % len(Ls)]); del Ls[(k + 1) % len(Ls)]; changed = True; break
    n_ = len(Ls); why = [None] * n_
    for k in range(n_):
        p, q = Ls[k], Ls[(k + 1) % n_]; x = meet(p, q); ok = False; why[k] = 'parallel'
        if x is not None:
            why[k] = 'far'
            if np.hypot(*(x - p['b'])) < RING_CORNER and np.hypot(*(x - q['a'])) < RING_CORNER:
                d1, d2 = p['b'] - p['a'], q['b'] - q['a']; why[k] = 'back'      # the corner must not turn a side back on itself
                ok = (x - p['a']) @ d1 > 0.25 * (d1 @ d1) and (q['b'] - x) @ d2 > 0.25 * (d2 @ d2)
        if ok: p['b'] = x.copy(); q['a'] = x.copy(); why[k] = None
        elif np.hypot(*(q['a'] - p['b'])) <= SNAP_JOIN: m_ = (p['b'] + q['a']) / 2; p['b'] = m_.copy(); q['a'] = m_.copy(); why[k] = None
    out = []
    for k in range(n_):
        out.append(Ls[k])
        if why[k]: out.append(dict(kind='bridge', why=why[k], a=Ls[k]['b'].copy(), b=Ls[(k + 1) % n_]['a'].copy()))
    return [s for s in out if np.hypot(*(s['b'] - s['a'])) >= 0.5]

ys, xs = np.nonzero(inst); lab = inst[ys, xs]; K = len(keep)
bx0 = np.full(K + 1, 1 << 30); bx1 = np.zeros(K + 1, int); by0 = np.full(K + 1, 1 << 30); by1 = np.zeros(K + 1, int)
np.minimum.at(bx0, lab, xs); np.maximum.at(bx1, lab, xs); np.minimum.at(by0, lab, ys); np.maximum.at(by1, lab, ys); del ys, xs, lab
cs = []
for i in range(1, K + 1):                                # each block traced on its own: tracing the union would join touching blocks again
    cs += list(cv2.findContours((inst[by0[i]:by1[i] + 1, bx0[i]:bx1[i] + 1] == i).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE, offset=(int(bx0[i]), int(by0[i])))[0])
polys = []; vis = (full * 0.7 + 76).astype(np.uint8); cnt = dict(sides=0, on_printed_line=0, on_detected_line=0, len_all=0.0, len_ink=0.0, len_det=0.0, short_pieces=0, bridges=0)
inner = cv2.erode(alpha.astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
for c in cs:
    sides = straighten(c[:, 0, :])
    if not sides or len(sides) < 3: continue
    rec = []
    for s in sides:
        a, b = s['a'], s['b']; L = float(np.hypot(*(b - a))); m = ((a + b) / 2).astype(int)
        inside = 0 <= m[0] < W and 0 <= m[1] < H and inner[m[1], m[0]]
        ik = on_ink(a, b); dt = bool(along(lp, a, b).mean() > 90)
        if inside:
            cnt['sides'] += 1; cnt['on_printed_line'] += ik; cnt['on_detected_line'] += dt; cnt['len_all'] += L; cnt['len_ink'] += L * ik; cnt['len_det'] += L * dt
        state = 'on print' if (ik and dt) else ('on print only' if ik else ('on detected line only' if dt else 'not on a line'))   # green needs the line network too
        r = dict(a=a.round(1).tolist(), b=b.round(1).tolist(), state=state, paper_edge=not inside)
        if s['kind'] == 'bridge': r['bridge'] = s['why']; cnt['bridges'] += 1
        rec.append(r)
        cv2.line(vis, tuple(a.round().astype(int)), tuple(b.round().astype(int)), (0, 150, 0) if state == 'on print' else ((0, 150, 255) if dt or ik else (0, 0, 230)), 4, cv2.LINE_AA)
    polys.append(rec)
json.dump(polys, open(OUT + 'outlines.json', 'w', encoding='utf8', newline='\n'))
rep = dict(plate=N, area=AREA, lines=LINES, blocks=len(polys), sides=cnt['sides'], on_printed_line=cnt['on_printed_line'], on_detected_line=cnt['on_detected_line'], short_pieces=cnt['short_pieces'],
           share_on_printed_line_by_length=round(cnt['len_ink'] / max(1.0, cnt['len_all']), 3), share_on_detected_line_by_length=round(cnt['len_det'] / max(1.0, cnt['len_all']), 3), bridges=cnt['bridges'])
json.dump(rep, open(OUT + f'{N}_outlines.json', 'w', encoding='utf8', newline='\n'), indent=1)
cv2.imwrite(OUT + f'{N}_outlines.jpg', cv2.resize(vis, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
cv2.imwrite(OUT + f'{N}_blockmask.png', cv2.resize(block * 255, (W // 2, H // 2), interpolation=cv2.INTER_NEAREST))
print(json.dumps(rep))
