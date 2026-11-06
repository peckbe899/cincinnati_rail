"""DRAFT, NOT USED. Automatic locator for OSM crossings on the 1922 plates (Ben's first ruling, 6 November 2026), kept as a
record of what was tried. It does not read Sanborn plates well enough: docs/sanborn/dense_locator_2026-11-06.md has the
four versions tried on plate 22-66 and their scores. Ben's second ruling (docs/sanborn/RULES.md rule 12) replaced it with
hand-read crossings; nothing in the pipeline imports or runs this file.

What is here is the last version tried (version 3 in that note): the street network traced as large paper regions,
then the 1912 corridor score (ground/1912/rebuild/controls.py) on it. The parts still useful:
- osm_network() and excluded(): every OSM crossing of two differently named streets, and rule 3's realigned and renamed
  lists by name;
- plate_image(), Model (the current model's forward, inverse and Jacobian), Matcher.on_page(): the crossings that fall on
  a plate's mapped area.

    cd data/sanborn
    python ../../tools/sanborn/dense/locate.py [PLATE ...]    (writes data/sanborn/controls_dense/; thresholds by DENSE_* env)
"""
import collections, csv, datetime, json, os, sys, time

import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'joint'))
import _ws  # noqa: E402

SP = _ws.DATA
for _d in ('sbg', 'cuf', 'cufp', 'cuf38', 'lph'):
    sys.path.insert(0, _ws.CODE + _d)
from names import key, base  # noqa: E402

OUT = 'controls_dense'
OSM_FILES = ('lph/osm_north.geojson', 'basin/osm_basin.geojson', 'lph/osm_east.geojson', 'lph/osm_norwood.geojson', 'lph/osm_west.geojson')
KEEP = {'primary', 'secondary', 'tertiary', 'residential', 'unclassified', 'living_street', 'trunk',
        'primary_link', 'secondary_link', 'tertiary_link'}
REALIGNED = ('Dixmyth', 'Glenmary', 'Lafayette', 'Elmore', 'Duke')
REALIGNED_PAIRS = (('Riddle', 'McMicken'), ('Taylor', 'Foulke'))
COLERAIN_N = 4336600.0
RENAMED = ('Victory Parkway', 'Crane Avenue', 'Montgomery Road', 'McNeil Avenue', 'Robertson Avenue', 'Mount Hope Avenue',
           'Filson Place', 'Alpine Place', 'Quebec Road')
K = 2                  # half resolution
WIN_M = 40.0           # template radius
SEARCH_M = 15.0        # search radius
NMS_M = 3.0            # two peaks closer than this are one
MAX_SECOND = float(os.environ.get('DENSE_MAX_SECOND', 0.85))   # one candidate: the second peak under this share of the best
MIN_CONF = float(os.environ.get('DENSE_MIN_CONF', 0.80))       # confidence: share of the centre-line samples on the street network
MIN_STREET = float(os.environ.get('DENSE_MIN_STREET', 0.60))   # each street's own share
PIN_M = 2.0
MIN_PIN = float(os.environ.get('DENSE_MIN_PIN', 0.05))         # a 2 m shift any way loses at least this share of the score
MIN_SAMPLES = 10       # samples per street in the window
MERGE_M = 5.0


# ------------------------------------------------------------------ OSM
def osm_network():
    """named street lines [(xy (n, 2), name)] and crossings [(E, N, names)] (EPSG:26916)"""
    seen, lines, node = set(), [], {}
    for fn in OSM_FILES:
        for f in json.load(open(SP + fn, encoding='utf8'))['features']:
            p = f['properties']; g = f['geometry']
            if p.get('highway') not in KEEP or not p.get('name') or g['type'] != 'LineString':
                continue
            c = np.round(np.asarray(g['coordinates'], float)[:, :2], 1)
            sig = (p['name'], tuple(c[0]), tuple(c[-1]), len(c))
            if sig in seen:
                continue
            seen.add(sig); lines.append((c, p['name']))
            for x, y in c:
                node.setdefault((x, y), set()).add(p['name'])
    inter = []
    for (x, y), names in node.items():
        if len({base(key(n)) for n in names}) >= 2:
            inter.append((x, y, tuple(sorted(names))))
    # one crossing per name set within MERGE_M
    by = collections.defaultdict(list)
    for e, n, nm in inter:
        by[frozenset(base(key(s)) for s in nm)].append((e, n, nm))
    out = []
    for k, L in by.items():
        used = [False] * len(L)
        for i, (e, n, nm) in enumerate(L):
            if used[i]:
                continue
            grp = [j for j in range(len(L)) if not used[j] and np.hypot(L[j][0] - e, L[j][1] - n) < MERGE_M]
            for j in grp:
                used[j] = True
            P = np.array([L[j][:2] for j in grp]).mean(0)
            out.append((float(P[0]), float(P[1]), nm))
    return lines, out


def excluded(E, N, names):
    s = ' '.join(names)
    for w in REALIGNED:
        if w in s:
            return f'realigned street ({w})'
    if 'Colerain' in s and N > COLERAIN_N:
        return 'realigned street (Colerain north of N 4,336,600)'
    for a, b in REALIGNED_PAIRS:
        if a in s and b in s:
            return f'realigned crossing ({a} at {b})'
    for w in RENAMED:
        if any(base(key(n)) == base(key(w)) for n in names):
            return f'renamed street ({w})'
    return None


def densify(xy, step=1.0):
    out = [xy[:1]]
    for a, b in zip(xy[:-1], xy[1:]):
        n = max(1, int(np.ceil(np.hypot(*(b - a)) / step)))
        out.append(a + (b - a) * (np.arange(1, n + 1)[:, None] / n))
    return np.vstack(out)


class Samples:
    """1 m samples of every named line, with a KD-tree, for template building"""
    def __init__(self, lines):
        from scipy.spatial import cKDTree
        pts, nm = [], []
        for xy, name in lines:
            d = densify(xy); pts.append(d); nm += [name] * len(d)
        self.P = np.vstack(pts); self.name = np.array(nm, object); self.tree = cKDTree(self.P)

    def near(self, E, N, r):
        i = np.array(self.tree.query_ball_point([E, N], r), int)
        return self.P[i], self.name[i]


# ------------------------------------------------------------------ plates
def plate_image(pid):
    """the plate's scan as BGR plus its mapped-area mask (alpha, the halves' page polygon), full resolution"""
    import plates
    n = pid[3:]
    if pid == '22-35N':
        import rasterio
        a = rasterio.open(_ws.ext('/mnt/user-data/uploads/35_northern_CUF.tif')).read()
        im = np.ascontiguousarray(np.moveaxis(a[:3], 0, -1)[:, :, ::-1])
        m = (a[3] > 0) if a.shape[0] > 3 else (im.max(2) > 0)
        return im, m
    if n in ('34L', '34R', '37L', '37R', '16R'):
        from sb import find
        im = cv2.imread(find(pid), cv2.IMREAD_COLOR)
        m = np.zeros(im.shape[:2], np.uint8); cv2.fillPoly(m, [np.array(plates.POLY22[pid], np.int32)], 1)
        return im, m.astype(bool)
    path = _ws.ext('/mnt/user-data/uploads/38.png') if pid == '22-38' else plates.PNGPATH.get(n, _ws.ext(f'/mnt/user-data/uploads/PNG/{n}.png'))
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im.ndim == 3 and im.shape[2] == 4:
        m = im[:, :, 3] > 0; im = np.ascontiguousarray(im[:, :, :3])
    else:
        m = np.ones(im.shape[:2], bool)
        if im.ndim == 2:
            im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    return im, m


class Model:
    """the plate's current model: forward (pixel -> world), its inverse, local Jacobian"""
    def __init__(self, pid, corr=None):
        import jointlib as J
        self.J, self.pid, self.corr = J, pid, corr

    def fwd(self, q):
        P = self.J.base_many(self.pid, np.asarray(q, float))
        return P + self.corr(P) if self.corr is not None else P

    def jac(self, q, h=10.0):
        q = np.asarray(q, float)
        ex = (self.fwd(q + [h, 0]) - self.fwd(q - [h, 0])) / (2 * h)
        ey = (self.fwd(q + [0, h]) - self.fwd(q - [0, h])) / (2 * h)
        return np.stack([ex, ey], 2)            # (n, 2 world, 2 px)

    def inv(self, W):
        W = np.asarray(W, float); Wt = W.copy()
        if self.corr is not None:
            for _ in range(6):
                Wt = W - self.corr(Wt)
        px, py = self.J.base_inv(self.pid, Wt[:, 0], Wt[:, 1])
        q = np.c_[np.ravel(px), np.ravel(py)].astype(float)
        ok = np.all(np.abs(q) < 1e5, 1)
        for _ in range(4):
            if not ok.any():
                break
            Jm = self.jac(q[ok]); r = W[ok] - self.fwd(q[ok])
            q[ok] += np.linalg.solve(Jm, r[:, :, None])[:, :, 0]
        q[~ok] = np.nan
        return q


# ------------------------------------------------------------------ matcher
INK_PAPER = 35.0       # darkness (against the local paper) above which a pixel is ink
STREET_MIN_M = 80.0    # a paper region this long or longer is street network; shorter ones are lots and yards
CLOSE_M = float(os.environ.get("DENSE_CLOSE_M", 4.0))   # closing that takes the pipe lines, lettering and house numbers drawn in a street into it
D_CAP_M = 12.0         # centring distance capped (parks and open ground)


def ink_image(im):
    """half resolution: darkness against the local paper (black ink only) and the coloured pixels"""
    sm = cv2.resize(im, (im.shape[1] // K, im.shape[0] // K), interpolation=cv2.INTER_AREA)
    lab = cv2.cvtColor(sm, cv2.COLOR_BGR2LAB)
    L = lab[..., 0]
    bg = cv2.medianBlur(cv2.resize(L, (L.shape[1] // 2, L.shape[0] // 2), interpolation=cv2.INTER_AREA), 21)
    bg = cv2.resize(bg, (L.shape[1], L.shape[0]), interpolation=cv2.INTER_LINEAR)
    dk = np.clip(bg.astype(np.float32) - L.astype(np.float32), 0, 255)
    col = np.hypot(lab[..., 1].astype(np.float32) - 128, lab[..., 2].astype(np.float32) - 128) > 25
    dk[col] = 0
    return dk, col


def street_mask(im, mask_full, mph):
    """half resolution: the plate's street network. Paper (neither black ink nor colour), its block outlines sealed by a
    one-pixel dilation of the ink, split into connected regions: the long ones (STREET_MIN_M or more) are the streets,
    the rest lots and yards inside the blocks. A closing over CLOSE_M takes in the pipe lines and lettering drawn in
    the streets."""
    ink, col = ink_image(im)
    mk = cv2.resize(mask_full.astype(np.uint8), (ink.shape[1], ink.shape[0]), interpolation=cv2.INTER_NEAREST).astype(bool)
    nonpaper = (ink > INK_PAPER) | col | ~mk
    nonpaper = cv2.dilate(nonpaper.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    n, lab, st, _ = cv2.connectedComponentsWithStats((~nonpaper).astype(np.uint8), connectivity=4)
    big = np.maximum(st[:, cv2.CC_STAT_WIDTH], st[:, cv2.CC_STAT_HEIGHT]) * mph >= STREET_MIN_M
    big[0] = False
    street = big[lab].astype(np.uint8)
    r = max(1, int(round(CLOSE_M / mph)))
    street = cv2.morphologyEx(street, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    return street.astype(bool) & mk


class Matcher:
    """1912 corridor fit on the plate's street network (street_mask): the score of a shift is the mean distance from
    the crossing's OSM centre lines (1 m samples, every street the same weight) to the edge of the street network,
    capped at D_CAP_M, so the best shift runs both centre lines down the middle of their corridors."""

    def __init__(self, im, mask, fold_side):
        self.mask_full = mask
        self.H, self.W = im.shape[:2]
        self.fold = fold_side
        self.im = im

    def prepare(self, mpp_full):
        self.mpp_half = mh = mpp_full * K
        st = street_mask(self.im, self.mask_full, mh); self.im = None
        D = cv2.distanceTransform(st.astype(np.uint8), cv2.DIST_L2, 5).astype(np.float32) * mh
        D = np.minimum(D, D_CAP_M)
        self.pad = int(np.ceil((WIN_M + SEARCH_M) / mh)) + 6
        self.D = cv2.copyMakeBorder(D, self.pad, self.pad, self.pad, self.pad, cv2.BORDER_CONSTANT, value=0.0)
        self.street = cv2.copyMakeBorder(st.astype(np.float32), self.pad, self.pad, self.pad, self.pad, cv2.BORDER_CONSTANT, value=0.0)
        self.street_share = float(st.mean())

    def on_page(self, q):
        q = np.asarray(q, float)
        x, y = q[:, 0], q[:, 1]
        ok = (x >= 0) & (y >= 0) & (x < self.W - 1) & (y < self.H - 1) & np.isfinite(x) & np.isfinite(y)
        xi = np.clip(np.nan_to_num(x), 0, self.W - 1).astype(int); yi = np.clip(np.nan_to_num(y), 0, self.H - 1).astype(int)
        ok &= self.mask_full[yi, xi]
        if self.fold is not None:
            import curl
            u, _ = curl.uv(self.fold, q)
            ok &= u >= 0
        return ok

    def match(self, q0, Jm, E, N, pts, names, streets):
        from scipy.ndimage import map_coordinates
        mh = self.mpp_half
        node = np.array([E, N])
        Ji = np.linalg.inv(Jm) / K                      # world -> half-res px
        rel = (pts - node) @ Ji.T
        keep = (np.hypot(*(pts - node).T) <= WIN_M) & self.on_page(q0[None] + rel * K)
        wts = np.zeros(len(pts)); sid = np.full(len(pts), -1); n_ok = 0
        for k, s in enumerate(streets):
            m = keep & np.array([base(key(n)) == s for n in names], bool)
            if m.sum() >= MIN_SAMPLES:
                wts[m] = 1.0 / m.sum(); sid[m] = k; n_ok += 1
        if n_ok < 2:
            return None, 'one street only in the window (the other off the page or under 10 m)'
        use = wts > 0; rel, wts, sid = rel[use], wts[use] / wts[use].sum(), sid[use]
        R = int(np.ceil(WIN_M / mh)) + 2; S = int(np.ceil(SEARCH_M / mh))
        T = np.zeros((2 * R + 1, 2 * R + 1), np.float32)
        fx, fy = rel[:, 0] + R, rel[:, 1] + R
        x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int); tx, ty = fx - x0, fy - y0
        for dx, dy, w in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)), (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
            np.add.at(T, (y0 + dy, x0 + dx), (wts * w).astype(np.float32))
        c = q0 / K + self.pad
        cx, cy = int(round(c[0])), int(round(c[1])); ox, oy = c[0] - cx, c[1] - cy
        if not (R + S < cx < self.D.shape[1] - R - S - 1 and R + S < cy < self.D.shape[0] - R - S - 1):
            return None, 'off the page'
        win = self.D[cy - R - S:cy + R + S + 1, cx - R - S:cx + R + S + 1]
        win = cv2.warpAffine(win, np.float32([[1, 0, ox], [0, 1, oy]]), (win.shape[1], win.shape[0]), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
        sc = cv2.matchTemplate(win, T, cv2.TM_CCORR)       # shift (dy, dx) = index - S
        a, b = np.unravel_index(int(np.argmax(sc)), sc.shape); best = float(sc[a, b])
        if best <= 0:
            return None, 'no street at the prediction'
        if a in (0, sc.shape[0] - 1) or b in (0, sc.shape[1] - 1):
            return None, 'best at the edge of the +-15 m search'
        nr = max(1, int(round(NMS_M / mh)))
        dil = cv2.dilate(sc, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * nr + 1, 2 * nr + 1)))
        yy, xx = np.mgrid[:sc.shape[0], :sc.shape[1]]
        far = np.hypot(yy - a, xx - b) * mh >= NMS_M
        cand = sc[(sc >= dil - 1e-9) & far]
        second = float(cand.max()) if len(cand) else 0.0
        pr = PIN_M / mh; drops = []
        for ang in np.arange(8) * np.pi / 4:
            v = cv2.getRectSubPix(sc, (1, 1), (float(b + pr * np.cos(ang)), float(a + pr * np.sin(ang))))[0, 0]
            drops.append(1 - float(v) / best)
        pin = float(min(drops))
        Z = sc[a - 1:a + 2, b - 1:b + 2].astype(float)
        gx = (Z[1, 2] - Z[1, 0]) / 2; gy = (Z[2, 1] - Z[0, 1]) / 2
        hxx = Z[1, 2] - 2 * Z[1, 1] + Z[1, 0]; hyy = Z[2, 1] - 2 * Z[1, 1] + Z[0, 1]
        hxy = (Z[2, 2] - Z[2, 0] - Z[0, 2] + Z[0, 0]) / 4
        Hm = np.array([[hxx, hxy], [hxy, hyy]])
        try:
            off = -np.linalg.solve(Hm, [gx, gy]) if np.linalg.eigvalsh(Hm).max() < 0 else np.zeros(2)
        except np.linalg.LinAlgError:
            off = np.zeros(2)
        off = np.clip(off, -0.6, 0.6)
        dx, dy = (b - S) + off[0], (a - S) + off[1]
        u = rel[:, 0] + cx + ox + dx; v = rel[:, 1] + cy + oy + dy
        ins = map_coordinates(self.street, [v, u], order=0, mode='constant') > 0.5
        conf = float(wts @ ins)
        per = [float((wts[sid == k] @ ins[sid == k]) / wts[sid == k].sum()) for k in range(len(streets)) if (sid == k).any()]
        px = q0 + np.array([dx, dy]) * K
        rec = dict(px=[round(float(px[0]), 2), round(float(px[1]), 2)], shift_m=round(float(np.hypot(dx, dy) * mh), 2),
                   score=dict(confidence=round(conf, 3), street_inside=[round(p, 3) for p in per], second_ratio=round(second / best, 3),
                              pin=round(pin, 3), mean_centring_m=round(best, 3)))
        if second / best > MAX_SECOND:
            return rec, f'two candidates (second peak {second / best:.2f} of the best)'
        if conf < MIN_CONF:
            return rec, f'confidence under {MIN_CONF} (centre lines off the street network)'
        if min(per) < MIN_STREET:
            return rec, f'a street not on the street network (under {MIN_STREET}: changed since 1922)'
        if pin < MIN_PIN:
            return rec, 'not pinned (the streets slide along each other)'
        return rec, None


# ------------------------------------------------------------------ hand picks
def hand_picks(pid):
    """the plate's own controls (the picks its current model was fitted to): pixel X, OSM O"""
    import importlib.util
    spec = importlib.util.spec_from_file_location('joint_solve', os.path.join(os.path.dirname(HERE), 'joint', 'solve.py'))
    SV = importlib.util.module_from_spec(spec); spec.loader.exec_module(SV)
    X, O, P, Pl, names, model = SV.controls(pid)
    return X, O, model


def run_plate(pid, lines=None, inter=None, samples=None, log=print):
    t0 = time.time()
    import curl
    if lines is None:
        lines, inter = osm_network()
    samples = samples or Samples(lines)
    side = curl.side_of(pid)
    fold = side if (side.get('fold') and pid[-1] in 'LR') else None
    im, mask = plate_image(pid)
    M = Model(pid)
    h, w = im.shape[:2]
    cxy = np.array([[w / 2, h / 2]])
    Jc = M.jac(cxy)[0]; mpp = float(np.sqrt(abs(np.linalg.det(Jc))))
    G = M.fwd(np.array([[0, 0], [w, 0], [w, h], [0, h], [w / 2, 0], [w, h / 2], [w / 2, h], [0, h / 2]], float))
    lo, hi = G.min(0) - 50, G.max(0) + 50
    mt = Matcher(im, mask, fold); del im
    mt.prepare(mpp)
    cand = [(e, n, nm) for e, n, nm in inter if lo[0] < e < hi[0] and lo[1] < n < hi[1]]
    W = np.array([c[:2] for c in cand], float)
    q = M.inv(W)
    on = mt.on_page(q)
    rej = collections.Counter(); rejected, found = [], []
    todo = []
    for i, (e, n, nm) in enumerate(cand):
        if not on[i]:
            continue          # not on this plate: not counted
        why = excluded(e, n, nm)
        if why:
            rej[why.split(' (')[0]] += 1; rejected.append(dict(osm=[round(e, 2), round(n, 2)], names=list(nm), reason=why)); continue
        todo.append(i)
    log(f'{pid}: {mpp:.3f} m/px, OSM crossings on the plate {sum(on)}, to match {len(todo)}')

    def attempt(idx, M_):
        res = {}
        qq = M_.inv(W[idx]); Jq = M_.jac(qq)
        for k, i in enumerate(idx):
            e, n, nm = cand[i]
            if not np.all(np.isfinite(qq[k])) or not mt.on_page(qq[k:k + 1])[0]:
                res[i] = (None, 'off the page'); continue
            pts, names = samples.near(e, n, WIN_M + 1)
            streets = sorted({base(key(s)) for s in nm})
            r, why = mt.match(qq[k], Jq[k], e, n, pts, names, streets)
            if r is not None:
                r['predicted_px'] = [round(float(qq[k][0]), 1), round(float(qq[k][1]), 1)]
            res[i] = (r, why)
        return res

    res1 = attempt(todo, M)
    ok1 = [i for i in todo if res1[i][1] is None]
    # pass 2: re-predict the others from the pass-1 controls (current model + smooth correction)
    res = dict(res1); passes = {i: 1 for i in ok1}
    retry = [i for i in todo if res1[i][1] is not None and not res1[i][1].startswith('one street')]
    if len(ok1) >= 20 and retry:
        Xp = np.array([res1[i][0]['px'] for i in ok1]); Op = W[ok1]
        Pp = M.fwd(Xp)
        corr = smooth_corr(Pp, Op - Pp)
        M2 = Model(pid, corr)
        res2 = attempt(retry, M2)
        for i in retry:
            if res2[i][1] is None:
                res[i] = res2[i]; passes[i] = 2
    for i in todo:
        r, why = res[i]; e, n, nm = cand[i]
        if why is None:
            found.append(dict(px=r['px'], osm=[round(e, 2), round(n, 2)], names=list(nm), score=r['score'], 
                              shift_m=r['shift_m'], predicted_px=r['predicted_px'], pass_=passes[i]))
        else:
            rej[why.split(' (')[0]] += 1
            rejected.append(dict(osm=[round(e, 2), round(n, 2)], names=list(nm), reason=why, **({'score': r['score'], 'px': r['px']} if r else {})))
    # agreement with the hand picks (same OSM crossing within 3 m)
    X, O, model = hand_picks(pid)
    Fd = np.array([f['osm'] for f in found]) if found else np.zeros((0, 2))
    agree = []
    for x, o in zip(X, O):
        if not len(Fd):
            break
        d = np.hypot(*(Fd - o).T); j = int(np.argmin(d))
        if d[j] < 3.0:
            pj = np.array(found[j]['px']); Jx = M.jac(x[None])[0]
            agree.append(dict(osm=[round(float(o[0]), 2), round(float(o[1]), 2)], hand_px=[round(float(x[0]), 1), round(float(x[1]), 1)],
                              dense_px=found[j]['px'], names=found[j]['names'],
                              dist_px=round(float(np.hypot(*(pj - x))), 1), dist_m=round(float(np.hypot(*(Jx @ (pj - x)))), 2)))
    dm = np.array([a['dist_m'] for a in agree])
    summ = dict(plate=pid, m_per_px=round(mpp, 4), hand_picks=len(X), osm_crossings_on_plate=int(sum(on)),
                matched=len(todo), found=len(found), found_pass2=sum(1 for f in found if f['pass_'] == 2),
                rejected=dict(sorted(rej.items(), key=lambda kv: -kv[1])),
                both=len(agree), agree_median_m=round(float(np.median(dm)), 2) if len(dm) else None,
                agree_p90_m=round(float(np.percentile(dm, 90)), 2) if len(dm) else None, seconds=round(time.time() - t0))
    for f in found:
        f['pass'] = f.pop('pass_')
    rec = dict(plate=pid, made=datetime.datetime.now().isoformat(timespec='seconds'), by='tools/sanborn/dense/locate.py',
               current_model=_model_path(pid), method='corridor fit (ground/1912/rebuild/controls.py), see the script docstring',
               thresholds=dict(window_m=WIN_M, search_m=SEARCH_M, half_res_m_per_px=round(mpp * K, 4), max_second_ratio=MAX_SECOND,
                               min_confidence=MIN_CONF, min_street_inside=MIN_STREET, pin_m=PIN_M, min_pin=MIN_PIN, ink_paper=INK_PAPER,
                               street_min_m=STREET_MIN_M, close_m=CLOSE_M, d_cap_m=D_CAP_M),
               summary=summ, controls=found, hand_pick_agreement=agree, rejected=rejected)
    os.makedirs(SP + OUT, exist_ok=True)
    json.dump(rec, open(SP + f'{OUT}/{pid}.json', 'w', encoding='utf8', newline='\n'), indent=1)
    log(json.dumps(summ))
    return summ


def _model_path(pid):
    import jointlib as J
    return J.base_path(pid)


def smooth_corr(P, d, lam=1.0, U=500.0):
    """a heavily smoothed world-space correction through displacements d at P (affine + r2 log r, robust)"""
    from scipy.interpolate import RBFInterpolator
    keep = np.ones(len(P), bool)
    for _ in range(3):
        rb = RBFInterpolator(P[keep] / U, d[keep], kernel='thin_plate_spline', smoothing=lam * keep.sum(), degree=1)
        r = np.hypot(*(rb(P / U) - d).T)
        keep = r < max(3.0 * 1.4826 * np.median(r), 3.0)
    return lambda Q: rb(np.asarray(Q, float) / U)


def main():
    import seams as S
    ids = [a for a in sys.argv[1:] if a.startswith('22-')] or S.plate_ids()
    lines, inter = osm_network(); samples = Samples(lines)
    print(f'OSM: {len(lines)} named street lines, {len(inter)} crossings', flush=True)
    rows = []
    for pid in ids:
        rows.append(run_plate(pid, lines, inter, samples, log=lambda s: print(s, flush=True)))
    if len(ids) == len(S.plate_ids()):
        write_summary(rows)


def write_summary(rows):
    reasons = sorted({k for r in rows for k in r['rejected']})
    flat = []
    for r in rows:
        d = {k: v for k, v in r.items() if k != 'rejected'}
        for k in reasons:
            d['rejected: ' + k] = r['rejected'].get(k, 0)
        flat.append(d)
    json.dump(dict(made=datetime.datetime.now().isoformat(timespec='seconds'), plates=rows), open(SP + f'{OUT}/summary.json', 'w', encoding='utf8', newline='\n'), indent=1)
    with open(SP + f'{OUT}/summary.csv', 'w', newline='', encoding='utf8') as f:
        w = csv.DictWriter(f, fieldnames=list(flat[0]), lineterminator='\n'); w.writeheader(); w.writerows(flat)


if __name__ == '__main__':
    main()
