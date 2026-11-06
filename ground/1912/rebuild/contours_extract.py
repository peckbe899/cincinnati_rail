"""Stage contours, step 1: vectorise the orange contour ink of one sheet into ordered pixel polylines.

Colour filter first (Ben, 6 November): every scan pixel is unmixed into local paper, the sheet's orange contour ink
and its black ink (linear mixing in RGB; paper = per-channel grey closing that removes thin strokes; orange and black
endmembers measured on the sheet itself). The orange share is a contour-only image: street lines, lettering and
symbols drop out and contours carry on through the street corridors, except where black ink is printed over them.
Centrelines: the ink mask (orange share > INK_T, specks removed) decides which lines exist; Hessian ridges at 1 px
with non-maximum suppression across the line put a 1-px centre in each stroke and keep strokes 4 px apart separate.
Worked in 2048 px tiles at full scan resolution. Segments split at junctions carry stroke peak and width (in
orange share); 'bold' is a first guess that the labelling refines.
Output <work>/contours_px/<sid>.npz: concatenated pixel paths, segment offsets, stroke features, ink coverage.
"""
import json, os, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np, cv2
from scipy import ndimage as ndi
from skimage.morphology import skeletonize, remove_small_objects
from skimage.filters import threshold_otsu

from common import load_paths, load_all, frame_px

T = 2048; OV = 64
MIN_SEG = 12          # px (about 4 m)


SIG = 1.0             # ridge scale (px): contour strokes are about 2 px wide, as little as 4 px apart
INK_T = 0.15          # orange share (smoothed 0.7 px) that seeds contour ink; solid strokes are 0.6-1
INK_LO = 0.06         # ...and the faint level a seeded line is followed through (gaps in pale stretches)
SOLID_T = 0.4         # orange share of solid ink, used to measure stroke width
BAND_HALF = 3.5       # px: solid ink at least this far from paper on both sides (7 px wide) is a merged band;
                      # single strokes are 2-4 px wide at this level
BAND_MIN = 40         # px: smallest band core
BAND_LEN = 30         # px: a band core must be at least this long (bounding-box diagonal)
INK_MIN = 30          # px: ink specks smaller than this are dropped
NMS_T = 0.005         # ridge strength floor (orange share per px^2) for a centreline pixel inside the ink
SPUR = 4              # px
BLACK_T = 0.4         # black share of street lines and lettering: 0.55-1.06; of contour ink: under 0.2 (sheet 29)


def red_excess(c):
    lab = cv2.cvtColor(c, cv2.COLOR_BGR2LAB); L = lab[..., 0]; a = lab[..., 1]
    # paper level: grey opening removes strokes up to ~5 px wide but keeps the paper between dense contours
    bga = cv2.morphologyEx(a, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    bga = cv2.GaussianBlur(bga.astype(np.float32), (0, 0), 3)
    r = np.clip(a.astype(np.float32) - bga, 0, None)
    black = cv2.dilate((L < 100).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    r[black] = 0
    return r


def endmembers(img):
    """Orange and black ink colours (BGR) of one sheet: medians of clearly red-excess and clearly dark pixels."""
    sm = cv2.resize(img, (img.shape[1] // 2, img.shape[0] // 2), interpolation=cv2.INTER_AREA)
    L = cv2.cvtColor(sm, cv2.COLOR_BGR2LAB)[..., 0]; r = red_excess(sm)
    X = sm.reshape(-1, 3).astype(np.float32)
    return np.median(X[((r > 14) & (L > 110)).ravel()], 0), np.median(X[(L < 70).ravel()], 0)


def orange_share(c, o_e, k_e):
    """Per-pixel share of orange ink: x = p + ao (o - p) + ak (k - p), least squares in RGB, p the local paper."""
    x = c.astype(np.float32)
    p = cv2.morphologyEx(x, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)); p = cv2.GaussianBlur(p, (0, 0), 3)
    d = x - p; A = np.stack([o_e[None, None] - p, k_e[None, None] - p], -1)
    AtA = np.einsum('hwci,hwcj->hwij', A, A); Atd = np.einsum('hwci,hwc->hwi', A, d)
    det = AtA[..., 0, 0] * AtA[..., 1, 1] - AtA[..., 0, 1] ** 2 + 1e-6
    ao = (AtA[..., 1, 1] * Atd[..., 0] - AtA[..., 0, 1] * Atd[..., 1]) / det
    ak = (AtA[..., 0, 0] * Atd[..., 1] - AtA[..., 0, 1] * Atd[..., 0]) / det
    # black/grey ink (street lines, lettering) carries a reddish scan fringe that reads as a little orange: blank the
    # orange share wherever black ink is present (contours lose only the few pixels where a street line crosses them)
    blk = cv2.dilate((cv2.GaussianBlur(ak.astype(np.float32), (0, 0), 0.7) > BLACK_T).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)   # + the 2 px colour fringe
    ao[blk] = 0
    return np.clip(ao, 0, 1.5).astype(np.float32), blk


def ridges(r):
    """Centrelines of the red contour ink: the ink mask (smoothed red excess > INK_T, specks removed) decides which
    lines exist; the Hessian ridge at SIG with non-maximum suppression across the line puts a 1-px centre in each
    stroke and keeps touching strokes apart. Returns the centreline mask, the ridge strength and the unit normal."""
    g = cv2.GaussianBlur(r, (0, 0), SIG)
    gyy, gyx = np.gradient(np.gradient(g, axis=0)); gxy, gxx = np.gradient(np.gradient(g, axis=1))
    gxy = (gxy + gyx) / 2
    tr = (gxx + gyy) / 2; dt = np.sqrt(((gxx - gyy) / 2) ** 2 + gxy ** 2)
    lmin = tr - dt
    s = np.where(lmin < 0, -lmin, 0).astype(np.float32)
    vx = gxy; vy = lmin - gxx
    bad = np.hypot(vx, vy) < 1e-9
    vx = np.where(bad, (gxx <= gyy).astype(np.float32), vx); vy = np.where(bad, (gxx > gyy).astype(np.float32), vy)
    nrm = np.hypot(vx, vy); nx = (vx / nrm).astype(np.float32); ny = (vy / nrm).astype(np.float32)
    H, W = s.shape; yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    s1 = cv2.remap(s, xx + nx, yy + ny, cv2.INTER_LINEAR); s2 = cv2.remap(s, xx - nx, yy - ny, cv2.INTER_LINEAR)
    # ink by hysteresis: seeds where the orange share is clear (> INK_T), grown through faint stretches (> INK_LO)
    sm = cv2.GaussianBlur(r, (0, 0), 0.7)
    hi = cv2.morphologyEx((sm > INK_T).astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    lo = (sm > INK_LO).astype(np.uint8)
    nl, lab_, st, _ = cv2.connectedComponentsWithStats(lo, connectivity=8)
    keep = np.zeros(nl, bool); keep[np.unique(lab_[hi > 0])] = True
    keep &= st[:, cv2.CC_STAT_AREA] >= INK_MIN; keep[0] = False
    ink = keep[lab_]
    # merged bands: where converging contours print as one solid stroke wider than any single line, the lines
    # inside cannot be told apart; keep only the band's outer edges (its top and bottom contours) and leave the
    # inside to the surface solve
    solid = (sm > SOLID_T).astype(np.uint8)
    dt = cv2.distanceTransform(solid, cv2.DIST_L2, 5)
    core = (dt >= BAND_HALF).astype(np.uint8)
    nc, lc, sc, _ = cv2.connectedComponentsWithStats(core, connectivity=8)
    kc = (sc[:, cv2.CC_STAT_AREA] >= BAND_MIN) & (np.hypot(sc[:, cv2.CC_STAT_WIDTH], sc[:, cv2.CC_STAT_HEIGHT]) >= BAND_LEN)
    kc[0] = False                          # label digits make short blobs; converging contours make long ones
    core = kc[lc].astype(np.uint8)
    band = (cv2.dilate(core, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * int(BAND_HALF) + 3,) * 2)) > 0) & (hi > 0)
    inner = cv2.erode(band.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    edge = band & ~inner
    nms = (s >= s1) & (s >= s2) & (s > NMS_T) & ink & ~band
    m = prune(skeletonize(nms | edge), SPUR)
    return m, s, nx, ny, band


def ink_coverage(r, m):
    """Share of contour ink (orange share > 0.2) within 2 px of a kept centreline."""
    ink = cv2.GaussianBlur(r, (0, 0), 0.7) > 0.2
    ink = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)).astype(bool)
    near = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    return int((ink & near).sum()), int(ink.sum())


def prune(sk, n):
    """Remove end branches shorter than n px (spurs), n passes of end-point erosion restricted to short branches."""
    sk = sk.copy(); k = np.ones((3, 3), np.uint8)
    removed = np.zeros_like(sk)
    for _ in range(n):
        nb = cv2.filter2D(sk.astype(np.uint8), -1, k, borderType=cv2.BORDER_CONSTANT) - sk
        ends = sk & (nb == 1)
        sk &= ~ends; removed |= ends
    # grow back the pruned ends along branches that were longer than n (they still touch a surviving end)
    for _ in range(n):
        nb = cv2.filter2D(sk.astype(np.uint8), -1, k, borderType=cv2.BORDER_CONSTANT) - sk
        grow = removed & (cv2.dilate((sk & (nb <= 1)).astype(np.uint8), k) > 0)
        sk |= grow; removed &= ~grow
    return sk


def tile(c, em):
    r, blk = orange_share(c, *em)
    m, s, nx, ny, band = ridges(r)
    return m, r, s, nx, ny, band, blk


def trace_paths(sk):
    """Split a skeleton at junctions and order each simple piece end to end. Returns list of (n,2) [x,y] arrays."""
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - 1
    seg = sk & (nb <= 2)
    seg &= ~ndi.binary_dilation(sk & (nb >= 3), np.ones((3, 3)))
    lab, n = ndi.label(seg, np.ones((3, 3)))
    if n == 0:
        return []
    objs = ndi.find_objects(lab)
    out = []
    for k, sl in enumerate(objs, 1):
        sub = lab[sl] == k
        ys, xs = np.nonzero(sub)
        if len(ys) < MIN_SEG:
            continue
        pts = set(zip(ys.tolist(), xs.tolist()))
        deg = {p: sum((p[0] + dy, p[1] + dx) in pts for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx) for p in pts}
        ends = [p for p, d in deg.items() if d <= 1]
        cur = ends[0] if ends else next(iter(pts))
        path = [cur]; seen = {cur}
        while True:
            nxt = None
            for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                q = (cur[0] + dy, cur[1] + dx)
                if q in pts and q not in seen:
                    nxt = q; break
            if nxt is None:
                break
            path.append(nxt); seen.add(nxt); cur = nxt
        if len(path) < MIN_SEG:
            continue
        p = np.array(path, float); p[:, 0] += sl[0].start; p[:, 1] += sl[1].start
        out.append(p[:, ::-1])          # x, y
    return out


def run_sheet(args):
    paths, sid = args
    P = load_paths(paths); ids, _ = load_all(P); d = ids[sid]
    out = Path(P['work']) / 'contours_px' / f'{sid}.npz'
    if out.exists():
        return sid, 'kept'
    t0 = time.time()
    im = cv2.imread(str(Path(P['sheets']) / d['file']))
    H, W = im.shape[:2]
    em = endmembers(im)
    fr = np.zeros((H, W), np.uint8); cv2.fillPoly(fr, [np.int32(frame_px(d))], 1)
    fr = cv2.erode(fr, np.ones((25, 25), np.uint8)).astype(bool)
    SK = np.zeros((H, W), bool); BAND = np.zeros((H, W), bool); BLK = np.zeros((H, W), bool); R = np.zeros((H, W), np.float32); NX = np.zeros((H, W), np.float32); NY = np.zeros((H, W), np.float32)
    for y in range(0, H, T):
        for x in range(0, W, T):
            ya, xa = max(0, y - OV), max(0, x - OV); yb, xb = min(H, y + T + OV), min(W, x + T + OV)
            m, r, s_, nx, ny, bd, bk = tile(im[ya:yb, xa:xb], em)
            hh, ww = min(T, H - y), min(T, W - x); sl = (slice(y - ya, y - ya + hh), slice(x - xa, x - xa + ww))
            SK[y:y + hh, x:x + ww] = m[sl]; R[y:y + hh, x:x + ww] = r[sl]; BAND[y:y + hh, x:x + ww] = bd[sl]; BLK[y:y + hh, x:x + ww] = bk[sl]
            NX[y:y + hh, x:x + ww] = nx[sl]; NY[y:y + hh, x:x + ww] = ny[sl]
    del im
    SK &= fr
    paths_ = trace_paths(SK)
    # how much of the sheet's contour ink the kept segments cover (reported per sheet)
    KM = np.zeros((H, W), bool)
    for p in paths_:
        KM[p[:, 1].astype(int), p[:, 0].astype(int)] = True
    Rf = np.where(fr, R, 0); cov_hit, cov_ink = ink_coverage(Rf, KM); del KM, Rf
    # stroke features along each segment: peak red excess and width (integral across the line / peak)
    G = cv2.GaussianBlur(R, (0, 0), 0.7)
    peak = np.zeros(len(paths_), np.float32); width = np.zeros(len(paths_), np.float32)
    offs = np.arange(-4, 5, dtype=np.float32)
    for k, p in enumerate(paths_):
        q = p[::3]; ix = q[:, 0].astype(int); iy = q[:, 1].astype(int)
        nx = NX[iy, ix]; ny = NY[iy, ix]
        X = (q[:, 0][:, None] + nx[:, None] * offs[None]).astype(np.float32); Y = (q[:, 1][:, None] + ny[:, None] * offs[None]).astype(np.float32)
        prof = cv2.remap(G, X, Y, cv2.INTER_LINEAR)
        pk = prof[:, 3:6].max(1); base = np.minimum(prof[:, 0], prof[:, -1])
        peak[k] = np.median(pk - base)
        width[k] = np.median(np.clip(prof - base[:, None], 0, None).sum(1) / np.maximum(pk - base, 1e-3))
    lens = np.array([len(p) for p in paths_])
    wt = peak * width
    big = wt[lens >= 40]
    thr = float(threshold_otsu(big)) if len(big) > 200 else float(np.percentile(wt, 80))
    bold = wt >= thr
    off = np.r_[0, np.cumsum(lens)].astype(np.int64)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, xy=np.vstack(paths_).astype(np.float32) if paths_ else np.zeros((0, 2), np.float32),
                        off=off, bold=bold, weight=wt, peak=peak, width=width, thr=thr, shape=np.array([H, W]),
                        ink_covered=cov_hit, ink_total=cov_ink, orange_bgr=em[0], black_bgr=em[1],
                        band=np.packbits(BAND & fr), band_px=int((BAND & fr).sum()), black=np.packbits(BLK))
    return sid, (f'{time.time() - t0:.0f}s segments {len(paths_)} px {off[-1]} ink coverage '
                 f'{cov_hit / max(cov_ink, 1):.2f} bold {bold.mean():.2f}')


if __name__ == '__main__':
    paths = sys.argv[1] if len(sys.argv) > 1 else 'configs/ground_paths.json'
    P = load_paths(paths); ids, _ = load_all(P)
    want = [s for s in sys.argv[2:] if s.startswith('s')] or sorted(ids)
    with Pool(int(os.environ.get('NPROC', 6))) as pool:
        for sid, msg in pool.imap_unordered(run_sheet, [(paths, s) for s in want]):
            print(sid, msg, flush=True)
