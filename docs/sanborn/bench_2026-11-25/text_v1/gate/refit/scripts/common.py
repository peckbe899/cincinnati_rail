"""Shared pieces of the character-or-not classifier (classifier step, 26 Nov 2026). numpy + cv2 only, so it runs on the
system python (cv2 4.13) inside finder3 and in the torch venv (cv2 5.0) for training.

A PIECE is a 0/1 mask cropped tight to its ink, at scan size (about 300 dpi). Its features are
  img    32 x 32 float image, 0 paper .. 1 ink: the mask scaled so its longest side is 28 px, centred, aspect kept, as in
         shapes/scripts/extract_glyphs.py (no turning: the piece is seen as it lies on the plate)
  scal   10 shape numbers that do not depend on how the piece is turned (all from the mask, so a synthetic glyph and a
         piece of the plate get them the same way):
           log longest side, log shortest side of the box, log area, log bar length and log bar thickness (second
           moments), stroke width (2 x mean distance to paper on the ridge), holes (1 - Euler number, 8-connected),
           area / (bar length x thickness), stroke length / bar length, aspect of the bounding box (short / long)
  hog    324 HOG numbers of img (32 px window, 16 px blocks, 8 px cells, 9 directions), computed in numpy so both
         pythons give the same numbers
"""
import numpy as np, cv2

S = 32; FIT = 28
SCAL_NAMES = ('log_ext', 'log_short', 'log_area', 'log_long', 'log_thick', 'sw', 'holes', 'fill_bar', 'slen_long', 'aspect')


def tight(m):
    ys, xs = np.nonzero(m)
    if not len(ys): return None
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.uint8)


def norm_img(m):
    h, w = m.shape; s = FIT / max(h, w)
    nh, nw = max(1, int(round(h * s))), max(1, int(round(w * s)))
    r = cv2.resize(m.astype(np.float32), (nw, nh), interpolation=cv2.INTER_AREA)
    out = np.zeros((S, S), np.float32); y0 = (S - nh) // 2; x0 = (S - nw) // 2
    out[y0:y0 + nh, x0:x0 + nw] = r
    return np.clip(out, 0, 1)


def euler8(m):
    b = m > 0
    if b.shape[0] < 2 or b.shape[1] < 2: return 1.0
    p = np.pad(b, 1)
    a, bb, c, d = p[:-1, :-1], p[:-1, 1:], p[1:, :-1], p[1:, 1:]
    s = a.astype(np.int8) + bb + c + d
    c1 = (s == 1).sum(); c3 = (s == 3).sum()
    cd = ((s == 2) & (((a & d) & ~bb & ~c) | ((bb & c) & ~a & ~d))).sum()
    return (c1 - c3 - 2 * cd) / 4.0


def scalars(m):
    m = (m > 0).astype(np.uint8); h, w = m.shape; ys, xs = np.nonzero(m); A = float(len(xs))
    mx, my = xs.mean(), ys.mean(); dx, dy = xs - mx, ys - my
    sxx, syy, sxy = (dx * dx).mean(), (dy * dy).mean(), (dx * dy).mean()
    t = (sxx + syy) / 2; d = np.sqrt(max(((sxx - syy) / 2) ** 2 + sxy ** 2, 0))
    lg = np.sqrt(12 * (t + d) + 1); th = np.sqrt(12 * max(t - d, 0) + 1)
    p = np.pad(m, 1); dt = cv2.distanceTransform(p, cv2.DIST_L2, 3)
    ridge = (dt > 0) & (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8)))
    sw = max(1.0, 2 * float(dt[ridge].mean())) if ridge.any() else 1.0
    holes = round(1 - euler8(m))
    return np.array([np.log(max(h, w)), np.log(min(h, w)), np.log(A), np.log(lg), np.log(th), sw, min(holes, 4),
                     A / max(1.0, lg * th), (A / sw) / max(1.0, lg), min(h, w) / max(h, w)], np.float32)


# ---- HOG in numpy: the same layout as cv2.HOGDescriptor((32,32),(16,16),(8,8),(8,8),9) (unsigned, 9 bins, L2-Hys).
# Not bit-equal to cv2 (no Gaussian block weighting, no bin interpolation in space); only used consistently.
def hog_batch(X):
    """X: (n, 32, 32) float -> (n, 324)"""
    X = X.astype(np.float32)
    gx = np.zeros_like(X); gy = np.zeros_like(X)
    gx[:, :, 1:-1] = X[:, :, 2:] - X[:, :, :-2]; gy[:, 1:-1, :] = X[:, 2:, :] - X[:, :-2, :]
    mag = np.hypot(gx, gy); ang = (np.degrees(np.arctan2(gy, gx)) % 180.0) / 20.0   # 9 bins of 20 deg
    b0 = np.floor(ang - 0.5).astype(int); f = (ang - 0.5) - b0; b1 = (b0 + 1) % 9; b0 = b0 % 9
    n = len(X)
    cy = np.repeat(np.arange(32) // 8, 32).reshape(32, 32); cx = np.tile(np.arange(32) // 8, 32).reshape(32, 32)
    cid = (cy * 4 + cx).ravel()
    M0 = (mag * (1 - f)).reshape(n, -1); M1 = (mag * f).reshape(n, -1); B0 = b0.reshape(n, -1); B1 = b1.reshape(n, -1)
    base = (np.arange(n)[:, None] * 144 + cid[None, :] * 9)
    flat = np.bincount((base + B0).ravel(), M0.ravel(), n * 144) + np.bincount((base + B1).ravel(), M1.ravel(), n * 144)
    cells = flat.reshape(n, 4, 4, 9).astype(np.float32); out = []
    for by in range(3):
        for bx in range(3):
            v = cells[:, by:by + 2, bx:bx + 2, :].reshape(n, 36)
            v = v / np.sqrt((v * v).sum(1, keepdims=True) + 1e-6); v = np.minimum(v, 0.2)
            v = v / np.sqrt((v * v).sum(1, keepdims=True) + 1e-6); out.append(v)
    return np.concatenate(out, 1).astype(np.float32)


def piece_features(masks):
    """list of 0/1 masks (any size) -> img (n,32,32), scal (n,10). Masks are cropped tight first."""
    imgs = np.zeros((len(masks), S, S), np.float32); sc = np.zeros((len(masks), len(SCAL_NAMES)), np.float32)
    for i, m in enumerate(masks):
        t = tight(m)
        if t is None: continue
        imgs[i] = norm_img(t); sc[i] = scalars(t)
    return imgs, sc


def wauc(p, y, w):
    """weighted AUC: probability that a random (weighted) positive scores above a random negative"""
    o = np.argsort(p, kind='stable'); p, y, w = p[o], y[o], w[o]
    wn = np.cumsum(w * (y == 0)); tot_n = wn[-1]; tot_p = (w * (y == 1)).sum()
    return float((w * (y == 1) * (wn - 0.5 * w * (y == 0))).sum() / max(tot_n * tot_p, 1e-9))
