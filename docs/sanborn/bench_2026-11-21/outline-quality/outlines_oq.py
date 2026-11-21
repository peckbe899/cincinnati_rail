"""outline-quality (21 Nov 2026): the outline step (tools/sanborn/unet/outlines.py) with switchable changes.

With every switch at its default (P = {}) this is outlines.py exactly: the bench's outlines_copy.py, reorganised into
functions so a sweep can load a plate once and run many settings. check_faith.py proves it: the default run gives
bench44/runs/batch/outlines.json byte for byte (batch maps) and picks22_guided/22-44/outlines.json (guided maps).

Switches (P keys; defaults = outlines.py):
  constants  SEED_B SEED_S TOL MINLEN SLIDE TURN CORNER MIN_AREA CUT as outlines.py:26; THR = 127, the P(block)*255 cut
             between block and street seeds (outlines.py:35)
  (a) markers     one watershed marker per block seed. Block seeds (as outlines.py:39) are cut by the line map
                  (P(line)*255 > mk_line_thr, dilated mk_cut px; mk_close > 0 first bridges gaps along straight lines
                  up to mk_close px, at quarter size), then labelled as 4-connected pieces of >= mk_seed_min px; smaller
                  crumbs are left to the watershed. After the watershed every block instance is opened, size-filtered
                  and traced on its own (outlines.py:43-47 and :92 work on the union, which joins the instances again).
      ridge       > 0: also seed street on the ridge (local maxima of the distance transform) of ground with
                  P(block) <= THR that is at least 2*ridge px wide. outlines.py:38 erodes street by SEED_S = 8, so a
                  street narrower than 17 px gets no street seed at all.
  (b) gate        green needs the line network too: a side is 'on print' only if on_ink AND the detected line runs
                  under it (dt, outlines.py:105); on ink without it becomes 'on print only' (exported orange).
  (c) rings       every outline comes out as a closed ring of sides that all survive step 4:
                    1. neighbouring fitted sides that lie on one straight line (angle <= colin_ang deg, each end within
                       colin_off px of the other's line, gap <= colin_gap px) are joined into one side (review pp-3);
                    2. each side is extended to meet the next at their intersection when that lies within ring_corner
                       px of both ends and does not turn either side back on itself (outlines.py uses CORNER = 120);
                    3. otherwise, ends within snap_join px are joined at their midpoint, and wider gaps get a bridging
                       side (kind 'bridge', tested against ink and line map like any side).
                  No 'short' pieces are written; sides shorter than 28 px are kept (in rings their state is tested
                  like any side). edge_extend > 0: a side whose neighbour runs along the paper's edge is extended
                  (up to edge_extend px) to the paper's edge, so the ring meets the editor's sheet outline.
Usage (as the bench harness runs an outline step; cwd data/sanborn):
    python outlines_oq.py N AREA_PNG LINES_PNG OUTDIR [JSON_PARAMS]
or from a variant file:  import outlines_oq; outlines_oq.main(dict(markers=True, ...))
Writes only into OUTDIR: outlines.json, N_outlines.json, N_outlines.jpg, N_blockmask.png, N_blockinst.png (markers).
"""
import json, os, sys
import numpy as np
import cv2

SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
DEF = dict(SEED_B=14, SEED_S=8, TOL=8.0, MINLEN=60.0, SLIDE=12, TURN=5, CORNER=120.0, MIN_AREA=6000, CUT=130.0, THR=127,
           markers=False, mk_line_thr=127, mk_cut=3, mk_seed_min=2000, mk_close=0, ridge=0,
           gate=False,
           rings=False, ring_corner=250.0, colin_ang=4.0, colin_off=6.0, colin_gap=250.0, snap_join=12.0, edge_extend=0, join_slide=0)
el = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def load(N, area_png, lines_png):
    """outlines.py:27-33"""
    full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
    pa = cv2.resize(cv2.imread(area_png, 0), (W, H), interpolation=cv2.INTER_LINEAR)
    pl = cv2.imread(lines_png, 0)
    alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
    hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170)); del hsv
    g = cv2.GaussianBlur(np.where(ink, cv2.cvtColor(full, cv2.COLOR_BGR2GRAY), 255).astype(np.uint8), (3, 3), 0).astype(np.float32); del ink
    lp = cv2.GaussianBlur(pl, (5, 5), 0).astype(np.float32)
    return dict(N=N, full=full, H=H, W=W, pa=pa, pl=pl, alpha=alpha, g=g, lp=lp)


def dir_close(ln, L, step=15):
    """bridge gaps of up to L px along straight lines: max over directions of a closing with a line, at quarter size"""
    H, W = ln.shape; q = cv2.resize(ln, (W // 4, H // 4), interpolation=cv2.INTER_AREA) > 0
    q = q.astype(np.uint8); out = q.copy(); r = max(2, int(round(L / 8)))
    for ang in range(0, 180, step):
        k = np.zeros((2 * r + 1, 2 * r + 1), np.uint8); t = np.radians(ang); dx, dy = np.cos(t) * r, np.sin(t) * r
        cv2.line(k, (int(round(r - dx)), int(round(r - dy))), (int(round(r + dx)), int(round(r + dy))), 1, 1)
        out |= cv2.morphologyEx(q, cv2.MORPH_CLOSE, k)
    return cv2.resize(out, (W, H), interpolation=cv2.INTER_NEAREST) > 0


def regions(D, P):
    """outlines.py:35-47 and :92. Returns (block mask uint8 full size, contours, instance image or None)"""
    H, W, pa, pl, alpha = D['H'], D['W'], D['pa'], D['pl'], D['alpha']
    blk = (pa > P['THR']) & alpha; stt = (pa <= P['THR']) & alpha
    mk = np.zeros((H, W), np.int32)
    mk[cv2.erode(stt.astype(np.uint8), el(P['SEED_S'])) > 0] = 1
    if P['ridge']:
        d = cv2.distanceTransform(stt.astype(np.uint8), cv2.DIST_L2, 5)
        mk[(d >= P['ridge']) & (d >= cv2.dilate(d, np.ones((3, 3), np.uint8)))] = 1; del d
    if not P['markers']:
        mk[cv2.erode(blk.astype(np.uint8), el(P['SEED_B'])) > 0] = 2
        mk[~alpha] = 1                                           # off the paper counts with the street side: a block ends at the paper's edge
        mk[(pl > 127) & (mk == 2)] = 0                           # a detected line inside a block seed is left for the watershed to decide
        ws = cv2.watershed(cv2.cvtColor(cv2.GaussianBlur(pl, (3, 3), 0), cv2.COLOR_GRAY2BGR), mk.copy())
        block = ((ws == 2) & alpha).astype(np.uint8)
        block = cv2.morphologyEx(block, cv2.MORPH_OPEN, el(3))
        n, cc, st, _ = cv2.connectedComponentsWithStats(block, connectivity=4)
        for i in range(1, n):
            if st[i, cv2.CC_STAT_AREA] < P['MIN_AREA']: block[cc == i] = 0
        cs, _ = cv2.findContours(block, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        return block, cs, None
    # (a) one marker per block seed
    seed = cv2.erode(blk.astype(np.uint8), el(P['SEED_B'])) > 0
    ln = (pl > P['mk_line_thr']).astype(np.uint8)
    if P['mk_close']: ln = dir_close(ln, P['mk_close']).astype(np.uint8)
    if P['mk_cut']: ln = cv2.dilate(ln, el(P['mk_cut']))
    seed &= ln == 0; del ln
    n, cc, st, _ = cv2.connectedComponentsWithStats(seed.astype(np.uint8), connectivity=4); del seed
    ok = st[:, cv2.CC_STAT_AREA] >= P['mk_seed_min']; ok[0] = False
    lut = np.where(ok, np.arange(n) + 1, 0).astype(np.int32)      # block instances are 2 .. n
    lab = lut[cc]; del cc
    mk[lab > 0] = lab[lab > 0]; del lab
    mk[~alpha] = 1
    ws = cv2.watershed(cv2.cvtColor(cv2.GaussianBlur(pl, (3, 3), 0), cv2.COLOR_GRAY2BGR), mk); del mk
    uni = ((ws >= 2) & alpha).astype(np.uint8)                    # instances are apart: the watershed puts -1 between them
    # opening the union = opening each instance: an instance's eroded core is >= 4 px from any other instance, so the
    # 3 px dilation cannot cross into it; the pixel keeps the label the watershed gave it
    uni = cv2.morphologyEx(uni, cv2.MORPH_OPEN, el(3))
    n4, cc4 = cv2.connectedComponents(uni, connectivity=4)
    # a 4-connected piece holding two watershed labels would join two blocks again: split such pieces by label
    wl = np.where(uni > 0, ws, 0); del ws
    hz = (cc4[:, 1:] == cc4[:, :-1]) & (cc4[:, 1:] > 0) & (wl[:, 1:] != wl[:, :-1]); vt = (cc4[1:, :] == cc4[:-1, :]) & (cc4[1:, :] > 0) & (wl[1:, :] != wl[:-1, :])
    D['_mixed_pieces'] = int(len(np.unique(np.r_[cc4[:, 1:][hz], cc4[1:, :][vt]])))
    if D['_mixed_pieces']:
        bad = np.unique(np.r_[cc4[:, 1:][hz], cc4[1:, :][vt]]); m = np.isin(cc4, bad)
        u, inv = np.unique(cc4[m].astype(np.int64) * 10_000_000 + wl[m], return_inverse=True)
        cc4[m] = n4 + inv.astype(np.int32); n4 += len(u)
    del hz, vt, wl
    area = np.bincount(cc4.ravel(), minlength=n4)
    keep = np.nonzero(area >= P['MIN_AREA'])[0]; keep = keep[keep > 0]
    lut = np.zeros(len(area), np.int32); lut[keep] = np.arange(1, len(keep) + 1)
    inst = lut[cc4]; del cc4
    block = (inst > 0).astype(np.uint8)
    cs = []
    # bounding boxes per instance
    ys, xs = np.nonzero(inst); lab = inst[ys, xs]; K = len(keep)
    x0 = np.full(K + 1, 1 << 30); x1 = np.zeros(K + 1, int); y0 = np.full(K + 1, 1 << 30); y1 = np.zeros(K + 1, int)
    np.minimum.at(x0, lab, xs); np.maximum.at(x1, lab, xs); np.minimum.at(y0, lab, ys); np.maximum.at(y1, lab, ys); del ys, xs, lab
    for i in range(1, K + 1):
        sub = (inst[y0[i]:y1[i] + 1, x0[i]:x1[i] + 1] == i).astype(np.uint8)
        c, _ = cv2.findContours(sub, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE, offset=(int(x0[i]), int(y0[i])))
        cs += list(c)
    return block, cs, inst


def outline(D, P, vis_out=True):
    """outlines.py:49-110 (+ the switches). Returns polys, the counts, the picture (or None)"""
    P = {**DEF, **P}
    H, W, g, lp, alpha, full = D['H'], D['W'], D['g'], D['lp'], D['alpha'], D['full']
    TOL, MINLEN, SLIDE, TURN, CORNER, CUT = P['TOL'], P['MINLEN'], P['SLIDE'], P['TURN'], P['CORNER'], P['CUT']
    block, cs, inst = regions(D, P)

    def along(img, a, b, o=0.0):
        d = b - a; L = np.hypot(*d); nrm = np.array([-d[1], d[0]]) / (L or 1); t = np.linspace(0.06, 0.94, max(10, int(L))); q = a + np.outer(t, d) + nrm * o
        x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1); return img[y, x]
    def on_ink(a, b):
        d = b - a; nrm = np.array([-d[1], d[0]]) / np.hypot(*d)
        return bool(max(np.mean([along(g, a + nrm * s, b + nrm * s, o).mean() for o in (-6, -3, 3, 6)]) - along(g, a + nrm * s, b + nrm * s).mean() for s in (-2, -1, 0, 1, 2)) > 25)

    def meet(p, q):
        d1, d2 = p['b'] - p['a'], q['b'] - q['a']; den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 0.2 * np.hypot(*d1) * np.hypot(*d2): return None
        return p['a'] + ((q['a'][0] - p['a'][0]) * d2[1] - (q['a'][1] - p['a'][1]) * d2[0]) / den * d1

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
        if P['rings']: return close_ring(lines)
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

    def colinear(p, q):
        d1, d2 = p['b'] - p['a'], q['b'] - q['a']; L1, L2 = np.hypot(*d1), np.hypot(*d2)
        if L1 < 1 or L2 < 1: return False
        u1, u2 = d1 / L1, d2 / L2
        if u1 @ u2 < np.cos(np.radians(P['colin_ang'])): return False
        n1, n2 = np.array([-u1[1], u1[0]]), np.array([-u2[1], u2[0]])
        if max(abs((q['a'] - p['a']) @ n1), abs((q['b'] - p['a']) @ n1), abs((p['a'] - q['a']) @ n2), abs((p['b'] - q['a']) @ n2)) > P['colin_off']: return False
        gap = (q['a'] - p['b']) @ u1
        return -0.5 * min(L1, L2) <= gap <= P['colin_gap']

    def join(p, q):
        """one side through two collinear ones: length-weighted direction and position, from p's start to q's end,
        then slid onto the strongest detected line beside it, as straighten() slides a fitted side"""
        d1, d2 = p['b'] - p['a'], q['b'] - q['a']; L1, L2 = np.hypot(*d1), np.hypot(*d2)
        u = d1 + d2; u = u / np.hypot(*u); c = (((p['a'] + p['b']) / 2) * L1 + ((q['a'] + q['b']) / 2) * L2) / (L1 + L2)
        a2, b2 = c + u * ((p['a'] - c) @ u), c + u * ((q['b'] - c) @ u)
        if P['join_slide']:
            nrm = np.array([-u[1], u[0]]); R = int(P['join_slide'])
            best = max(((along(lp, a2 + nrm * i_, b2 + nrm * j_).mean() - 0.6 * (abs(i_) + abs(j_)) / 2, i_, j_) for i_ in range(-R, R + 1, 2) for j_ in range(-R, R + 1, 2) if abs(i_ - j_) <= TURN * 2))
            a3, b3 = a2 + nrm * best[1], b2 + nrm * best[2]
            if along(lp, a3, b3).mean() > 90: a2, b2 = a3, b3
        return dict(kind='line', a=a2, b=b2)

    def close_ring(lines):
        Ls = [dict(kind='line', a=l['a'].copy(), b=l['b'].copy()) for l in lines if l['kind'] == 'line']
        if len(Ls) < 2: return None
        changed = True
        while changed and len(Ls) > 2:
            changed = False
            for k in range(len(Ls)):
                p, q = Ls[k], Ls[(k + 1) % len(Ls)]
                if colinear(p, q):
                    Ls[k] = join(p, q); del Ls[(k + 1) % len(Ls)]; changed = True; break
        n_ = len(Ls); out = []
        for k in range(n_):
            p, q = Ls[k], Ls[(k + 1) % n_]
            x = meet(p, q); ok = False; why = 'parallel'
            if x is not None:
                why = 'far'
                if np.hypot(*(x - p['b'])) < P['ring_corner'] and np.hypot(*(x - q['a'])) < P['ring_corner']:
                    d1, d2 = p['b'] - p['a'], q['b'] - q['a']
                    ok = (x - p['a']) @ d1 > 0.25 * (d1 @ d1) and (q['b'] - x) @ d2 > 0.25 * (d2 @ d2); why = 'back'
            if ok: p['b'] = x.copy(); q['a'] = x.copy()
            elif np.hypot(*(q['a'] - p['b'])) <= P['snap_join']: m = (p['b'] + q['a']) / 2; p['b'] = m.copy(); q['a'] = m.copy()
            else: p['bridge_to_next'] = why
        for k in range(n_):
            p, q = Ls[k], Ls[(k + 1) % n_]; out.append(p)
            why = p.pop('bridge_to_next', None)
            if why: out.append(dict(kind='bridge', why=why, a=p['b'].copy(), b=q['a'].copy()))
        return [s for s in out if np.hypot(*(s['b'] - s['a'])) >= 0.5]

    polys = []; vis = (full * 0.7 + 76).astype(np.uint8) if vis_out else None
    cnt = dict(sides=0, on_printed_line=0, on_detected_line=0, len_all=0.0, len_ink=0.0, len_det=0.0, short_pieces=0, bridges=0)
    inner = cv2.erode(alpha.astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
    def line(a, b, col, th):
        if vis is not None: cv2.line(vis, tuple(a.round().astype(int)), tuple(b.round().astype(int)), col, th, cv2.LINE_AA)
    for c in cs:
        sides = straighten(c[:, 0, :])
        if not sides or len(sides) < 3: continue
        if P['rings'] and P['edge_extend']: extend_to_edge(sides, inner, alpha, W, H, P['edge_extend'])
        rec = []
        for s in sides:
            a, b = s['a'], s['b']; L = float(np.hypot(*(b - a))); m = ((a + b) / 2).astype(int)
            inside = 0 <= m[0] < W and 0 <= m[1] < H and inner[m[1], m[0]]
            if s['kind'] == 'short' or (not P['rings'] and (s['kind'] != 'line' or L < 28)):
                cnt['short_pieces'] += 1; rec.append(dict(a=a.round(1).tolist(), b=b.round(1).tolist(), state='short'))
                line(a, b, (150, 150, 150), 3); continue
            ik = on_ink(a, b); dt = bool(along(lp, a, b).mean() > 90)
            if inside:
                cnt['sides'] += 1; cnt['on_printed_line'] += ik; cnt['on_detected_line'] += dt; cnt['len_all'] += L; cnt['len_ink'] += L * ik; cnt['len_det'] += L * dt
            if P['gate']: state = 'on print' if (ik and dt) else ('on print only' if ik else ('on detected line only' if dt else 'not on a line'))
            else: state = 'on print' if ik else ('on detected line only' if dt else 'not on a line')
            r = dict(a=a.round(1).tolist(), b=b.round(1).tolist(), state=state, paper_edge=not inside)
            if s['kind'] == 'bridge': r['bridge'] = s.get('why', True); cnt['bridges'] += 1
            rec.append(r)
            line(a, b, (0, 150, 0) if state == 'on print' else ((0, 150, 255) if dt or ik else (0, 0, 230)), 4)
        polys.append(rec)
    rep = dict(plate=D['N'], blocks=len(polys), sides=cnt['sides'], on_printed_line=cnt['on_printed_line'], on_detected_line=cnt['on_detected_line'], short_pieces=cnt['short_pieces'],
               share_on_printed_line_by_length=round(cnt['len_ink'] / max(1.0, cnt['len_all']), 3), share_on_detected_line_by_length=round(cnt['len_det'] / max(1.0, cnt['len_all']), 3))
    if P['rings']: rep['bridges'] = cnt['bridges']
    return polys, rep, vis, block, inst


def extend_to_edge(sides, inner, alpha, W, H, reach):
    """a side whose neighbour in the ring runs along the paper's edge: move the shared end along the side, outwards,
    to the first pixel off the paper (up to reach px), so the side meets the editor's sheet outline"""
    def pe(s):
        m = ((s['a'] + s['b']) / 2).astype(int)
        return not (0 <= m[0] < W and 0 <= m[1] < H and inner[m[1], m[0]])
    flags = [pe(s) for s in sides]; n = len(sides)
    for k, s in enumerate(sides):
        if flags[k] or s['kind'] == 'short': continue
        d = s['b'] - s['a']; L = np.hypot(*d)
        if L < 1: continue
        u = d / L
        for end, sgn, nb in (('b', 1, (k + 1) % n), ('a', -1, (k - 1) % n)):
            if not flags[nb]: continue
            p = s[end]
            for t in range(0, int(reach) + 1):
                q = p + sgn * u * t; x, y = int(round(q[0])), int(round(q[1]))
                if not (0 <= x < W and 0 <= y < H) or not alpha[y, x]: s[end] = q; break


def main(P=None):
    P = dict(P or {})
    if len(sys.argv) > 5: P.update(json.loads(sys.argv[5]))
    if os.environ.get('OQ_PARAMS'): P.update(json.loads(os.environ['OQ_PARAMS']))
    N, AREA, LINES = sys.argv[1], sys.argv[2], sys.argv[3]
    OUT = os.path.abspath(sys.argv[4]).replace('\\', '/') + '/'
    AREA_PNG = AREA if AREA.lower().endswith('.png') else U + f'{N}_pred_{AREA}.png'; LINES_PNG = LINES if LINES.lower().endswith('.png') else U + f'{N}_lines_{LINES}.png'
    D = load(N, AREA_PNG, LINES_PNG)
    polys, rep, vis, block, inst = outline(D, P)
    rep = dict(plate=N, area=AREA, lines=LINES, **{k: v for k, v in rep.items() if k != 'plate'})
    if P: rep['params'] = P
    os.makedirs(OUT, exist_ok=True)
    json.dump(polys, open(OUT + 'outlines.json', 'w', encoding='utf8', newline='\n'))
    json.dump(rep, open(OUT + f'{N}_outlines.json', 'w', encoding='utf8', newline='\n'), indent=1)
    H, W = D['H'], D['W']
    cv2.imwrite(OUT + f'{N}_outlines.jpg', cv2.resize(vis, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
    cv2.imwrite(OUT + f'{N}_blockmask.png', cv2.resize(block * 255, (W // 2, H // 2), interpolation=cv2.INTER_NEAREST))
    if inst is not None: cv2.imwrite(OUT + f'{N}_blockinst.png', cv2.resize(inst.astype(np.uint16), (W // 2, H // 2), interpolation=cv2.INTER_NEAREST))
    print(json.dumps(rep))


if __name__ == '__main__':
    main()
