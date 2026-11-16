"""Training pair for the block / street U-net from a placed plate (14 November 2026).

    cd data/sanborn
    ../../tools/sanborn/unet/.venv/Scripts/python.exe ../../tools/sanborn/unet/make_labels.py N [TAG]

The image is the plate scan at half size (about 2.4 px per metre). The label comes free from the placement: today's
parcel blocks (today/blocks_N.geojson, guided/parcels.py) drawn onto the plate through the plate's model (TAG, default
'guided'). Classes: 0 street or other open ground, 1 block, 255 ignore. Each block side is first slid onto the printed block
line beside it (snap), so the label's edges are straight and lie on the ruled lines. A side is verified when the scan is
clearly darker along it than beside it; a side that is not (no printed line there, or the snap missed) is blanked
out in a band, so only verified edges are taught. Ignored: off the paper, those bands, and one pixel either side of
every label edge. The guide keeps the unsnapped (rough) blocks.
Also writes the guide (N_guide.png): today's blocks and centre lines through the same model, the U-net's extra input
(unet.py shifts and erases it at random in training, so the network must find the real edge in the picture).
Writes unet_data/N_img.jpg, N_label.png, N_guide.png, N_meta.json (not committed: remade from the scan and the parcels).
"""
import json, os, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'guided'))
import streets as S  # noqa: E402
from scipy.interpolate import LinearNDInterpolator  # noqa: E402
from shapely.geometry import shape  # noqa: E402
J = S.J
N = sys.argv[1]; TAG = sys.argv[2] if len(sys.argv) > 2 else 'guided'; K, IGN, SNAP, TURN, MINSIDE, UNSURE, FAR, MARK, PIECE, VBAND, XR, FOLLOW = 2, 1, 18, 8, 28, 8, 35, 12, 150.0, 30, 14, 120.0
SP = S.SP; OUT = SP + 'unet_data/'; os.makedirs(OUT, exist_ok=True)
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
img = cv2.resize(full, (W // K, H // K), interpolation=cv2.INTER_AREA); h, w = img.shape[:2]
gx, gy = np.meshgrid(np.linspace(-300, W + 300, 120), np.linspace(-300, H + 300, 90)); P = np.c_[gx.ravel(), gy.ravel()]
inv = LinearNDInterpolator(J.world_many(f'22-{N}', P, TAG), P)
lab = np.zeros((h, w), np.uint8); cl = np.zeros((h, w), np.uint8); rough = np.zeros((h, w), np.uint8)
def ink_image(bgr):
    """Ben, 14 November 2026: use black/grey line detection. The printed lines are black or grey ink; the boundary bands
    (blue-green, pink, yellow, orange) and the building tints are colour. A pixel is ink when it is dark, or fairly dark
    and without colour; everything else is set to paper white, so only the printed lines are left to fit an edge to."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV); gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170))
    return cv2.GaussianBlur(np.where(ink, gray, 255).astype(np.uint8), (3, 3), 0).astype(np.float32)
grayF = ink_image(full)      # the snap and every edge test work on the black/grey ink of the full-size scan
def dark(a, b):
    d = b - a; L = np.hypot(*d); t = np.linspace(0.06, 0.94, max(10, int(L)))
    q = a + np.outer(t, d); x = q[:, 0].round().astype(int); y = q[:, 1].round().astype(int)
    ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
    return float(grayF[y[ok], x[ok]].mean()) if ok.sum() > 8 else 255.0
def on_line(a, b):
    """is the side on a printed line: at least 25 grey darker than the paper 3 to 6 px either side of it"""
    d = b - a; L = np.hypot(*d)
    if L < MINSIDE: return False
    nrm = np.array([-d[1], d[0]]) / L
    return np.mean([dark(a + nrm * o, b + nrm * o) for o in (-6, -3, 3, 6)]) - dark(a, b) > 25
# Ben, 15 November 2026: take the pipeline's outputs and fix the plate with them. The networks' block outlines
# (outlines.py, picks22_guided/22-N/outlines.json) give, for a parcel side the snap could not put on a printed line, the
# printed line the networks found beside it. Only an outline side that tests as on the print is used, and the moved side
# is tested against the ink again here; the area prediction must have block on the parcel's own side of the new line (so
# a side is not moved across an alley onto the next block's line).
_of = SP + f'picks22_guided/22-{N}/outlines.json'; OUTD, OUTANG = 45.0, 0.9945
OUTL = [(np.array(r['a'], float), np.array(r['b'], float)) for q in (json.load(open(_of, encoding='utf8')) if os.path.exists(_of) and '--no-outlines' not in sys.argv else []) for r in q if r['state'] == 'on print']
_pa = cv2.imread(OUT + f'{N}_pred_edge_v1.png', 0); NOUT = [0]
def from_outline(a, b, poly32):
    L = np.hypot(*(b - a)); d = (b - a) / L; nrm = np.array([-d[1], d[0]]); m = (a + b) / 2; best = None
    for p_, q_ in OUTL:
        e = q_ - p_; Le = np.hypot(*e); e = e / Le
        if abs(d @ e) < OUTANG: continue
        dist = abs(e[0] * (m - p_)[1] - e[1] * (m - p_)[0])
        if dist > OUTD or (best is not None and dist >= best[0]): continue
        t0, t1 = sorted(((p_ - a) @ d, (q_ - a) @ d))
        if min(L, t1) - max(0.0, t0) < 0.5 * L: continue
        a2, b2 = p_ + e * ((a - p_) @ e), p_ + e * ((b - p_) @ e)
        if not on_line(a2, b2): continue
        if _pa is not None:
            m2 = (a2 + b2) / 2; ins = nrm if cv2.pointPolygonTest(poly32, tuple(map(float, m + nrm * 12)), False) > 0 else -nrm
            v = [int(_pa[int(np.clip(y / K, 0, h - 1)), int(np.clip(x / K, 0, w - 1))]) for x, y in (m2 + ins * 14, m2 - ins * 14)]
            if v[0] < v[1] + 40: continue
        best = (dist, a2, b2)
    return None if best is None else (best[1], best[2])
def snap(poly):
    """Ben, 14 November 2026: teach it how a street looks. A block side is a straight ruled line. Each side of today's
    block (full-size px) is first slid sideways (up to SNAP px, about 3.5 m) to the darkest line beside it, then its two
    ends are moved separately (TURN px each) so the side can turn onto the printed line: the placed parcels are slightly
    rotated against the print, and a slide alone leaves the side crossing the line. Corners are rebuilt where
    neighbouring sides meet. Returns the polygon and how many sides were snapped."""
    v = cv2.approxPolyDP(poly.astype(np.float32).reshape(-1, 1, 2), 3.0, True)[:, 0, :].astype(float); n = len(v); moved = 0
    if n < 3: return poly, 0
    def fit_piece(a, b, rng):
        L = np.hypot(*(b - a)); nrm = np.array([-(b - a)[1], (b - a)[0]]) / (L or 1)
        ds = {o: dark(a + nrm * o, b + nrm * o) + 0.3 * abs(o) for o in range(-rng, rng + 1, 2)}; o1 = min(ds, key=ds.get)
        if ds[o1] >= np.median(list(ds.values())) - 10: return None
        best = min(((dark(a + nrm * (o1 + i), b + nrm * (o1 + j)), i, j) for i in range(-TURN, TURN + 1) for j in range(-TURN, TURN + 1)))
        return a + nrm * (o1 + best[1]), b + nrm * (o1 + best[2])
    sides = []; extra = {}
    for k in range(n):
        a, b = v[k], v[(k + 1) % n]; L = np.hypot(*(b - a)); a2, b2 = a, b
        if L >= MINSIDE:
            f = fit_piece(a, b, SNAP)
            if f is not None and on_line(*f): a2, b2 = f; moved += 1
            elif L >= 2 * PIECE:
                # a long side that does not lie on one printed line (a street that bends, a side a little further off):
                # cut it into pieces and fit each on its own, looking a little further
                m = int(np.ceil(L / PIECE)); pts = [a + (b - a) * i / m for i in range(m + 1)]; got = []
                for p, q in zip(pts[:-1], pts[1:]):
                    f2 = fit_piece(p, q, SNAP + 8); got.append(f2 if f2 is not None and on_line(*f2) else None)
                if sum(g_ is not None for g_ in got) >= 0.6 * m:
                    ends = [got[i] if got[i] is not None else (pts[i], pts[i + 1]) for i in range(m)]
                    a2, b2 = ends[0][0], ends[-1][1]; extra[k] = [(ends[i][1] + ends[i + 1][0]) / 2 for i in range(m - 1)]; moved += 1
            if a2 is a and OUTL and not on_line(a, b):
                f = from_outline(a, b, poly.astype(np.float32).reshape(-1, 1, 2))
                if f is not None: a2, b2 = f; moved += 1; NOUT[0] += 1
        sides.append((a2, b2))
    out = []
    for k in range(n):
        (a1, b1), (a2, b2) = sides[k - 1], sides[k]; d1, d2 = b1 - a1, b2 - a2; den = d1[0] * d2[1] - d1[1] * d2[0]; x = None
        if abs(den) > 0.15 * np.hypot(*d1) * np.hypot(*d2):
            x = a1 + ((a2[0] - a1[0]) * d2[1] - (a2[1] - a1[1]) * d2[0]) / den * d1
            if np.hypot(*(x - a2)) > 2.5 * SNAP: x = None
        out.append(x if x is not None else (b1 + a2) / 2)
        out += extra.get(k, [])
    return np.array(out), moved
_rf = SP + f'picks22_guided/22-{N}/edges_review.json'; PAPER = (lambda r_: r_.get('paper_boxes', []) + r_.get('ok_boxes', []))(json.load(open(_rf, encoding='utf8'))) if os.path.exists(_rf) else []   # sides kept as they are: the paper edge, or seen on the print by eye
def strip(mask, a, b, half, val=1):
    """fill the strip of half-width `half` (half-size px) along a-b (half-size px), with square ends: nothing past a or b"""
    a = np.asarray(a, float); b = np.asarray(b, float); d = b - a; L = np.hypot(*d)
    if L < 1e-6: return
    n = np.array([-d[1], d[0]]) / L * half
    cv2.fillPoly(mask, [np.array([a + n, b + n, b - n, a - n]).round().astype(np.int32)], val)
VER = []          # every verified edge (the green ones), full-size px: written as N_edge.png for the U-net
snapped = []; unsure = np.zeros((h, w), np.uint8); vband = np.zeros((h, w), np.uint8); nver = 0
nside = nmoved = 0
for f in json.load(open(SP + f'today/blocks_{N}.geojson', encoding='utf8'))['features']:
    q = inv(np.asarray(shape(f['geometry']).exterior.segmentize(3).coords)[:, :2])
    q = q[~np.isnan(q[:, 0])]
    if len(q) < 3: continue
    cv2.fillPoly(rough, [(q / K).astype(np.int32)], 1)
    q2, m = snap(q); nmoved += m; nside += len(q2); cv2.fillPoly(lab, [(q2 / K).round().astype(np.int32)], 1); snapped.append(q2.round(1).tolist())
    for k in range(len(q2)):                    # a side with no printed line under it is not taught as an edge: blank a band along it
        a_, b_ = q2[k], q2[(k + 1) % len(q2)]
        if on_line(a_, b_) or any(x0 <= (a_[0] + b_[0]) / 2 <= x1 and y0 <= (a_[1] + b_[1]) / 2 <= y1 for x0, y0, x1, y1 in PAPER):
            nver += 1   # on a printed line, or declared the trimmed paper edge (edges_review.json)
            VER.append((a_, b_))
            strip(vband, a_ / K, b_ / K, VBAND)   # ground beside a verified side, not past its ends (14 Nov: McNeil ran on north of where it stops)
        else: cv2.line(unsure, tuple((a_ / K).round().astype(int)), tuple((b_ / K).round().astype(int)), 1, 2 * UNSURE + 1)
for s_ in S.Plate(N).streets():                    # today's centre lines, for the guide input
    for l in getattr(s_['geom'], 'geoms', [s_['geom']]):
        q = inv(np.asarray(l.segmentize(3).coords)[:, :2]) / K; q = q[~np.isnan(q[:, 0])]
        if len(q) >= 2: cv2.polylines(cl, [q.astype(np.int32)], False, 255, 3)
json.dump(snapped, open(OUT + f'{N}_snapped.json', 'w', encoding='utf8', newline=chr(10)))      # block polygons on the printed lines, full-size px
cv2.imwrite(OUT + f'{N}_guide.png', np.dstack([rough * 255, cl, np.zeros_like(cl)]))   # channel 0: today's blocks, 1: today's centre lines
edge = cv2.morphologyEx(lab, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
band = cv2.dilate(edge.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * IGN + 1, 2 * IGN + 1))) > 0
alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > 0.5
out = lab.copy(); out[band] = 255; out[unsure > 0] = 255
# Streets from the plate itself (plate_streets.py; Ben, 14 November 2026: pull all the streets). Today's parcels miss a
# street that was realigned or is gone (Reading, Ross on 82A) and have streets that were not there in 1922.
#  - a traced piece the parcel label does not already show as street is painted as street between its two block lines
#    (only when both lines are known; a band along a piece with no width is blanked);
#  - parcel "street" with no traced street within FAR px is blanked: it is not a street of the plate.
added = np.zeros((h, w), np.uint8); nadd = nblank = 0
if True:           # on every plate: a parcel street is taught only where the print gives evidence for it
    near = np.zeros((h, w), np.uint8)
    for p in (json.load(open(OUT + f'{N}_streets.json', encoding='utf8')) if os.path.exists(OUT + f'{N}_streets.json') else []):
        a_, b_ = np.array(p['a']) / K, np.array(p['b']) / K
        strip(near, a_, b_, FAR)
        t = np.linspace(0, 1, 30); q = (a_ + np.outer(t, b_ - a_)).round().astype(int); ok = (q[:, 0] >= 0) & (q[:, 0] < w) & (q[:, 1] >= 0) & (q[:, 1] < h)
        if ok.sum() < 10 or (lab[q[ok, 1], q[ok, 0]] == 0).mean() >= 0.6: continue          # the parcels already have this street here
        # 14 Nov 2026: the automatic search is not trusted to place an edge (it took pipe and lot lines for block lines):
        # a traced street the parcels lack is only blanked here; it is taught once it is marked by eye (streets_marked.json)
        if False: pass
        else: cv2.line(added, tuple(a_.round().astype(int)), tuple(b_.round().astype(int)), 2, 2 * FAR + 1); nblank += 1
    # 14 Nov 2026 (completeness check): the readers' traces have gaps, so "no traced street nearby" alone blanked real
    # streets (Allison by the Board of Education). A parcel street is also kept where it runs beside a side verified on
    # the print, or round a crossing both readers placed. A today-only street has neither.
    near[vband > 0] = 1
    OBSF = SP + f'picks22_guided/22-{N}/observations.json'
    XS = [c for c in json.load(open(OBSF, encoding='utf8'))['crossings']] if os.path.exists(OBSF) else []
    MF_ = SP + f'cufp/{N}/matches.json'      # a plate with no guided reading: its own fitted controls (blind picks)
    if not XS and os.path.exists(MF_): XS = [m_ for m_ in json.load(open(MF_, encoding='utf8')) if m_.get('used')]
    for c in XS: cv2.circle(near, (int(round(c['x'] / K)), int(round(c['y'] / K))), FAR, 1, -1)
    out[(out == 0) & (near == 0)] = 255
    # a traced street the parcels lack: the band along it is blanked only over what the parcels call block. A trace runs
    # straight between the readers' points, so it can cut across a real, verified street beside it (Allison, Woodlawn).
    out[(added == 2) & (out == 1)] = 255; out[added == 1] = 0
    ring = cv2.morphologyEx((added == 1).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0; out[ring] = 255
# Streets marked by eye on full-size crops (picks22_guided/22-N/streets_marked.json; Ben, 14 November 2026: go in
# yourself and read them). Each has its two edges as lines in plate px. Every piece of an edge is moved onto the printed
# line beside it when there is a clear one within MARK px (a reading is good to about 5-10 px); an edge with no printed
# line (the paper's edge, a railway side) stays as read. The strip between the edges is taught as street.
nmark = nmark_on = 0; MF = SP + f'picks22_guided/22-{N}/streets_marked.json'
if os.path.exists(MF):
    loose = []
    def ink(a, b):
        d = b - a; L = np.hypot(*d); t = np.linspace(0.04, 0.96, max(10, int(L))); q = a + np.outer(t, d)
        x = q[:, 0].round().astype(int); y = q[:, 1].round().astype(int); ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
        if ok.sum() <= 8: return 0.0
        # a point is on ink when it is dark, or (along a colour band, where ink prints lighter) clearly darker than the
        # paper 5 px either side of it
        nrm = np.array([-d[1], d[0]]) / (L or 1); g0 = grayF[y[ok], x[ok]]; side = []
        for o in (-5, 5):
            xs = np.clip((q[ok, 0] + nrm[0] * o).round().astype(int), 0, W - 1); ys = np.clip((q[ok, 1] + nrm[1] * o).round().astype(int), 0, H - 1); side.append(grayF[ys, xs])
        return float(((g0 < 150) | ((g0 < 185) & (g0 < np.minimum(side[0], side[1]) - 18))).mean())
    def refine(pl):
        """a read edge follows the printed line in pieces of about FOLLOW px: each piece is moved sideways (up to MARK + 3
        px) and turned (its ends up to 5 px apart) to where most of its length lies on ink. A piece is on the print when
        at least 80% of it is ink (a dashed pipe line is about half) or it passes the darker-than-beside test."""
        pl = np.array(pl, float); pts = [pl[0]]
        for a_, b_ in zip(pl[:-1], pl[1:]):
            m = max(1, int(round(np.hypot(*(b_ - a_)) / FOLLOW))); pts += [a_ + (b_ - a_) * i / m for i in range(1, m + 1)]
        segs = []; hit = 0
        for a_, b_ in zip(pts[:-1], pts[1:]):
            L = np.hypot(*(b_ - a_)); nrm = np.array([-(b_ - a_)[1], (b_ - a_)[0]]) / (L or 1); a2, b2 = a_, b_
            if L >= MINSIDE:
                best = max(((ink(a_ + nrm * i, b_ + nrm * j) - 0.004 * (abs(i) + abs(j)), i, j) for i in range(-MARK - 3, MARK + 4) for j in range(-MARK - 3, MARK + 4) if abs(i - j) <= 5))
                c2, d2 = a_ + nrm * best[1], b_ + nrm * best[2]
                if ink(c2, d2) >= 0.8 or on_line(c2, d2): a2, b2 = c2, d2; hit += 1; VER.append((c2, d2))
                elif not any(x0 <= (a_[0] + b_[0]) / 2 <= x1 and y0 <= (a_[1] + b_[1]) / 2 <= y1 for x0, y0, x1, y1 in PAPER): loose.append((a_, b_))   # read, but no printed line found under it: not taught along it
            segs.append((a2, b2))
        v = [segs[0][0]] + [(segs[k][1] + segs[k + 1][0]) / 2 for k in range(len(segs) - 1)] + [segs[-1][1]]
        return np.array(v), hit, len(segs)
    marked = np.zeros((h, w), np.uint8); medge = np.zeros((h, w), np.uint8); munsure = np.zeros((h, w), np.uint8); refined = []
    for m in json.load(open(MF, encoding='utf8')):
        # an edge with "left_kind"/"right_kind" other than "line" has no printed line (the trimmed paper edge, a railway
        # side): it stays exactly as read
        keep = lambda pl: (np.array(pl, float), 0, len(pl) - 1)
        l, hl, nl = refine(m['left']) if m.get('left_kind', 'line') == 'line' else keep(m['left'])
        r, hr, nr = refine(m['right']) if m.get('right_kind', 'line') == 'line' else keep(m['right'])
        nmark += nl + nr; nmark_on += hl + hr
        cv2.fillPoly(marked, [(np.r_[l, r[::-1]] / K).round().astype(np.int32)], 1)
        # the band beside a marked edge has square ends (15 Nov 2026, plate 45): a thick line's round cap ran past the
        # edge's end and cut a notch of block into the cross street at every T-junction
        for e in (l, r):
            for a_, b_ in zip(e[:-1], e[1:]): strip(medge, a_ / K, b_ / K, UNSURE + 2)
        for e, kd in ((l, m.get('left_kind', 'line')), (r, m.get('right_kind', 'line'))):
            if kd == 'unsure': cv2.polylines(munsure, [(e / K).round().astype(np.int32)], False, 1, 2 * UNSURE + 1)   # read but not settled: not taught along it
        refined.append(dict(name=m['name'], left=l.round(1).tolist(), right=r.round(1).tolist(), left_kind=m.get('left_kind', 'line'), right_kind=m.get('right_kind', 'line'), edge_pieces=nl + nr, on_printed_line=hl + hr))
    # a parcel side that is not on a printed line but has a marked edge beside it: the marked edge decides. Its blanked
    # band becomes street inside the marked street and block outside it.
    fix = (unsure > 0) & (medge > 0); out[fix & (marked == 0)] = 1
    near_m = cv2.dilate(marked, np.ones((2 * UNSURE + 5, 2 * UNSURE + 5), np.uint8)) > 0
    out[(out == 0) & near_m & (marked == 0) & (medge > 0)] = 1          # parcel "street" just outside a marked edge is block
    json.dump(refined, open(OUT + f'{N}_marked_refined.json', 'w', encoding='utf8', newline=chr(10)), indent=1)
    out[marked == 1] = 0
    for a_, b_ in loose: cv2.line(munsure, tuple((a_ / K).round().astype(int)), tuple((b_ / K).round().astype(int)), 1, 2 * UNSURE + 1)
    out[munsure == 1] = 255
    ring = cv2.morphologyEx(marked, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0; out[ring & (lab == 1)] = 255
# ground declared block by eye (edges_review.json "block_polys"): only what is blank becomes block, a taught street stays
if os.path.exists(_rf):
    for poly in json.load(open(_rf, encoding='utf8')).get('block_polys', []):
        pm = np.zeros((h, w), np.uint8); cv2.fillPoly(pm, [(np.array(poly, float) / K).round().astype(np.int32)], 1); out[(pm == 1) & (out == 255)] = 1
# ground seen by eye NOT to be a street although a parcel side beside it tests as on a printed line (15 Nov 2026, plate
# 80: today's street lying on the canal bank, strips beside Broerman where a parcel side sits on a pipe line):
# edges_review.json "not_street_polys". Taught street inside becomes not taught, and verified edges inside are dropped.
if os.path.exists(_rf):
    for poly in json.load(open(_rf, encoding='utf8')).get('not_street_polys', []):
        pm = np.zeros((h, w), np.uint8); cv2.fillPoly(pm, [(np.array(poly, float) / K).round().astype(np.int32)], 1); out[(pm == 1) & (out == 0)] = 255
        VER = [(a_, b_) for a_, b_ in VER if cv2.pointPolygonTest(np.array(poly, np.float32).reshape(-1, 1, 2), tuple(map(float, (np.asarray(a_) + np.asarray(b_)) / 2)), False) < 0]
# the middle of every crossing the readers agreed on is street (XR px at half size): a junction is never left blank
if os.path.exists(SP + f'picks22_guided/22-{N}/observations.json'):
    for c in json.load(open(SP + f'picks22_guided/22-{N}/observations.json', encoding='utf8'))['crossings']:
        cv2.circle(out, (int(round(c['x'] / K)), int(round(c['y'] / K))), XR, 0, -1)
out[~alpha] = 255
cv2.imwrite(OUT + f'{N}_img.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 92]); cv2.imwrite(OUT + f'{N}_label.png', out)
# Ben, 14 November 2026: apply the green limits to the U-net. The verified edges themselves, one pixel wide at half size:
# the U-net weights its loss by nearness to them and has a second output that must draw them (unet.py).
vedge = np.zeros((h, w), np.uint8)
for a_, b_ in VER: cv2.line(vedge, tuple((np.asarray(a_) / K).round().astype(int)), tuple((np.asarray(b_) / K).round().astype(int)), 255, 1)
vedge[~alpha] = 0; cv2.imwrite(OUT + f'{N}_edge.png', vedge)
json.dump([[np.asarray(a_).round(1).tolist(), np.asarray(b_).round(1).tolist()] for a_, b_ in VER], open(OUT + f'{N}_verified.json', 'w', encoding='utf8', newline=chr(10)))   # the same edges as full-size lines, for edgenet.py
json.dump(dict(plate=N, tag=TAG, scale=K, ignore_px=IGN, verified_edges=len(VER), sides=nside, sides_snapped=nmoved, sides_on_printed_line=nver, sides_from_outlines=NOUT[0], plate_pieces_added=nadd, plate_pieces_blanked=nblank, marked_edge_pieces=nmark, marked_on_printed_line=nmark_on, size=[w, h], block=float((out == 1).mean()), street=float((out == 0).mean()), ignore=float((out == 255).mean())),
          open(OUT + f'{N}_meta.json', 'w', encoding='utf8', newline='\n'), indent=1)
full_vis = full.copy()                       # full-size check: snapped block sides (green) on the scan
for q in snapped:
    q = np.array(q)
    for k in range(len(q)): cv2.line(full_vis, tuple(q[k].round().astype(int)), tuple(q[(k + 1) % len(q)].round().astype(int)), (0, 170, 0) if on_line(q[k], q[(k + 1) % len(q)]) else (0, 0, 230), 1, cv2.LINE_AA)   # green: on a printed line; red: not verified
cv2.imwrite(OUT + f'{N}_snapcheck.jpg', full_vis, [cv2.IMWRITE_JPEG_QUALITY, 88])
vis = (img * 0.55 + 100).astype(np.uint8)      # the label as taught: street blue, block untouched, not taught grey
vis[out == 0] = (vis[out == 0] * 0.35 + np.array([200, 70, 0]) * 0.65).astype(np.uint8)
vis[(out == 255) & alpha] = (vis[(out == 255) & alpha] * 0.5 + np.array([120, 120, 120]) * 0.5).astype(np.uint8)
cv2.imwrite(OUT + f'{N}_check.jpg', vis, [cv2.IMWRITE_JPEG_QUALITY, 85])
print(json.load(open(OUT + f'{N}_meta.json')))
