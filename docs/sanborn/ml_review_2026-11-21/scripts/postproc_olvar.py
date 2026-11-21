"""outlines.py re-implemented with switches (reads the repo, writes only here), scored against Ben's street map of 44.
python olvar.py N AREA LINES variant [variant ...]
variants: base | tol20 | slide30 | tol20slide30 | seedcut | seedcut_tol20slide30 | ... (tokens combined with _)"""
import json, os, sys, time
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'; OUT = os.path.dirname(os.path.abspath(__file__)) + '/'
N, AREA, LINES = sys.argv[1:4]; VARS = sys.argv[4:]
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
pa = cv2.resize(cv2.imread(U + f'{N}_pred_{AREA}.png', 0), (W, H), interpolation=cv2.INTER_LINEAR)
pl = cv2.imread(U + f'{N}_lines_{LINES}.png', 0)
alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170)); del hsv
g = cv2.GaussianBlur(np.where(ink, cv2.cvtColor(full, cv2.COLOR_BGR2GRAY), 255).astype(np.uint8), (3, 3), 0).astype(np.float32)
lp = cv2.GaussianBlur(pl, (5, 5), 0).astype(np.float32)
el = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
inner = cv2.erode(alpha.astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
SEED_B, SEED_S, MIN_AREA = 14, 8, 6000

def blockmask(seedcut):
    blk = (pa > 127) & alpha; stt = (pa <= 127) & alpha
    mk = np.zeros((H, W), np.int32)
    mk[cv2.erode(stt.astype(np.uint8), el(SEED_S)) > 0] = 1
    bs = cv2.erode(blk.astype(np.uint8), el(SEED_B)) > 0
    if seedcut:   # the block seed cut along the detected lines; pieces of it that are small next to their block (a strip of text beyond the line) are dropped
        line = cv2.dilate((pl > 127).astype(np.uint8), el(2)) > 0
        n, cc, st, _ = cv2.connectedComponentsWithStats((bs & ~line).astype(np.uint8), connectivity=4)
        n2, cc2, st2, _ = cv2.connectedComponentsWithStats(blk.astype(np.uint8), connectivity=4)
        big = np.zeros(n2, np.int64)
        for i in range(1, n):   # the largest seed piece inside each area component
            ys, xs = np.nonzero(cc[st[i, 1]:st[i, 1] + st[i, 3], st[i, 0]:st[i, 0] + st[i, 2]] == i); j = cc2[st[i, 1] + ys[0], st[i, 0] + xs[0]]
            big[j] = max(big[j], st[i, 4])
        keep = np.zeros(n, bool)
        for i in range(1, n):
            ys, xs = np.nonzero(cc[st[i, 1]:st[i, 1] + st[i, 3], st[i, 0]:st[i, 0] + st[i, 2]] == i); j = cc2[st[i, 1] + ys[0], st[i, 0] + xs[0]]
            keep[i] = st[i, 4] >= max(MIN_AREA, 0.1 * big[j])
        bs = keep[cc]
    mk[bs] = 2
    mk[~alpha] = 1
    mk[(pl > 127) & (mk == 2)] = 0
    ws = cv2.watershed(cv2.cvtColor(cv2.GaussianBlur(pl, (3, 3), 0), cv2.COLOR_GRAY2BGR), mk.copy())
    block = ((ws == 2) & alpha).astype(np.uint8)
    block = cv2.morphologyEx(block, cv2.MORPH_OPEN, el(3))
    n, cc, st, _ = cv2.connectedComponentsWithStats(block, connectivity=4)
    small = np.zeros(n, bool); small[1:] = st[1:, cv2.CC_STAT_AREA] < MIN_AREA; block[small[cc]] = 0
    return block

def along(img, a, b, o=0.0):
    d = b - a; L = np.hypot(*d); nrm = np.array([-d[1], d[0]]) / (L or 1); t = np.linspace(0.06, 0.94, max(10, int(L))); q = a + np.outer(t, d) + nrm * o
    x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1); return img[y, x]
def on_ink(a, b):
    d = b - a; nrm = np.array([-d[1], d[0]]) / np.hypot(*d)
    return bool(max(np.mean([along(g, a + nrm * s, b + nrm * s, o).mean() for o in (-6, -3, 3, 6)]) - along(g, a + nrm * s, b + nrm * s).mean() for s in (-2, -1, 0, 1, 2)) > 25)

def straighten(c, TOL, MINLEN, SLIDE, TURN, CORNER, CUT, BRIDGE=False):
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
    def colin(p, q):
        d = p['b'] - p['a']; L = np.hypot(*d); d = d / L; e = q['b'] - q['a']; e = e / np.hypot(*e); n = np.array([-d[1], d[0]])
        return d @ e > np.cos(np.radians(3)) and abs((q['a'] - p['a']) @ n) < 5 and abs((q['b'] - p['a']) @ n) < 5 and (q['a'] - p['b']) @ d < 250
    st_ = next((i for i, l in enumerate(lines) if l['kind'] == 'line'), None)
    if st_ is None: return None
    order = lines[st_:] + lines[:st_]; out = []; k = 0; n_ = len(order)
    while k < n_:
        l = order[k]
        if l['kind'] != 'line': out.append(l); k += 1; continue
        j = k + 1; run = []
        while j < n_ and order[j]['kind'] == 'short': run.append(order[j]); j += 1
        while BRIDGE and j < n_ and order[j]['kind'] == 'line' and colin(l, order[j]):   # one straight side cut by a notch: one line across it
            l['b'] = order[j]['b']; run = []; j += 1
            while j < n_ and order[j]['kind'] == 'short': run.append(order[j]); j += 1
        nxt = order[j % n_]; out.append(l)
        if nxt['kind'] == 'line' and nxt is not l:
            x = meet(l, nxt)
            if x is not None and np.hypot(*(x - l['b'])) < CORNER and np.hypot(*(x - nxt['a'])) < CORNER: l['b'] = x; nxt['a'] = x
            else: out += run
        else: out += run
        k = j
    return out

sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8')) if N == '44' else None
def score(polys, tag):
    kept = [(np.array(s['a']), np.array(s['b']), s['state']) for p in polys for s in p if s['state'] != 'short' and not s.get('paper_edge')]
    Lk = sum(np.hypot(*(b - a)) for a, b, _ in kept); Lg = sum(np.hypot(*(b - a)) for a, b, st in kept if st == 'on print')
    Ls = sum(np.hypot(*np.subtract(s['b'], s['a'])) for p in polys for s in p if s['state'] == 'short')
    src = open('C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/edit_server.py', encoding='utf8').read()
    ns = dict(np=np); exec(src[src.index('def clean('):src.index('def plates(')], ns)
    cl = ns['clean']([dict(src='read', name='', a=list(a), b=list(b), state='green' if st == 'on print' else 'orange') for a, b, st in kept])
    A_ = np.array([l['a'] for l in cl], float); B_ = np.array([l['b'] for l in cl], float); D_ = (B_ - A_) / np.hypot(*(B_ - A_).T)[:, None]; Ln_ = np.hypot(*(B_ - A_).T); frag = 0
    for i in range(len(cl)):
        for j in range(i + 1, len(cl)):
            if abs(D_[i] @ D_[j]) < np.cos(np.radians(3)): continue
            n = np.array([-D_[i][1], D_[i][0]])
            if max(abs((A_[j] - A_[i]) @ n), abs((B_[j] - A_[i]) @ n)) > 12: continue
            tj = sorted(((A_[j] - A_[i]) @ D_[i], (B_[j] - A_[i]) @ D_[i])); gap = max(tj[0] - Ln_[i], -tj[1])
            frag += gap < 150
    rep = dict(variant=tag, shown_after_clean=len(cl), broken_pairs=int(frag), blocks=len(polys), exported=len(kept), exported_len=round(Lk), short_len=round(Ls), share_on_print_by_len=round(Lg / max(Lk, 1), 3))
    if sm is not None:
        ex = np.full((H, W), 255, np.uint8)
        for a, b, _ in kept: cv2.line(ex, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), 0, 1)
        dex = cv2.distanceTransform(ex, cv2.DIST_L2, 3)
        bn = np.full((H, W), 255, np.uint8)
        for l in sm['lines']: cv2.line(bn, tuple(np.round(l['a']).astype(int)), tuple(np.round(l['b']).astype(int)), 0, 1)
        dbn = cv2.distanceTransform(bn, cv2.DIST_L2, 3)
        def samp(a, b, D):
            L = np.hypot(*(b - a)); n = max(2, int(L / 4)); P = a + np.outer(np.linspace(0, 1, n), b - a)
            return D[np.clip(P[:, 1].round().astype(int), 0, H - 1), np.clip(P[:, 0].round().astype(int), 0, W - 1)], L
        tot = got = 0
        for l in sm['lines']:
            if l['kind'] != 'printed': continue
            d, L = samp(np.array(l['a']), np.array(l['b']), dex); tot += L; got += L * (d <= 6).mean()
        pt = pg = gt = gg = 0
        for a, b, st in kept:
            d, L = samp(a, b, dbn); pt += L; pg += L * (d <= 6).mean()
            if st == 'on print': gt += L; gg += L * (d <= 6).mean()
        exg = np.full((H, W), 255, np.uint8)
        for a, b, st in kept:
            if st == 'on print': cv2.line(exg, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), 0, 1)
        dexg = cv2.distanceTransform(exg, cv2.DIST_L2, 3); gotg = 0
        for l in sm['lines']:
            if l['kind'] != 'printed': continue
            d, L = samp(np.array(l['a']), np.array(l['b']), dexg); gotg += L * (d <= 6).mean()
        rep.update(recall_green=round(gotg / tot, 3), recall_ben_printed=round(got / tot, 3), precision_exported=round(pg / pt, 3), precision_green=round(gg / max(gt, 1), 3))
    return rep

res = []
for v in VARS:
    t0 = time.time(); tok = v.split('_')
    P = dict(TOL=8.0, MINLEN=60.0, SLIDE=12, TURN=5, CORNER=120.0, CUT=130.0)
    for t_ in tok:
        if t_.startswith('tol') and t_[3:].isdigit(): P['TOL'] = float(t_[3:])
        if t_.startswith('slide') and t_[5:].isdigit(): P['SLIDE'] = int(t_[5:]); P['TURN'] = max(5, int(t_[5:]) // 4)
        if t_.startswith('cut') and t_[3:].isdigit(): P['CUT'] = float(t_[3:])
    P['BRIDGE'] = 'bridge' in tok
    block = blockmask('seedcut' in tok)
    cs, _ = cv2.findContours(block, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); polys = []
    for c in cs:
        sides = straighten(c[:, 0, :], **P)
        if not sides or len(sides) < 3: continue
        rec = []
        for s in sides:
            a, b = s['a'], s['b']; L = float(np.hypot(*(b - a))); m = ((a + b) / 2).astype(int)
            inside = 0 <= m[0] < W and 0 <= m[1] < H and inner[m[1], m[0]]
            if s['kind'] != 'line' or L < 28: rec.append(dict(a=a.round(1).tolist(), b=b.round(1).tolist(), state='short')); continue
            ik = on_ink(a, b); dt = bool(along(lp, a, b).mean() > 90); ik = ik and (dt or 'gate' not in tok)
            rec.append(dict(a=a.round(1).tolist(), b=b.round(1).tolist(), state='on print' if ik else ('on detected line only' if dt else 'not on a line'), paper_edge=not inside))
        polys.append(rec)
    r = score(polys, v); r['seconds'] = round(time.time() - t0); print(json.dumps(r), flush=True); res.append(r)
    json.dump(polys, open(OUT + f'olvar_{N}_{AREA}_{LINES}_{v}.json', 'w'))
json.dump(res, open(OUT + f'olvar_{N}_{AREA}_{LINES}.json', 'w'), indent=1)
