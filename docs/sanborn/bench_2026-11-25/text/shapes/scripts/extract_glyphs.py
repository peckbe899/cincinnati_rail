"""Single glyphs from a Sanborn 1922 plate, normalised for size and rotation (shapes prototype, 25 Nov 2026).

    cd data/sanborn
    python -B bench_2026-11-25/text/shapes/scripts/extract_glyphs.py N [N ...] [--weak L --out DIR]

Reads only: cufp/22-N.jpg, cufp/N/png_alpha_s4.npy (paper), unet_data/N_bins.png (only to record how much of
each glyph ink_bins already calls text, bin 8). Writes only into bench_2026-11-25/text/shapes/glyphs/N.npz.

How (simple, no learning):
  1. ink = Lab L < 140 on the paper (as ink_bins.py). --weak L (test option): also pixels with L < that value which
     touch (8-connected, through such pixels) the L < 140 ink: faintly printed figures that break apart at 140 hold
     together (hysteresis). --out DIR writes DIR/N.npz instead of glyphs/N.npz. Thin straight lines are taken out first: ink kept by an opening
     with a 1 px line 51 px long (45 directions), except where the ink is 7 px thick or more (bold letters keep the
     pixels a pipe or sewer line runs through). 'touch' records the glyphs that touched a removed line.
  2. connected pieces of what is left (8-connected). A candidate glyph is a piece 4..130 px in its longest side, area >= 10,
     and not a long thin line piece (minAreaRect long/short <= 12, or long side < 30).
  3. words: two candidates of similar size (longest sides within 1.7x, both >= 10 px) whose centres are less than
     1.3x the bigger longest side apart are linked. Each glyph gets a local direction from its links (doubled-angle
     mean, so curved street names keep a local angle). A link more than 30 deg off either end's direction is dropped
     (a row above or below), and the directions are worked out again. Groups of linked glyphs are words.
  4. the reading direction is taken in (-90, +90] deg (image y down): left to right, and for vertical text reading
     downward. Text that reads upward comes out upside down here; the classifier step tries both ways round.
     A word whose glyphs are, once turned, wider than tall (median w/h > 1.15) is taken to be a column of upright
     glyphs, not a word: its glyphs are left at 0 deg. A glyph with no link is left at 0 deg.
  5. each glyph's own pixels (not its neighbours') are turned by its angle, cropped tight, scaled so the longest
     side is 28 px and centred in 32 x 32 (anti-aliased, 0 paper .. 255 ink).
"""
import os, sys, time
import numpy as np
import cv2
from scipy.spatial import cKDTree

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'glyphs')
INK_L = 140
EXT_MIN, EXT_MAX, AREA_MIN = 4, 130, 10
LINK_MIN, LINK_RATIO, LINK_DIST, LINK_TURN = 10, 1.7, 1.3, np.deg2rad(30)
S = 32; FIT = 28
LINE_LEN = 51


def line_kernel(length, ang):
    """as ink_bins.line_kernel: a 1 px line through the middle of a length x length square"""
    k = np.zeros((length, length), np.uint8); c = length // 2; d = np.array([np.cos(ang), np.sin(ang)]) * c
    cv2.line(k, tuple(np.round(c - d).astype(int).tolist()), tuple(np.round(c + d).astype(int).tolist()), 1, 1); return k


def local_angles(n, links, ang):
    """per node: doubled-angle mean of its links' angles (mod pi); nan where no link"""
    cx = np.zeros(n); cy = np.zeros(n)
    for (i, j), a in zip(links, ang):
        c, s = np.cos(2 * a), np.sin(2 * a)
        cx[i] += c; cy[i] += s; cx[j] += c; cy[j] += s
    out = 0.5 * np.arctan2(cy, cx)
    out[(cx == 0) & (cy == 0)] = np.nan
    return out


def groups(n, links):
    par = np.arange(n)
    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    for i, j in links:
        a, b = f(i), f(j)
        if a != b: par[a] = b
    return np.array([f(i) for i in range(n)])


def angdiff(a, b):
    return np.abs(((a - b + np.pi / 2) % np.pi) - np.pi / 2)


def norm_glyph(m):
    """m: uint8 0/1 tight crop -> 32x32 uint8, longest side FIT px"""
    h, w = m.shape; s = FIT / max(h, w)
    nh, nw = max(1, int(round(h * s))), max(1, int(round(w * s)))
    r = cv2.resize(m.astype(np.float32), (nw, nh), interpolation=cv2.INTER_AREA)
    out = np.zeros((S, S), np.float32); y0 = (S - nh) // 2; x0 = (S - nw) // 2
    out[y0:y0 + nh, x0:x0 + nw] = r
    return (np.clip(out, 0, 1) * 255).round().astype(np.uint8)


def extract(N):
    t0 = time.time()
    im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
    L = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0]
    al = np.load(f'cufp/{N}/png_alpha_s4.npy'); paper = cv2.resize(al, (W, H), interpolation=cv2.INTER_NEAREST) > 0
    ink = ((L < INK_L) & paper).astype(np.uint8)
    if WEAK:
        wk = ((L < WEAK) & paper).astype(np.uint8); n_, lw = cv2.connectedComponents(wk, connectivity=8)
        has = np.zeros(n_, bool); has[np.unique(lw[ink > 0])] = True; has[0] = False
        ink = has[lw].astype(np.uint8); del wk, lw
    del L
    bins = cv2.imread(f'unet_data/{N}_bins.png', 0) if os.path.exists(f'unet_data/{N}_bins.png') else None
    # take out thin straight lines (an opening with a 1 px line 51 px long, every 4 deg), but not where the ink is thick
    # (a bold street-name letter that a pipe or sewer line runs through keeps its pixels)
    lines = np.zeros_like(ink)
    for a in np.arange(0, 180, 4):
        lines |= cv2.morphologyEx(ink, cv2.MORPH_OPEN, line_kernel(LINE_LEN, np.deg2rad(a)))
    thick = cv2.dilate(cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))), np.ones((3, 3), np.uint8))
    thin = lines & (1 - thick); del lines, thick
    glyph_ink = ink & (1 - thin)
    near_line = cv2.dilate(thin, np.ones((5, 5), np.uint8))
    n, lb, st, cen = cv2.connectedComponentsWithStats(glyph_ink, connectivity=8)
    touch = np.bincount(lb.ravel(), near_line.ravel(), n) > 0; del near_line
    ext = np.maximum(st[:, 2], st[:, 3]); A = st[:, 4]
    cand = np.nonzero((ext >= EXT_MIN) & (ext <= EXT_MAX) & (A >= AREA_MIN))[0]
    cand = cand[cand > 0]
    keep = []; elong = []
    for i in cand:
        x, y, w, h = st[i, :4]
        ys, xs = np.nonzero(lb[y:y + h, x:x + w] == i)
        if len(xs) >= 5:
            (_, _), (rw, rh), _ = cv2.minAreaRect(np.c_[xs, ys].astype(np.float32))
            lo, hi = max(min(rw, rh), 1.0), max(rw, rh)
        else:
            lo, hi = 1.0, float(max(w, h))
        if hi / lo > 12 and hi >= 30: continue
        keep.append(i); elong.append(hi / lo)
    keep = np.array(keep); elong = np.array(elong)
    m = len(keep); c = cen[keep]; s = ext[keep].astype(float)
    # links
    T = cKDTree(c); links = []
    big = s >= LINK_MIN
    for a, js in enumerate(T.query_ball_point(c, LINK_DIST * s.clip(LINK_MIN))):
        if not big[a]: continue
        for b in js:
            if b <= a or not big[b]: continue
            sm = max(s[a], s[b])
            if sm / min(s[a], s[b]) > LINK_RATIO: continue
            if np.hypot(*(c[b] - c[a])) < LINK_DIST * sm: links.append((a, b))
    links = np.array(links, int).reshape(-1, 2)
    ang = np.arctan2(c[links[:, 1], 1] - c[links[:, 0], 1], c[links[:, 1], 0] - c[links[:, 0], 0]) if len(links) else np.zeros(0)
    for _ in range(2):
        la = local_angles(m, links, ang)
        ok = (angdiff(ang, la[links[:, 0]]) <= LINK_TURN) & (angdiff(ang, la[links[:, 1]]) <= LINK_TURN)
        links, ang = links[ok], ang[ok]
    la = local_angles(m, links, ang)
    g = groups(m, links)
    # reading direction in (-90, 90]
    la = np.where(la <= -np.pi / 2 + 1e-9, la + np.pi, la)
    la = np.where(la > np.pi / 2, la - np.pi, la)
    # glyph images
    imgs = np.zeros((m, S, S), np.uint8); hw = np.zeros((m, 2), np.float32); b8 = np.zeros(m, np.float32)
    turned = np.zeros(m, np.float32)
    def render(k, a):
        i = keep[k]; x, y, w, h = st[i, :4]; pad = int(0.5 * max(w, h)) + 2
        crop = np.zeros((h + 2 * pad, w + 2 * pad), np.uint8); crop[pad:pad + h, pad:pad + w] = (lb[y:y + h, x:x + w] == i)
        if a != 0:
            M = cv2.getRotationMatrix2D(((w + 2 * pad) / 2, (h + 2 * pad) / 2), np.rad2deg(a), 1.0)
            crop = (cv2.warpAffine(crop.astype(np.float32), M, crop.shape[::-1], flags=cv2.INTER_LINEAR) > 0.5).astype(np.uint8)
        ys, xs = np.nonzero(crop)
        if len(xs) == 0: return None, (0, 0)
        t = crop[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        return t, t.shape
    # a word whose turned glyphs are wider than tall is a column of upright glyphs: leave them at 0
    angle = np.where(np.isnan(la), 0.0, la)
    for gid in np.unique(g):
        mem = np.nonzero(g == gid)[0]
        if len(mem) < 2 or abs(angle[mem]).max() < np.deg2rad(5): continue
        asp = []
        for k in mem:
            t, (hh, ww) = render(k, angle[k])
            if t is not None: asp.append(ww / max(hh, 1))
        if np.median(asp) > 1.15: angle[mem] = 0.0; turned[mem] = -1
    raw = []; raw_off = np.zeros(m + 1, np.int64)   # the turned glyph at full size, for splitting touching figures later
    for k in range(m):
        t, (hh, ww) = render(k, angle[k])
        raw_off[k + 1] = raw_off[k]
        if t is None: continue
        imgs[k] = norm_glyph(t); hw[k] = (hh, ww)
        if max(hh, ww) >= 12: raw.append(t.ravel()); raw_off[k + 1] += t.size
        if bins is not None:
            i = keep[k]; x, y, w, h = st[i, :4]; mk = lb[y:y + h, x:x + w] == i
            b8[k] = (bins[y:y + h, x:x + w][mk] == 8).mean()
    # order along the word
    order = np.zeros(m, np.int32); gsize = np.zeros(m, np.int32)
    for gid in np.unique(g):
        mem = np.nonzero(g == gid)[0]; gsize[mem] = len(mem)
        if len(mem) > 1:
            a0 = np.arctan2(np.sin(2 * angle[mem]).mean(), np.cos(2 * angle[mem]).mean()) / 2
            if a0 <= -np.pi / 2 + 1e-9: a0 += np.pi
            u = np.array([np.cos(a0), np.sin(a0)]); order[mem[np.argsort(c[mem] @ u)]] = np.arange(len(mem))
    os.makedirs(OUT, exist_ok=True)
    np.savez_compressed(os.path.join(OUT, f'{N}.npz'), weak=WEAK or 0, plate=N, imgs=imgs, bbox=st[keep, :4].astype(np.int32), area=A[keep].astype(np.int32),
                        cen=c.astype(np.float32), angle=angle.astype(np.float32), hw=hw, word=g.astype(np.int32), wsize=gsize, order=order,
                        elong=elong.astype(np.float32), bin8=b8, column=turned, touch=touch[keep], size=(H, W),
                        raw=np.concatenate(raw).astype(np.uint8) if raw else np.zeros(0, np.uint8), raw_off=raw_off)
    print(f'plate {N}: {n - 1} ink pieces, {len(cand)} 4-130 px, {m} glyph candidates, {len(links)} links, '
          f'{(gsize >= 2).sum()} in words of 2+ ({len(np.unique(g[gsize >= 2]))} words), {int((turned == -1).sum())} reset as upright columns, '
          f'{100 * (b8 > 0.5).mean():.1f}% mostly bin 8 | {time.time() - t0:.0f} s')


WEAK = None
if __name__ == '__main__':
    a = sys.argv[1:]
    if '--weak' in a: WEAK = int(a[a.index('--weak') + 1]); a = a[:a.index('--weak')] + a[a.index('--weak') + 2:]
    if '--out' in a: OUT = os.path.abspath(a[a.index('--out') + 1]); a = a[:a.index('--out')] + a[a.index('--out') + 2:]
    for N in a:
        extract(N)
