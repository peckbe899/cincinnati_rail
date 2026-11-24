"""Training data for the second blank-guide pair (area_ng2, lines_ng2): one folder per plate (23 November 2026).

    cd data/sanborn
    PY=../../tools/sanborn/unet/.venv/Scripts/python.exe        (system python works too, except for verify)
    $PY -B ../../tools/sanborn/unet/make_labels_v2.py label  43 45 80 82A   [--out DIR]
    $PY -B ../../tools/sanborn/unet/make_labels_v2.py map    1A             [--out DIR] [--val-x X]
    $PY -B ../../tools/sanborn/unet/make_labels_v2.py pseudo 30 60B ...     [--out DIR] [--hi .. --lo .. ...]
    $PY -B ../../tools/sanborn/unet/make_labels_v2.py verify 43 45 80 82A   [--out DIR]   (venv: torch, unet.py, edgenet.py)
    $PY -B ../../tools/sanborn/unet/make_labels_v2.py compare 1A --pseudo DIR --map DIR [--json FILE]

Ben, 23 November 2026: "1A is done. let's try training on a number of them. you should choose them by complexity and
size, with what you think are enough plates to teach the U-net sufficiently". The default output is data/sanborn/train_v2/
(one subfolder per plate, and manifest.json); --out DIR writes elsewhere (a test). Plates 44 and 90 (Ben's ground
truth and his planned second one) are never written into train_v2/: 44 is the untouched benchmark.

FORMAT (every plate folder; half size = the scan at 1/2, as make_labels.py makes it; full size = cufp/22-N.jpg)
  img.jpg     half size RGB scan, exactly as make_labels.py makes N_img.jpg (INTER_AREA, JPEG quality 92)
  label.png   half size, uint8: 0 street (or other open ground), 1 block, 255 not taught
  edge.png    half size, as make_labels.py's N_edge.png: the edges the area net's third output draws (unet.load_edge)
  lines.png   FULL size, uint8: the line net's target exactly as edgenet.load builds t (1 line, 0 not, 255 not scored)
  area_in.png half size, P(block)*255: the line net's 7th channel (always the batch's unet_data/N_pred_area_ng1.png)
  valmask.png (map plates only) half size, 1 = validation ground, never trained on: x >= --val-x (half px), by default
              the right-hand quarter of the image (x >= int(0.75 * width), the same cut unet.train makes). train_v2/1A
              uses --val-x 1420, the centre line of Elm Street (integrator, 23 Nov: the image's right quarter holds
              10% of 1A's paper and 1 of Ben's 21 blocks; right of Elm St are 35% of the paper and 9 blocks, none cut)
  meta.json   source, what made each file and its sha256, the thresholds, counts, the scale in ft per inch
  streetmap.json (map plates only) Ben's street map, as street_map.py writes it (never into streetmap/)
The full-size scan is not copied: the line net reads cufp/22-N.jpg (its sha256 is in meta.json).
manifest.json (in the output folder): every plate, its source, and its files' sha256; 'content_sha256' is the sha256
of the plates section (json, sorted keys), the hash the trainers record.

LOADING (what 'verify' does; for 43, 45, 80 and 82A it gives today's training arrays pixel for pixel)
  area net  x = dstack(imread(img.jpg)[:, :, ::-1], zeros, zeros) (the blank guide); label = imread(label.png, 0);
            edge weights and edge target from imread(edge.png, 0) by unet.load_edge's formulas.
  line net  full = imread(cufp/22-N.jpg); x = dstack(full[:, :, ::-1], edgenet.ink_image(full)[0], zeros, zeros,
            resize(imread(area_in.png, 0), (W, H), INTER_LINEAR)); t = imread(lines.png, 0); weights 1, NEG_INK on ink
            where t == 0, POS where t == 1 (edgenet.load's).
  valmask   half size; for the line net resize it to full size with INTER_NEAREST.

THE THREE SOURCES
label   43, 45, 80, 82A: today's training inputs, unchanged. img.jpg, label.png, edge.png and area_in.png are copied
        byte for byte from unet_data/N_img.jpg, N_label.png, N_edge.png and N_pred_area_ng1.png; lines.png is
        edgenet.load's t built from N_label.png, N_verified.json and the paper outline, by the same code. 'verify'
        loads each plate through the new folder and through unet.load, unet.load_edge and edgenet.load (blank guide,
        --area area_ng1) and compares every array pixel for pixel. area_in.png is IN SAMPLE for these four: area_ng1
        was trained on them.
map     a plate whose lines Ben has checked in the line editor (picks22_guided/22-N/edges_ben.json).
        - Street map: street_map.editor_lines (the editor's lines with his edits) closed as street_map.py closes them
          (ends extended TOL px, polygonized, faces of 400 px2 or more): written as streetmap.json in the plate folder.
        - Area label: his closed blocks are 1 (a face under NARROW px across, an alley closed at both ends or a sliver,
          is 255). Street: from every point of each of his lines a ray goes out on the side that is not block (the side
          a probe POKE px out does not find in a closed block; where neither side is a closed block, the side that meets
          another of his lines, running within PAR_DEG degrees of parallel, within WPAIR_FT ft while the other side meets
          no line nearer than 1.5 times as far) up to
          the first of his lines, a closed block or the paper's edge; the ground it crosses is street when that stop is
          within WMAX_FT ft, else only the first BAND_FT ft is (open land beyond: the ground next to the line is still
          not block). Everything else is 255, and so is a band of 1 px either side of every block's edge (as
          make_labels.py's IGN) and the ground off the paper.
        - Line target: his printed and drawn lines are positive, LINE px wide; the GAP px margin beside them is 255
          (edgenet.load's rules); his sheet-edge and no-printed-line sides are 255 with the same margin (no ink to
          learn); every other pixel of the ground the area label teaches is negative, and so is a strip WRONG_PX wide
          along each line he marked wrong (his decision that it is not a street side); the rest is 255.
        - edge.png: his printed and drawn lines, 1 px at half size (as N_edge.png draws the verified edges).
        - valmask.png: x >= --val-x (half px), by default the right-hand quarter of the image.
pseudo  a batch plate (never placed): the merged outline step's own outputs, kept only where they are confident. These
        are the networks' guesses, filtered; they cannot teach what the networks never see (see LIMITS).
        Inputs: picks22_guided/22-N/outlines.json (block polygons, street holes cut: ink_bins.block_ground's rule),
        unet_data/N_pred_area_ng1.png, N_lines_lines_ng1.png, N_edges.json (green = 'on print') and, on an uncut PDF
        sheet, N_mapground.png (the map ground; elsewhere the paper).
        Thresholds (PSEUDO; d and ds in half-size px, ms, mr and mu in full-size px, me and ll in feet on the ground):
        - Block: inside a block polygon AND P(block) > hi (0.95) AND at least d (8) px inside the polygon's edge.
        - Street: outside every polygon AND P(block) < lo (0.05) AND at least ds (6) px from a polygon AND on the map
          ground.
        - Not taught (255): everything else, and the alley strips (below).
        - Line target: positive = the green editor lines (edit_server.clean of N_edges.json, state green), LINE px, GAP
          margin 255. Negative only where confidently not a block line: at least ms (12) px from every outline side and
          every orange editor line, at least mr (6) px from any line-net response above tl (0.1), at least mu (4) px
          from ground the area label leaves untaught, at least me (20) ft from the paper's edge (a street side drawn
          along the edge has no block on the plate to show it), and not within the GAP margin of a long straight ink
          line (ll, 80 ft or longer) in the block ground: such a line may be a block line the networks missed (an alley
          side, a narrow street); it also takes the long lot lines out of the negatives. The rest is 255.
        - Alley strips (alley True; ALLEY): two long straight parallel ink lines 8-45 ft apart, overlapping over most of
          their length, with no building tint between them (Lab a*b* more than 12 from the paper's colour on at most
          15% of the strip), no line right across the strip (a lot is closed by its rear line), and running across the
          block (carried on along its line it leaves the block ground within 40 ft at both ends, or meets a strip found
          in the first pass): an alley or narrow street the networks missed. The strip is 255 in the area label (and so
          the line negatives keep mu px off it). A missed single street side is not caught (ll covers its line only).
        - bigx (off, 0): block is taught only in polygons at most bigx times the plate's median block polygon. The
          networks call open land (creek, rail corridors, farm tracts) block; Ben's map leaves that ground undecided,
          so it cannot be scored, and whether it is block is a convention he has not settled.
        - cap (1.0; integrator, 23 Nov): block is taught only in polygons of at most cap x CAP_ACRES acres at the
          plate's scale (16.97 at 100 ft, 35.46 at 200 ft: the 98th percentile of the labelled plates' block pieces,
          select/pseudo_area.py --strict). A bigger polygon is a merge across streets, open land, the river or a rail
          yard far more often than a real block (on the ten chosen plates: 51's landing, 68's Zoo, 76's KEY and
          Duck Creek ground, 79's and 89's open land). Its ground is 255.
        - KEY (integrator): the printed KEY's box from bench_2026-11-21/census/rail_key.json (full px, KEY_PAD px
          more) is 255 in the label and the line target, and has no edge. On the PDF sheets the map ground already
          leaves it out; on a cut plate (76) nothing else does.
        - Off the map ground (integrator): on a PDF sheet the line target is 255 more than MG_PAD px off the map ground
          (N_mapground.png), so a green line in the margin, a title or an inset frame is not taught as a block line.
        - Hand masks (--mask FILE; integrator): boxes (full px) of ground seen by eye in the overlays to be taught
          wrongly (a bridge approach across streets, a parkway median, blank paper beyond the mapped ground): 255 in
          the label and the line target, no edge. The file and its sha256 are in meta.json.
        - edge.png: the green lines at half size, 1 px (none in the KEY box, off the map ground or in a hand mask).
        - The thresholds were tuned on plate 1A only (pseudo labels from 1A's batch outputs against 1A's map labels
          from Ben; bench_2026-11-23/train/labels/tune/); the same comparison is reported on 44 (in a test folder,
          never train_v2/).

LIMITS (the 21 Nov reviews, docs/sanborn/ml_review_2026-11-21 and bench_2026-11-21): pseudo labels repeat the networks'
own mistakes where they are confident (confirmation bias); the 200-ft mid-block alleys the networks never see are
taught as block unless the alley test catches them; the 400-ft sheets and the suspect plates have poor outputs, so
pseudo labels there are poor; the networks are brittle to pen width and scale.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, time
import numpy as np
import cv2


def _repo():
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.exists(os.path.join(d, 'tools', 'sanborn', '_ws.py')) and os.path.exists(os.path.join(d, 'configs', 'sanborn_paths.json')): return d
        p = os.path.dirname(d)
        if p == d: sys.exit('make_labels_v2: no repo (tools/sanborn/_ws.py) above this file')
        d = p


REPO = _repo(); TOOLS = os.path.join(REPO, 'tools', 'sanborn', 'unet')   # the pipeline's own modules (also when this file is run from a staging folder)
sys.path.insert(0, TOOLS); sys.path.insert(0, os.path.dirname(TOOLS))
import _ws  # noqa: E402
SP = _ws.DATA; U = SP + 'unet_data/'; OUT_DEFAULT = SP + 'train_v2/'
TEST_ONLY = ('44', '90')               # Ben's ground truth (the benchmark) and his planned second truth plate: never in train_v2/
NO_WRITE = ('unet_data', 'picks22_guided', 'streetmap', 'cufp')   # folders of data/sanborn this script never writes into
K, LINE, GAP, TOL = 2, 3, 4, 3         # half size; edgenet.py's LINE, GAP and TOL (full-size px)
AREA_IN, LINES_NET = 'area_ng1', 'lines_ng1'
# map labels
SM_TOL, SM_MIN_FACE, NARROW = 1.5, 400.0, 60.0          # street_map.py's closing (ends extended 1.5 px, faces of 400 px2 or more); a face under 60 px across is not taught
POKE, WMAX_FT, WPAIR_FT, BAND_FT, WRONG_PX, PAR_DEG = 4, 130.0, 110.0, 20.0, 11, 12.0
# pseudo labels (tuned on 1A only: see the docstring and the tuning record in meta.json)
PSEUDO = dict(hi=0.95, lo=0.05, d=8, ds=6, tl=0.1, ms=12, mr=6, mu=4, me=20.0, ll=80.0, gmin=0.0, bigx=0.0, cap=1.0, alley=True)   # gmin: shortest green line taught, ft (0: all); bigx, cap: see the docstring (0: off)
# integrator, 23 Nov: the size cap, the KEY box and the map ground (see the docstring, pseudo)
CAP_ACRES = {100: 16.97, 200: 35.46}   # 1.0 x the 98th percentile of the block pieces of the labelled plates' N_label.png at that scale (43 at 100 ft; 45, 80, 82A at 200 ft), acres: bench_2026-11-23/train/select/pseudo_area.py --strict
KEY_JSON, KEY_PAD, MG_PAD = SP + 'bench_2026-11-21/census/rail_key.json', 20, 12   # the printed KEY's box (full px) from the 21 Nov census; its margin and the map ground's, full px
ALLEY = dict(min_ft=8.0, max_ft=45.0, min_len_ft=80.0, ang_deg=2.0, overlap=0.6, tint=12.0, tint_share=0.15, cross=True, reach_ft=40.0, passes=2, pad=4, ang_join=1.5, off_join=4.0, gap_ft=8.0, cont=0.8)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def rel(path):
    p = os.path.abspath(path).replace('\\', '/'); r = REPO.replace('\\', '/') + '/'
    return p[len(r):] if p.startswith(r) else p


def git_head():
    try: return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO, capture_output=True, text=True, timeout=20).stdout.strip() or None
    except Exception: return None


def scale_ft(N):
    t = json.load(open(SP + 'scale_table.json', encoding='utf8')).get(N) or {}
    return t.get('ft_per_inch')


def check_out(out, N):
    """refuse a write that would put 44 or 90 into train_v2/, or anything into the pipeline's own folders"""
    o = os.path.normcase(os.path.abspath(out)); tv = os.path.normcase(os.path.abspath(OUT_DEFAULT))
    if N in TEST_ONLY and (o == tv or o.startswith(tv + os.sep)): sys.exit(f'plate {N} is test only (Ben\'s truth): never written into train_v2/. Use --out DIR for a test.')
    for f in NO_WRITE:
        p = os.path.normcase(os.path.abspath(SP + f))
        if o == p or o.startswith(p + os.sep): sys.exit(f'--out {out}: never writes into data/sanborn/{f}/')


def scan(N):
    full = cv2.imread(SP + f'cufp/22-{N}.jpg')
    if full is None: sys.exit(f'no scan cufp/22-{N}.jpg')
    return full


def alpha_half(N, w, h):            # make_labels.py's paper at half size
    return cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > 0.5


def alpha_full(N, W, H):            # edgenet.load's paper at full size
    return cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5


def half_img(full):
    H, W = full.shape[:2]; return cv2.resize(full, (W // K, H // K), interpolation=cv2.INTER_AREA)


def line_target(H, W, pos, taught, alpha, blank=None):
    """edgenet.load's t: pos lines (full-size (a, b) pairs) drawn LINE px = 1; the margin of GAP px beside them 255; ground
    not taught (taught False) 255 except the lines and their margin; off the paper 255. blank (bool, full size): more
    ground not scored (sheet edges, orange lines), never over a positive. With blank None this is edgenet.load's code."""
    line = np.zeros((H, W), np.uint8)
    for a, b in pos: cv2.line(line, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), 1, LINE)
    near = cv2.dilate(line, np.ones((2 * (LINE + GAP) + 1, 2 * (LINE + GAP) + 1), np.uint8)) > 0
    t = np.where(line > 0, 1, 0).astype(np.uint8)
    t[~taught & ~near] = 255
    t[near & (line == 0)] = 255
    if blank is not None: t[blank & (line == 0)] = 255
    t[~alpha] = 255
    return t


def raster(lines, shape, scale=1.0, thick=1, val=1):
    m = np.zeros(shape, np.uint8)
    for a, b in lines: cv2.line(m, tuple(np.round(np.asarray(a, float) * scale).astype(int)), tuple(np.round(np.asarray(b, float) * scale).astype(int)), val, thick)
    return m


def block_ground(polys, h, w, scale=1.0):
    """ink_bins.block_ground at another size: every block polygon filled, the street holes (sides with hole=True) cut
    out, a block lying in a hole filled again. uint8, 1 = block"""
    rings = lambda hole: [np.round(np.array([s['a'] for s in p], float) * scale).astype(np.int32) for p in polys if p and bool(p[0].get('hole')) == hole and len(p) >= 3]
    B = np.zeros((h, w), np.uint8); blk = rings(False); hol = rings(True)
    for r in blk: cv2.fillPoly(B, [r], 1)
    if hol:
        Hm = np.zeros((h, w), np.uint8)
        for r in hol: cv2.fillPoly(Hm, [r], 1)
        B[Hm > 0] = 0
        for r in blk:
            c = np.clip(r, 0, [w - 1, h - 1])
            if Hm[c[:, 1], c[:, 0]].mean() > 0.5: cv2.fillPoly(B, [r], 1)
    return B


def edge_band(lab):
    """make_labels.py's band round every label edge (IGN = 1): the gradient of the block mask, dilated by a 3 px ellipse"""
    e = cv2.morphologyEx((lab == 1).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    return cv2.dilate(e.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))) > 0


def save_png(path, a):
    if not cv2.imwrite(path, a): sys.exit(f'could not write {path}')


def copy(src, dst):
    if not os.path.exists(src): sys.exit(f'missing {rel(src)}')
    shutil.copyfile(src, dst); return dict(made=f'copied byte for byte from {rel(src)}', source_sha256=sha(src))


def finish(N, out, source, files, extra):
    """meta.json in the plate folder and the plate's entry in out/manifest.json (after checking the format)"""
    d = out + N + '/'; shas = {f: sha(d + f) for f in sorted(files)}
    lab, t, ai = cv2.imread(d + 'label.png', cv2.IMREAD_UNCHANGED), cv2.imread(d + 'lines.png', cv2.IMREAD_UNCHANGED), cv2.imread(d + 'area_in.png', cv2.IMREAD_UNCHANGED)
    im = cv2.imread(d + 'img.jpg'); h, w = im.shape[:2]; H, W = t.shape
    bad = [m for ok, m in ((lab.dtype == np.uint8 and lab.shape == (h, w) and set(np.unique(lab).tolist()) <= {0, 1, 255}, 'label.png'), (t.dtype == np.uint8 and set(np.unique(t).tolist()) <= {0, 1, 255}, 'lines.png'),
                           ((W // K, H // K) == (w, h), 'lines.png size'), (ai.shape == (h, w), 'area_in.png size'), (cv2.imread(d + 'edge.png', 0).shape == (h, w), 'edge.png size'),
                           (not os.path.exists(d + 'valmask.png') or cv2.imread(d + 'valmask.png', 0).shape == (h, w), 'valmask.png size')) if not ok]
    if bad: sys.exit(f'plate {N}: format check failed: {bad}')
    for f in files: files[f]['sha256'] = shas[f]
    meta = dict(plate=N, source=source, made=time.strftime('%Y-%m-%d %H:%M:%S'), by=rel(__file__), by_sha256=sha(__file__), git_head=git_head(),
                ft_per_inch=scale_ft(N), scan=dict(path=f'data/sanborn/cufp/22-{N}.jpg', sha256=sha(SP + f'cufp/22-{N}.jpg')), files=files, **extra)
    json.dump(meta, open(d + 'meta.json', 'w', encoding='utf8', newline='\n'), indent=1)
    mf = out + 'manifest.json'; man = json.load(open(mf, encoding='utf8')) if os.path.exists(mf) else dict(plates={})
    man['plates'][N] = dict(source=source, files=shas, meta_sha256=sha(d + 'meta.json'), ft_per_inch=meta['ft_per_inch'])
    man['plates'] = {k: man['plates'][k] for k in sorted(man['plates'])}
    man.update(note='make_labels_v2.py: one folder per plate; content_sha256 = sha256 of json.dumps(plates, sort_keys=True)', updated=meta['made'],
               content_sha256=hashlib.sha256(json.dumps(man['plates'], sort_keys=True).encode()).hexdigest())
    json.dump(man, open(mf + '.tmp', 'w', encoding='utf8', newline='\n'), indent=1); os.replace(mf + '.tmp', mf)
    return meta


# ---------------------------------------------------------------- label: today's four labelled plates, unchanged
def make_label(N, out):
    d = out + N + '/'; os.makedirs(d, exist_ok=True); F = {}
    for a, b in (('img.jpg', f'{N}_img.jpg'), ('label.png', f'{N}_label.png'), ('edge.png', f'{N}_edge.png'), ('area_in.png', f'{N}_pred_{AREA_IN}.png')):
        F[a] = copy(U + b, d + a)
    F['area_in.png']['note'] = f'IN SAMPLE: {AREA_IN} was trained on this plate (train_noguide.py: 82A, 80, 43, 45)'
    full = scan(N); H, W = full.shape[:2]; del full
    lab = cv2.resize(cv2.imread(U + f'{N}_label.png', 0), (W, H), interpolation=cv2.INTER_NEAREST)
    vf = U + f'{N}_verified.json'; ver = json.load(open(vf, encoding='utf8')) if os.path.exists(vf) else []
    t = line_target(H, W, ver, lab != 255, alpha_full(N, W, H)); save_png(d + 'lines.png', t)
    F['lines.png'] = dict(made=f'edgenet.load\'s t from {rel(U + N + "_label.png")}, {rel(vf)} and cufp/{N}/png_alpha_s4.npy (LINE {LINE}, GAP {GAP})',
                          sources_sha256={rel(U + N + '_label.png'): sha(U + f'{N}_label.png'), rel(vf): sha(vf)})
    lh = cv2.imread(d + 'label.png', 0)
    counts = dict(size_half=[lh.shape[1], lh.shape[0]], size_full=[W, H], block=int((lh == 1).sum()), street=int((lh == 0).sum()), untaught=int((lh == 255).sum()),
                  line_pos=int((t == 1).sum()), line_neg=int((t == 0).sum()), line_unscored=int((t == 255).sum()), verified_edges=len(ver))
    mk = U + f'{N}_meta.json'
    return finish(N, out, 'label', F, dict(counts=counts, make_labels_meta=json.load(open(mk, encoding='utf8')) if os.path.exists(mk) else None))


# ---------------------------------------------------------------- map: a plate whose lines Ben has checked
def street_map(N, W, H):
    """street_map.py's street map of plate N (editor_lines + its closing), as a dict in streetmap/22-N.json's format, and the faces"""
    import street_map as SM  # noqa: E402
    from shapely.geometry import LineString, Point
    from shapely.ops import unary_union, polygonize_full
    bf = SP + f'picks22_guided/22-{N}/edges_ben.json'; B = json.load(open(bf, encoding='utf8'))
    L, SH = SM.editor_lines(N, W, H, json.load(open(U + f'{N}_edges.json', encoding='utf8')), B)
    def ext(l):
        a, b = np.array(l['a'], float), np.array(l['b'], float); d = (b - a) / np.hypot(*(b - a)); return LineString([a - d * SM_TOL, b + d * SM_TOL])
    ls = [LineString([l['a'], l['b']]) for l in L]; paper = unary_union([LineString([s['a'], s['b']]) for s in SH])
    P = sorted(polygonize_full(unary_union([ext(l) for l in L]))[0].geoms, key=lambda p: (round(p.centroid.y / 400), p.centroid.x))
    P = [p for p in P if p.area >= SM_MIN_FACE]
    blocks = []
    for i, p in enumerate(P):
        (cx, cy), (w, h), _ = cv2.minAreaRect(np.array(p.exterior.coords, np.float32))
        blocks.append(dict(id=i + 1, area_px=round(p.area), narrow_px=round(min(w, h)), ring=[[round(x, 1), round(y, 1)] for x, y in p.exterior.coords[:-1]]))
    ends = []
    for i, l in enumerate(L):
        for p in (l['a'], l['b']):
            g = min(o.distance(Point(p)) for j, o in enumerate(ls) if j != i)
            if g > SM_TOL: dd = paper.distance(Point(p)); ends.append(dict(at=[round(p[0], 1), round(p[1], 1)], gap_px=round(g, 1), where='sheet_edge' if dd <= 60.0 else 'inside', paper_edge_px=round(dd)))
    kinds = {k: [sum(1 for l in L if l['kind'] == k), round(sum(ls[i].length for i, l in enumerate(L) if l['kind'] == k))] for k in ('printed', 'drawn', 'sheet_edge', 'no_printed_line')}
    sm = dict(plate=N, size=[W, H], source=f'picks22_guided/22-{N}/edges_ben.json', source_saved_at=B.get('saved_at'), tolerance_px=SM_TOL, sheet_edge_px=60.0,
              note="Ben's ground truth street sides. Open ends are meant: a street that carries on to another sheet, or stops at the creek, canal or railway, is left open.",
              counts=dict(lines=len(L), length_px=round(sum(l.length for l in ls)), by_kind=kinds, blocks=len(blocks), open_ends=len(ends), open_at_sheet_edge=sum(e['where'] == 'sheet_edge' for e in ends), open_inside=sum(e['where'] == 'inside' for e in ends)),
              lines=[dict(a=[round(v, 1) for v in l['a']], b=[round(v, 1) for v in l['b']], kind=l['kind'], name=l['name']) for l in L], blocks=blocks, open_ends=ends)
    return sm, P, B


def street_rays(L, blk, stop, alpha_h, ftpi, sid=None):
    """the street ground beside Ben's lines (half size): see the docstring, map. Returns the mask and counts"""
    h, w = blk.shape; pxft = 300.0 / ftpi / K; WMAX = int(round(WMAX_FT * pxft)); WPAIR = WPAIR_FT * pxft; BAND = int(round(BAND_FT * pxft))
    offs = np.arange(2, WMAX + 1); street = np.zeros((h, w), np.uint8); n = dict(samples=0, block_one_side=0, paired=0, undecided=0, closed=0, banded=0)
    for l in L:
        a, b = np.array(l['a'], float) / K, np.array(l['b'], float) / K; Lh = np.hypot(*(b - a))
        if Lh < 4: continue
        dv = (b - a) / Lh; nv = np.array([-dv[1], dv[0]]); pts = a + np.outer(np.arange(1.0, Lh - 1.0, 1.0), dv); m = len(pts); n['samples'] += m
        side = {}
        for s in (1, -1):
            q = pts[:, None, :] + s * offs[None, :, None] * nv; x = q[..., 0].round().astype(int); y = q[..., 1].round().astype(int)
            ins = (x >= 0) & (x < w) & (y >= 0) & (y < h); xc, yc = np.clip(x, 0, w - 1), np.clip(y, 0, h - 1)
            st = ~ins | (stop[yc, xc] > 0) | (blk[yc, xc] > 0) | ~alpha_h[yc, xc]; st[:, 0] = False   # offset 2 may still touch the line itself
            first = np.where(st.any(1), st.argmax(1), len(offs)); r = np.where(first < len(offs), offs[np.minimum(first, len(offs) - 1)], np.inf)
            hit_line = np.zeros(m, bool); k_ = first < len(offs); hit_line[k_] = stop[yc[k_, first[k_]], xc[k_, first[k_]]] > 0
            par = np.zeros(m, bool)                       # the line met runs (nearly) parallel: the other side of a street
            if sid is not None and k_.any():
                j = sid[yc[k_, first[k_]], xc[k_, first[k_]]]; dj = np.array([[0.0, 0.0]] + [list((np.array(o['b'], float) - np.array(o['a'], float)) / max(1e-6, np.hypot(o['b'][0] - o['a'][0], o['b'][1] - o['a'][1]))) for o in L])
                par[k_] = (j > 0) & (np.abs(dj[j] @ dv) >= np.cos(np.radians(PAR_DEG)))
            pk = pts + s * POKE * nv; px_, py_ = np.clip(pk[:, 0].round().astype(int), 0, w - 1), np.clip(pk[:, 1].round().astype(int), 0, h - 1)
            side[s] = dict(x=xc, y=yc, ins=ins, r=r, line=hit_line, par=par if sid is not None else hit_line, inblk=blk[py_, px_] > 0)
        for s in (1, -1):
            me, ot = side[s], side[-s]
            by_block = ot['inblk'] & ~me['inblk']
            by_pair = ~ot['inblk'] & ~me['inblk'] & me['par'] & (me['r'] <= WPAIR) & ~(ot['line'] & (ot['r'] < 1.5 * me['r']))
            use = by_block | by_pair
            if not use.any(): continue
            n['block_one_side'] += int(by_block.sum()); n['paired'] += int(by_pair.sum())
            reach = np.where(me['r'] <= WMAX, me['r'], BAND); n['closed'] += int((use & (me['r'] <= WMAX)).sum()); n['banded'] += int((use & (me['r'] > WMAX)).sum())
            sel = use[:, None] & (offs[None, :] < reach[:, None]) & me['ins']
            street[me['y'][sel], me['x'][sel]] = 1
        n['undecided'] = n['samples'] - n['block_one_side'] - n['paired']
    street = cv2.morphologyEx(street, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))   # rays of a slanting line leave pinholes
    return street > 0, dict(n, wmax_px_half=WMAX, wpair_px_half=round(WPAIR, 1), band_px_half=BAND)


def map_labels(N, verbose=True, val_x=None):
    """the map labels of plate N in memory: (img, label, edge, lines, valmask, streetmap dict, counts). val_x: the
    validation ground is x >= val_x (half px); None: the right-hand quarter of the image, x >= int(0.75 w)"""
    full = scan(N); H, W = full.shape[:2]; img = half_img(full); h, w = img.shape[:2]; del full
    ftpi = scale_ft(N) or 100; ah = alpha_half(N, w, h); af = alpha_full(N, W, H)
    sm, P, B = street_map(N, W, H)
    blk = np.zeros((h, w), np.uint8); narrow = np.zeros((h, w), np.uint8)
    for p, bl in zip(P, sm['blocks']):
        rings = [np.round(np.array(p.exterior.coords) / K).astype(np.int32)] + [np.round(np.array(r.coords) / K).astype(np.int32) for r in p.interiors]
        cv2.fillPoly(narrow if bl['narrow_px'] < NARROW else blk, rings, 1)
    blk[narrow > 0] = 0
    L = sm['lines']; stop = raster([(l['a'], l['b']) for l in L], (h, w), 1.0 / K, 3) | narrow
    sid = np.zeros((h, w), np.int32)
    for i, l in enumerate(L): cv2.line(sid, tuple(np.round(np.array(l['a']) / K).astype(int)), tuple(np.round(np.array(l['b']) / K).astype(int)), i + 1, 3)
    street, rc = street_rays(L, blk, stop, ah, ftpi, sid)
    lab = np.full((h, w), 255, np.uint8); lab[street & (blk == 0) & (narrow == 0)] = 0; lab[blk > 0] = 1
    lab[edge_band(lab)] = 255; lab[~ah] = 255
    pos = [(l['a'], l['b']) for l in L if l['kind'] in ('printed', 'drawn')]; blank_l = [(l['a'], l['b']) for l in L if l['kind'] in ('sheet_edge', 'no_printed_line')]
    blank = cv2.dilate(raster(blank_l, (H, W), 1.0, LINE), np.ones((2 * (LINE + GAP) + 1,) * 2, np.uint8)) > 0
    wrong = [(s['a'], s['b']) for s in B['lines'] if s.get('verdict') == 'wrong']
    taught = cv2.resize(lab, (W, H), interpolation=cv2.INTER_NEAREST) != 255
    wr = raster(wrong, (H, W), 1.0, WRONG_PX) > 0; taught |= wr
    t = line_target(H, W, pos, taught, af, blank)
    edge = raster(pos, (h, w), 1.0 / K, 1, 255); edge[~ah] = 0
    vx = int(w * 0.75) if val_x is None else int(val_x)
    if not 0 < vx < w: sys.exit(f'--val-x {vx}: outside the plate (0 < x < {w}, half px)')
    val = np.zeros((h, w), np.uint8); val[:, vx:] = 1
    counts = dict(size_half=[w, h], size_full=[W, H], ft_per_inch=ftpi, faces=len(P), blocks_taught=sum(b['narrow_px'] >= NARROW for b in sm['blocks']), narrow_faces_untaught=sum(b['narrow_px'] < NARROW for b in sm['blocks']),
                  block=int((lab == 1).sum()), street=int((lab == 0).sum()), untaught=int((lab == 255).sum()), paper=int(ah.sum()),
                  line_pos=int((t == 1).sum()), line_neg=int((t == 0).sum()), line_unscored=int((t == 255).sum()), lines_pos=len(pos), lines_blank=len(blank_l), lines_wrong=len(wrong), rays=rc,
                  val_x_half=vx, val_block=int(((lab == 1) & (val == 1)).sum()), val_street=int(((lab == 0) & (val == 1)).sum()),
                  val_line_pos=int((t[:, 2 * vx:] == 1).sum()), val_line_neg=int((t[:, 2 * vx:] == 0).sum()), val_paper_share=round(float(ah[:, vx:].sum() / max(1, ah.sum())), 4))
    if verbose: print(N, 'map', json.dumps({k: v for k, v in counts.items() if k != 'rays'}), flush=True)
    return img, lab, edge, t, val, sm, counts


def make_map(N, out, val_x=None):
    d = out + N + '/'; os.makedirs(d, exist_ok=True)
    img, lab, edge, t, val, sm, counts = map_labels(N, val_x=val_x); F = {}
    cv2.imwrite(d + 'img.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 92]); F['img.jpg'] = dict(made=f'cufp/22-{N}.jpg at half size (INTER_AREA), JPEG 92, as make_labels.py')
    save_png(d + 'label.png', lab); F['label.png'] = dict(made='Ben\'s closed blocks 1; street by rays from his lines (street_rays); 255 elsewhere')
    save_png(d + 'edge.png', edge); F['edge.png'] = dict(made='his printed and drawn lines, 1 px at half size')
    save_png(d + 'lines.png', t); F['lines.png'] = dict(made='his printed and drawn lines positive (LINE 3, GAP 4 margin 255); sheet-edge and no-printed-line sides 255; negatives on taught ground and along his wrong lines')
    save_png(d + 'valmask.png', val); F['valmask.png'] = dict(made=f'1 = validation: x >= {counts["val_x_half"]} half px' + (' (int(0.75 * width): the right-hand quarter of the image)' if val_x is None else ' (--val-x)'), val_x_half=counts['val_x_half'])
    F['area_in.png'] = copy(U + f'{N}_pred_{AREA_IN}.png', d + 'area_in.png'); F['area_in.png']['note'] = f'out of sample: {AREA_IN} was not trained on {N} (the batch\'s own map)'
    json.dump(sm, open(d + 'streetmap.json', 'w', encoding='utf8', newline='\n'), separators=(',', ':')); F['streetmap.json'] = dict(made='street_map.editor_lines + street_map.py\'s closing, from his edits')
    srcs = {rel(SP + f'picks22_guided/22-{N}/edges_ben.json'): sha(SP + f'picks22_guided/22-{N}/edges_ben.json'), rel(U + f'{N}_edges.json'): sha(U + f'{N}_edges.json')}
    return finish(N, out, 'map', F, dict(counts=counts, sources_sha256=srcs, edges_ben_saved_at=sm['source_saved_at'],
                                          thresholds=dict(sm_tol=SM_TOL, min_face=SM_MIN_FACE, narrow_px=NARROW, poke=POKE, wmax_ft=WMAX_FT, wpair_ft=WPAIR_FT, par_deg=PAR_DEG, band_ft=BAND_FT, wrong_px=WRONG_PX, line=LINE, gap=GAP)))


# ---------------------------------------------------------------- pseudo: a batch plate, the networks' confident guess
def pseudo_inputs(N, outlines=None, edges=None, area=None, lines=None, mapground=None, masks=None):
    """everything the pseudo labels need, loaded once (the tuner calls pseudo_labels many times on one of these)"""
    import edit_server as es  # noqa: E402
    full = scan(N); H, W = full.shape[:2]; img = half_img(full); h, w = img.shape[:2]
    of = outlines or SP + f'picks22_guided/22-{N}/outlines.json'; ef = edges or U + f'{N}_edges.json'
    af_ = area or U + f'{N}_pred_{AREA_IN}.png'; lf = lines or U + f'{N}_lines_{LINES_NET}.png'
    mg = mapground if mapground is not None else U + f'{N}_mapground.png'
    for f in (of, ef, af_, lf):
        if not os.path.exists(f): sys.exit(f'plate {N}: missing {rel(f)} (the batch outputs)')
    if os.path.exists(U + f'{N}_guide.png') and outlines is None: sys.exit(f'plate {N} is placed (unet_data/{N}_guide.png): its outlines.json is the guided one, not the batch\'s')
    polys = json.load(open(of, encoding='utf8')); E = es.clean(json.load(open(ef, encoding='utf8')))
    pa = cv2.imread(af_, 0); pl = cv2.imread(lf, 0)
    if pa.shape != (h, w) or pl.shape != (H, W): sys.exit(f'plate {N}: map sizes {pa.shape} {pl.shape} do not fit the scan ({h}, {w}) / ({H}, {W})')
    ah = alpha_half(N, w, h); af = alpha_full(N, W, H); ground_h = ah.copy(); mg_used = None
    if mg and os.path.exists(mg):
        m8 = cv2.imread(mg, 0) > 127; ground_h &= cv2.resize(m8.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0; mg_used = mg
    blockg = block_ground(polys, h, w, 1.0 / K)
    rings = [np.array([q['a'] for q in p_], float) for p_ in polys if p_ and not p_[0].get('hole') and len(p_) >= 3]
    areas = np.array([abs(cv2.contourArea(r.astype(np.float32))) for r in rings]); med = float(np.median(areas)) if len(areas) else 1.0
    ratio = np.zeros((h, w), np.float32)                                  # each block polygon's area over the plate's median block (outermost first, so a nested one paints over)
    for k in np.argsort(-areas) if len(areas) else []: cv2.fillPoly(ratio, [np.round(rings[k] / K).astype(np.int32)], float(areas[k] / max(med, 1.0)))
    din = cv2.distanceTransform(blockg, cv2.DIST_L2, 5); dout = cv2.distanceTransform((1 - blockg).astype(np.uint8), cv2.DIST_L2, 5)
    sides = [(s['a'], s['b']) for p in polys for s in p] + [(e['a'], e['b']) for e in E if e['state'] != 'green']
    dside = cv2.distanceTransform((raster(sides, (H, W)) == 0).astype(np.uint8), cv2.DIST_L2, 5)
    green = [(e['a'], e['b']) for e in E if e['state'] == 'green']
    hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170)); del hsv, full
    pxft = 300.0 / (scale_ft(N) or 100)
    inner = cv2.dilate(cv2.resize(blockg, (W, H), interpolation=cv2.INTER_NEAREST), np.ones((9, 9), np.uint8)) > 0
    longl = long_lines(ink & inner, pxft, ALLEY); del inner                           # long straight ink lines in the block ground (alleys, missed street sides, rear lot lines)
    dedge = cv2.distanceTransform(af.astype(np.uint8), cv2.DIST_L2, 5)               # distance to the paper's edge
    # integrator, 23 Nov: each block polygon's size in acres (half size, holes cut, as select/pseudo_area.py measures it),
    # the printed KEY's box, and the map ground at full size (a little wider, so a street side drawn along it stays taught)
    inst = np.zeros((h, w), np.int32); k_ = 0
    for p_ in polys:
        if p_ and not p_[0].get('hole') and len(p_) >= 3: k_ += 1; cv2.fillPoly(inst, [np.round(np.array([q['a'] for q in p_], float) / K).astype(np.int32)], k_)
    for p_ in polys:
        if p_ and p_[0].get('hole') and len(p_) >= 3: cv2.fillPoly(inst, [np.round(np.array([q['a'] for q in p_], float) / K).astype(np.int32)], 0)
    acre_px = (K / pxft) ** 2 / 43560.0; acres = (np.bincount(inst.ravel(), minlength=k_ + 1) * acre_px).astype(np.float32); acres[0] = 0.0; acres = acres[inst]; del inst
    key = (json.load(open(KEY_JSON, encoding='utf8')).get(N) or {}).get('key_box') if os.path.exists(KEY_JSON) else None
    key_h = np.zeros((h, w), bool); key_f = np.zeros((H, W), bool)
    if key:
        x0, y0, x1, y1 = [int(v) for v in key]; key_f[max(0, y0 - KEY_PAD):y1 + KEY_PAD, max(0, x0 - KEY_PAD):x1 + KEY_PAD] = True
        key_h[max(0, (y0 - KEY_PAD) // K):(y1 + KEY_PAD) // K + 1, max(0, (x0 - KEY_PAD) // K):(x1 + KEY_PAD) // K + 1] = True
    hand_h = np.zeros((h, w), bool); hand_f = np.zeros((H, W), bool)                 # hand masks (--mask): ground seen by eye to be taught wrongly
    for m_ in masks or []:
        x0, y0, x1, y1 = [int(v) for v in m_['box']]; hand_f[max(0, y0):y1, max(0, x0):x1] = True; hand_h[max(0, y0 // K):y1 // K + 1, max(0, x0 // K):x1 // K + 1] = True
    mg_f = None
    if mg_used:
        mg_f = cv2.dilate(cv2.resize((cv2.imread(mg_used, 0) > 127).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST), np.ones((2 * MG_PAD + 1,) * 2, np.uint8)) > 0
    return dict(N=N, H=H, W=W, h=h, w=w, img=img, polys=polys, E=E, pa=pa, pl=pl, ah=ah, af=af, ground_h=ground_h, blockg=blockg, din=din, dout=dout, dside=dside, green=green, ink=ink,
                pxft=pxft, longl=longl, dedge=dedge, ratio=ratio, acres=acres, key=key, key_h=key_h, key_f=key_f, mg_f=mg_f, hand=masks or [], hand_h=hand_h, hand_f=hand_f,
                files={k: rel(v) for k, v in (('outlines', of), ('edges', ef), ('area', af_), ('lines', lf))} | ({'mapground': rel(mg_used)} if mg_used else {}) | ({'key': rel(KEY_JSON)} if key else {}),
                sha={rel(v): sha(v) for v in (of, ef, af_, lf) + ((mg_used,) if mg_used else ()) + ((KEY_JSON,) if key else ())})


def long_lines(m, pxft, A):
    """long straight ink lines of mask m (full size): HoughLinesP pieces joined when they lie on one line (within ANG_JOIN
    degrees and OFF_JOIN px) with a gap under GAP_FT ft, kept when at least min_len_ft long and on ink along CONT of
    their length. Returns a list of (p, u, length): start point, unit direction, length"""
    minlen = A['min_len_ft'] * pxft
    segs = cv2.HoughLinesP(m.astype(np.uint8), 1, np.pi / 720, threshold=max(20, int(0.3 * minlen)), minLineLength=0.4 * minlen, maxLineGap=max(4, int(2 * pxft)))
    segs = np.zeros((0, 4)) if segs is None else np.asarray(segs).reshape(-1, 4).astype(float)   # OpenCV 4 gives (n, 1, 4), OpenCV 5 (n, 4)
    segs = segs[np.argsort(-np.hypot(segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1]))]
    cj = np.cos(np.radians(A['ang_join'])); lines = []
    for x0, y0, x1, y1 in segs:
        a, b = np.array([x0, y0]), np.array([x1, y1]); L = np.hypot(*(b - a))
        if L < 2: continue
        u = (b - a) / L; hit = False
        for ln in lines:
            if abs(u @ ln['u']) < cj: continue
            n = np.array([-ln['u'][1], ln['u'][0]])
            if abs((a - ln['p']) @ n) > A['off_join'] or abs((b - ln['p']) @ n) > A['off_join']: continue
            t0, t1 = sorted(((a - ln['p']) @ ln['u'], (b - ln['p']) @ ln['u']))
            if t0 > ln['t1'] + A['gap_ft'] * pxft or t1 < ln['t0'] - A['gap_ft'] * pxft: continue
            ln['t0'], ln['t1'] = min(ln['t0'], t0), max(ln['t1'], t1); hit = True; break
        if not hit: lines.append(dict(p=a, u=u, t0=0.0, t1=L))
    inkd = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0; H, W = m.shape; out = []
    for ln in lines:
        L = ln['t1'] - ln['t0']
        if L < minlen: continue
        p = ln['p'] + ln['u'] * ln['t0']; q = p + np.outer(np.arange(0, L, 2.0), ln['u'])
        x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1)
        if inkd[y, x].mean() >= A['cont']: out.append((p, ln['u'], L))
    return out


def alley_strips(I, ftpi):
    """alleys and narrow streets the networks missed, inside their blocks (see the docstring): pairs of long straight
    parallel ink lines min_ft..max_ft apart, overlapping over most of their length, little tint between them (no
    buildings), and the strip runs across the block: carried on along its line it leaves the block ground within
    reach_ft ft at both ends (in a second pass, or on a strip found in the first). Returns the half-size
    mask (strip and its lines, padded) and the strips found (full-size px)"""
    A = ALLEY; pxft = 300.0 / ftpi; H, W, h, w = I['H'], I['W'], I['h'], I['w']
    lines = I['longl']
    out = np.zeros((h, w), np.uint8); found = []
    if len(lines) < 2: return out > 0, found
    hink = cv2.resize(I['ink'].astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0
    lab_ = cv2.cvtColor(I['img'], cv2.COLOR_BGR2LAB)[:, :, 1:].astype(np.float32); open_ = I['ground_h'] & (I['blockg'] == 0) & ~hink
    ref = np.median(lab_[open_], 0) if open_.sum() > 1000 else np.median(lab_[I['ah'] & ~hink], 0)       # the paper's colour (a*, b*): open ground outside the blocks
    tint = (np.hypot(lab_[:, :, 0] - ref[0], lab_[:, :, 1] - ref[1]) > A['tint']) & ~hink                 # building tints (pink, yellow, ...): far from the paper's colour
    inkf = I['ink']
    lo, hi = A['min_ft'] * pxft, A['max_ft'] * pxft; ca = np.cos(np.radians(A['ang_deg'])); cands = []
    for i in range(len(lines)):
        p, u, L = lines[i]; n = np.array([-u[1], u[0]])
        for j in range(i + 1, len(lines)):
            p2, u2, L2 = lines[j]
            if abs(u @ u2) < ca: continue
            off = ((p2 + u2 * L2 / 2) - p) @ n
            if not lo <= abs(off) <= hi: continue
            t0, t1 = sorted(((p2 - p) @ u, (p2 + u2 * L2 - p) @ u)); s0, s1 = max(0.0, t0), min(L, t1)
            if s1 - s0 < A['overlap'] * min(L, L2) or s1 - s0 < A['min_len_ft'] * pxft: continue
            a0, a1 = p + u * s0, p + u * s1
            g = a0[None, None] + np.linspace(0.05, 0.95, 24)[:, None, None] * (a1 - a0) + np.linspace(0.2, 0.8, 5)[None, :, None] * off * n
            gx = np.clip((g[..., 0] / K).round().astype(int), 0, w - 1); gy = np.clip((g[..., 1] / K).round().astype(int), 0, h - 1)
            if tint[gy, gx].mean() > A['tint_share']: continue                                                # buildings between: the two sides of a lot
            if A['cross']:                         # a line right across the strip, from one side line to the other, closes it: a lot, not an alley (lettering stops short of the sides)
                g = a0[None, None] + np.arange(0, s1 - s0, 2.0)[:, None, None] * u + np.linspace(0.03, 0.97, 12)[None, :, None] * off * n
                gx = np.clip(g[..., 0].round().astype(int), 0, W - 1); gy = np.clip(g[..., 1].round().astype(int), 0, H - 1)
                if (inkf[gy, gx].mean(1) >= 0.99).any(): continue
            cands.append((a0, a1, off, n, u))
    def reach(c, extra):
        a0, a1, off, n, u = c; mid0, mid1 = a0 + n * off / 2, a1 + n * off / 2; ok = []; ends = []
        for m0, d in ((mid0, -u), (mid1, u)):
            q = m0 + np.outer(np.arange(0, A['reach_ft'] * pxft, 2.0), d); x = (q[:, 0] / K).round().astype(int); y = (q[:, 1] / K).round().astype(int)
            ins = (x >= 0) & (x < w) & (y >= 0) & (y < h); xc, yc = np.clip(x, 0, w - 1), np.clip(y, 0, h - 1)
            outb = ~ins | (I['blockg'][yc, xc] == 0) | (extra[yc, xc] > 0); k = int(outb.argmax()) if outb.any() else -1
            ok.append(k >= 0); ends.append(q[k] if k >= 0 else q[-1])
        return all(ok), ends
    done = np.zeros(len(cands), bool)
    for npass in range(A['passes']):                     # a later pass lets a strip end on one found before (an alley teed into a street the networks also missed)
        for k, c in enumerate(cands):
            if done[k]: continue
            good, ends = reach(c, out)
            if not good: continue
            a0, a1, off, n, u = c; e0 = ends[0] - n * off / 2; e1 = ends[1] - n * off / 2; done[k] = True
            quad = np.array([e0, e1, e1 + n * off, e0 + n * off]); cv2.fillPoly(out, [np.round(quad / K).astype(np.int32)], 1)
            found.append(dict(a=e0.round(1).tolist(), b=e1.round(1).tolist(), width_px=round(float(abs(off)), 1), width_ft=round(float(abs(off) / pxft), 1), npass=npass + 1))
    out = cv2.dilate(out, np.ones((2 * A['pad'] + 1,) * 2, np.uint8))
    return out > 0, found


def pseudo_labels(I, th, ftpi=100, alley=None):
    """the pseudo labels from loaded inputs I and thresholds th: (label, lines, edge, counts)"""
    h, w, H, W = I['h'], I['w'], I['H'], I['W']
    pa = I['pa'].astype(np.float32) / 255.0
    blk = (I['blockg'] > 0) & (pa > th['hi']) & (I['din'] >= th['d']) & I['ground_h']
    if th.get('bigx', 0) > 0: blk &= I['ratio'] <= th['bigx']                  # off by default: a polygon many times the median block is often open land (a convention Ben has not settled)
    capa = th.get('cap', 0) * CAP_ACRES.get(ftpi, 0) if 'acres' in I else 0
    if capa > 0: blk &= I['acres'] <= capa                                     # integrator: a polygon bigger than the labelled plates' big blocks is a merge across streets, open land, the river or a rail yard: not taught
    st = (I['blockg'] == 0) & (pa < th['lo']) & (I['dout'] >= th['ds']) & I['ground_h']
    lab = np.full((h, w), 255, np.uint8); lab[st] = 0; lab[blk] = 1
    if alley is not None: lab[alley] = 255
    if 'key_h' in I: lab[I['key_h']] = 255                                    # integrator: the printed KEY is not map
    if I.get('hand'): lab[I['hand_h']] = 255                                  # integrator: hand masks (--mask)
    lab[~I['ah']] = 255
    unsure = cv2.resize((lab == 255).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)
    dun = cv2.distanceTransform((unsure == 0).astype(np.uint8), cv2.DIST_L2, 5) if th['mu'] > 0 else None
    resp = I['pl'] > th['tl'] * 255
    dres = cv2.distanceTransform((~resp).astype(np.uint8), cv2.DIST_L2, 5)
    neg = (I['dside'] >= th['ms']) & (dres >= th['mr']) & I['af']
    neg &= (dun >= th['mu']) if dun is not None else (unsure == 0)
    if th.get('me', 0) > 0: neg &= I['dedge'] >= th['me'] * I['pxft']                # a street side drawn along the paper's edge has no block on the plate to show it
    blank = None
    if th.get('ll', 0) > 0:                                                          # a long straight ink line in the block ground may be a block line the networks missed: not taught
        ll = [(p, p + u * L) for p, u, L in I['longl'] if L >= th['ll'] * I['pxft']]
        blank = cv2.dilate(raster(ll, (H, W), 1.0, LINE), np.ones((2 * (LINE + GAP) + 1,) * 2, np.uint8)) > 0 if ll else None
    green = [(a, b) for a, b in I['green'] if np.hypot(b[0] - a[0], b[1] - a[1]) >= th.get('gmin', 0) * I['pxft']]   # a short green line is less often a block line: not taught (it is an outline side, so not negative either)
    t = line_target(H, W, green, neg, I['af'], blank)
    edge = raster(green, (h, w), 1.0 / K, 1, 255); edge[~I['ah']] = 0
    off = None                                                                 # integrator: no line is taught in the KEY box or off the map ground (a green line in the margin or the KEY)
    if I.get('key') is not None: off = I['key_f'].copy()
    if I.get('mg_f') is not None: off = ~I['mg_f'] if off is None else (off | ~I['mg_f'])
    if I.get('hand'): off = I['hand_f'].copy() if off is None else (off | I['hand_f'])
    if off is not None:
        t[off] = 255; edge[cv2.resize(off.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0] = 0
    counts = dict(block=int((lab == 1).sum()), street=int((lab == 0).sum()), untaught=int((lab == 255).sum()), paper=int(I['ah'].sum()),
                  line_pos=int((t == 1).sum()), line_neg=int((t == 0).sum()), line_unscored=int((t == 255).sum()), green_lines=len(green), alley_px=int(alley.sum()) if alley is not None else 0,
                  cap_acres=round(capa, 2), capped_block_px=int(((I['blockg'] > 0) & (I['acres'] > capa) & I['ground_h']).sum()) if capa > 0 else 0,
                  key_box=I.get('key'), hand_masks=len(I.get('hand') or []), hand_mask_half_px=int(I['hand_h'].sum()) if I.get('hand') else 0, full_px_off_map_or_key=int(off.sum()) if off is not None else 0)
    return lab, t, edge, counts


def make_pseudo(N, out, th, outlines=None, edges=None, mapground=None, mask_file=None):
    d = out + N + '/'; os.makedirs(d, exist_ok=True)
    masks = (json.load(open(mask_file, encoding='utf8')).get(N) or []) if mask_file else []
    ftpi = scale_ft(N) or 100; I = pseudo_inputs(N, outlines, edges, mapground=mapground, masks=masks)
    al, found = alley_strips(I, ftpi) if th.get('alley') else (None, [])
    lab, t, edge, counts = pseudo_labels(I, th, ftpi, al); F = {}
    cv2.imwrite(d + 'img.jpg', I['img'], [cv2.IMWRITE_JPEG_QUALITY, 92]); F['img.jpg'] = dict(made=f'cufp/22-{N}.jpg at half size (INTER_AREA), JPEG 92, as make_labels.py')
    save_png(d + 'label.png', lab); F['label.png'] = dict(made='block: in a polygon, P > hi, d px in; street: outside, P < lo, ds px out, on the map ground; alley strips 255')
    save_png(d + 'edge.png', edge); F['edge.png'] = dict(made='the green editor lines, 1 px at half size')
    save_png(d + 'lines.png', t); F['lines.png'] = dict(made='green editor lines positive (LINE 3, GAP 4 margin 255); negatives ms px from every side and orange line, mr px from line-net response > tl, mu px from untaught area ground, me ft from the paper edge, off long straight ink lines (ll ft) in the block ground')
    F['area_in.png'] = copy(U + f'{N}_pred_{AREA_IN}.png', d + 'area_in.png'); F['area_in.png']['note'] = f'out of sample: {AREA_IN} was not trained on {N} (the batch\'s own map)'
    counts.update(size_half=[I['w'], I['h']], size_full=[I['W'], I['H']], ft_per_inch=ftpi, alley_pairs=len(found))
    bf = U + f'{N}_blocks_ng.json'; qa = json.load(open(bf, encoding='utf8')) if os.path.exists(bf) else {}
    warn = ([f'the batch flagged it suspect: {qa.get("suspect_why")}'] if qa.get('suspect') else []) + ([f'{ftpi} ft to the inch: the networks were trained at 100 and 200'] if ftpi not in (100, 200) else [])
    print(N, 'pseudo', json.dumps(counts), ('| WARNING: ' + '; '.join(warn)) if warn else '', flush=True)
    meta = finish(N, out, 'pseudo', F, dict(counts=counts, thresholds=dict(th, alley_cfg=ALLEY if th.get('alley') else None, line=LINE, gap=GAP), inputs=I['files'], sources_sha256=I['sha'],
                                            alley_pairs=found, warnings=warn, hand_masks=dict(file=rel(mask_file), sha256=sha(mask_file), masks=masks) if mask_file else None, tuned_on='1A only (pseudo labels from its batch outputs against its map labels from Ben): data/sanborn/bench_2026-11-23/train/labels/tune/', note='the networks\' own guesses (area_ng1, lines_ng1, the merged outline step), confidence-filtered: not ground truth'))
    return meta


# ---------------------------------------------------------------- verify: label plates against today's loaders
def verify(N, out):
    """load plate N through the new folder and through unet.load / load_edge / edgenet.load (blank guide, area_ng1): every array equal"""
    import unet as A, edgenet as E  # noqa: E402   (torch)
    A.NOGUIDE = True; E.NOGUIDE = True; E.AREA = AREA_IN
    d = out + N + '/'; res = {}
    x0, l0 = A.load(N); w0, e0 = A.load_edge(N, l0)
    im = cv2.imread(d + 'img.jpg')[:, :, ::-1]; z = np.zeros(im.shape[:2], np.uint8); x1 = np.dstack([im, z, z]); l1 = cv2.imread(d + 'label.png', 0)
    e = cv2.imread(d + 'edge.png', 0); dd = cv2.distanceTransform((e == 0).astype(np.uint8), cv2.DIST_L2, 3)
    w1 = (1.0 + A.EDGE_W * np.exp(-dd / A.EDGE_D)).astype(np.float32); e1 = (cv2.dilate(e, np.ones((3, 3), np.uint8)) > 0).astype(np.uint8); e1[(l1 == 255) & (e1 == 0)] = 255
    eq = lambda p, q: bool(p.shape == q.shape and p.dtype == q.dtype and np.array_equal(p, q))
    res['unet.load x'] = eq(x0, x1); res['unet.load label'] = eq(l0, l1); res['unet.load_edge weights'] = eq(w0, w1); res['unet.load_edge target'] = eq(e0, e1)
    del x0, x1, w0, w1
    X0, T0, G0 = E.load(N)
    full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]; inkimg, ink = E.ink_image(full); Z = np.zeros((H, W), np.uint8)
    sp = cv2.resize(cv2.imread(d + 'area_in.png', 0), (W, H), interpolation=cv2.INTER_LINEAR)
    X1 = np.dstack([full[:, :, ::-1], inkimg, Z, Z, sp]); T1 = cv2.imread(d + 'lines.png', 0)
    G1 = np.ones((H, W), np.float32); G1[ink & (T1 == 0)] = E.NEG_INK; G1[T1 == 1] = E.POS
    res['edgenet.load x'] = eq(X0, X1); res['edgenet.load t'] = eq(T0, T1); res['edgenet.load weights'] = eq(G0, G1)
    res['pixels'] = dict(half=int(l1.size), full=int(T1.size), line_pos=int((T1 == 1).sum()), line_neg=int((T1 == 0).sum()))
    print(N, 'verify', json.dumps(res), flush=True)
    return res


# ---------------------------------------------------------------- compare: pseudo labels against a map plate's labels (how noisy they are)
def compare(N, pdir, mdir, val=None):
    """pseudo folder pdir/N against map folder mdir/N. Area: precision of taught block and street, coverage. Lines:
    precision of the positives (within TOL px of Ben's printed/drawn lines), and Ben's lines (1 px samples along each)
    taught positive, wrongly negative, or left 255. val: None whole plate, 'val' the right-hand quarter, 'train' the rest"""
    vm = cv2.imread(mdir + N + '/valmask.png', 0) if os.path.exists(mdir + N + '/valmask.png') else None
    return compare_arrays(N, cv2.imread(pdir + N + '/label.png', 0), cv2.imread(pdir + N + '/lines.png', 0), cv2.imread(mdir + N + '/label.png', 0),
                          cv2.imread(mdir + N + '/lines.png', 0), json.load(open(mdir + N + '/streetmap.json', encoding='utf8')), val, vm)


def compare_arrays(N, pl, pt, ml, mt, sm, val=None, vm=None):
    h, w = ml.shape
    roi = np.ones((h, w), bool)
    if val:
        if vm is not None: q = vm > 0                                     # the map folder's valmask.png (integrator, 23 Nov)
        else: q = np.zeros((h, w), bool); q[:, int(w * 0.75):] = True
        roi = q if val == 'val' else ~q
    ah = alpha_half(N, w, h) & roi; dec = (ml != 255) & roi; tp = (pl != 255) & roi
    r = dict(plate=N, part=val or 'whole')
    r['area'] = dict(block_precision=round(float((ml[(pl == 1) & dec] == 1).mean()), 4) if ((pl == 1) & dec).any() else None,
                     street_precision=round(float((ml[(pl == 0) & dec] == 0).mean()), 4) if ((pl == 0) & dec).any() else None,
                     coverage_of_decided=round(float((tp & dec).sum() / max(1, dec.sum())), 4), coverage_of_decided_block=round(float(((pl == 1) & (ml == 1) & roi).sum() / max(1, ((ml == 1) & roi).sum())), 4),
                     coverage_of_decided_street=round(float(((pl == 0) & (ml == 0) & roi).sum() / max(1, ((ml == 0) & roi).sum())), 4),
                     taught_share_of_paper=round(float((tp & ah).sum() / max(1, ah.sum())), 4), taught_where_map_undecided=round(float((tp & ~dec & ah).sum() / max(1, tp.sum())), 4),
                     block_px=int(((pl == 1) & roi).sum()), street_px=int(((pl == 0) & roi).sum()))
    W, H = sm['size']
    roif = cv2.resize(roi.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    pos = [(l['a'], l['b'], l['kind']) for l in sm['lines'] if l['kind'] in ('printed', 'drawn')]
    cen = raster([(a, b) for a, b, _ in pos], (H, W))
    near = cv2.dilate(cen, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * TOL + 1, 2 * TOL + 1))) > 0
    allc = raster([(l['a'], l['b']) for l in sm['lines']], (H, W)); near_all = cv2.dilate(allc, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * TOL + 1, 2 * TOL + 1))) > 0
    pp = (pt == 1) & roif
    lines = dict(pos_precision=round(float(near[pp].mean()), 4) if pp.any() else None, pos_precision_incl_sheet_edge=round(float(near_all[pp].mean()), 4) if pp.any() else None, pos_px=int(pp.sum()))
    def samples(kinds):
        xs, ys = [], []
        for a, b, k in pos:
            if k not in kinds: continue
            a, b = np.array(a, float), np.array(b, float); n = max(2, int(np.hypot(*(b - a))) + 1); q = a + np.outer(np.linspace(0, 1, n), b - a)
            x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1); k_ = roif[y, x]; xs.append(x[k_]); ys.append(y[k_])
        return (np.concatenate(xs), np.concatenate(ys)) if xs else (np.zeros(0, int), np.zeros(0, int))
    for nm, kinds in (('ben_lines', ('printed', 'drawn')), ('ben_printed', ('printed',)), ('ben_drawn', ('drawn',))):
        x, y = samples(kinds); v = pt[y, x]
        lines[nm] = dict(length_px=int(len(v)), taught_positive=round(float((v == 1).mean()), 4) if len(v) else None, wrongly_negative=round(float((v == 0).mean()), 4) if len(v) else None, left_255=round(float((v == 255).mean()), 4) if len(v) else None)
    pn = (pt == 0) & roif
    lines['neg_px'] = int(pn.sum()); lines['neg_within_tol_of_ben_line'] = round(float(near[pn].mean()), 5) if pn.any() else None
    lines['neg_agree_with_map'] = round(float((mt[pn] == 0).sum() / max(1, (pn & (mt != 255)).sum())), 4)   # of pseudo negatives the map scores, share the map also calls negative
    lines['neg_coverage_of_map_neg'] = round(float((pn & (mt == 0)).sum() / max(1, ((mt == 0) & roif).sum())), 4)
    r['lines'] = lines
    return r


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='training data for area_ng2 / lines_ng2 (see the docstring)', allow_abbrev=False)
    ap.add_argument('mode', choices=('label', 'map', 'pseudo', 'verify', 'compare')); ap.add_argument('plates', nargs='+')
    ap.add_argument('--out', default=OUT_DEFAULT, help='output folder (default data/sanborn/train_v2/)')
    ap.add_argument('--outlines'); ap.add_argument('--edges'); ap.add_argument('--mapground', help="pseudo: another N_mapground.png, or 'none'")
    for k, v in PSEUDO.items():
        if k != 'alley': ap.add_argument('--' + k, type=float, default=v)
    ap.add_argument('--no-alley', action='store_true'); ap.add_argument('--pseudo'); ap.add_argument('--map'); ap.add_argument('--json')
    ap.add_argument('--val-x', type=int, help='map: the validation ground is x >= VAL_X (half px); default the right-hand quarter of the image')
    ap.add_argument('--mask', help='pseudo: hand masks, json {plate: [{box: [x0, y0, x1, y1] (full px), why: ...}]}: not taught (label, lines and edge)')
    a = ap.parse_args(); out = os.path.abspath(a.out).replace('\\', '/') + '/'
    th = {k: getattr(a, k) for k in PSEUDO if k != 'alley'}; th['alley'] = not a.no_alley
    res = []; plates = [p.upper() for p in a.plates]; LP = ('43', '45', '80', '82A')
    if a.mode in ('label', 'map', 'pseudo'):          # every plate is checked before anything is written
        for N in plates: check_out(out, N)
        if a.mode == 'label' and set(plates) - set(LP): sys.exit(f'label: only the four labelled plates 43, 45, 80, 82A (not {sorted(set(plates) - set(LP))})')
        if a.mode == 'map' and [N for N in plates if not os.path.exists(SP + f'picks22_guided/22-{N}/edges_ben.json')]: sys.exit('map: a plate without picks22_guided/22-N/edges_ben.json (Ben has not checked its lines)')
        if a.mode == 'pseudo' and (a.outlines or a.edges) and len(plates) > 1: sys.exit('--outlines / --edges name the files of one plate: give one plate')
        os.makedirs(out, exist_ok=True)
    for N in plates:
        if a.mode == 'label': make_label(N, out)
        elif a.mode == 'map': make_map(N, out, a.val_x)
        elif a.mode == 'pseudo': make_pseudo(N, out, th, a.outlines, a.edges, '' if (a.mapground or '').lower() == 'none' else a.mapground, os.path.abspath(a.mask) if a.mask else None)
        elif a.mode == 'verify': res.append(verify(N, out))
        else:
            if not (a.pseudo and a.map): sys.exit('compare needs --pseudo DIR and --map DIR')
            pd_, md_ = (os.path.abspath(x).replace('\\', '/') + '/' for x in (a.pseudo, a.map))
            for part in (None, 'train', 'val'): r = compare(N, pd_, md_, part); res.append(r); print(json.dumps(r), flush=True)
    if a.json and res: json.dump(res, open(a.json, 'w', encoding='utf8', newline='\n'), indent=1)
    if a.mode == 'verify' and not all(all(v for k, v in r.items() if k != 'pixels') for r in res): sys.exit('verify: NOT equal (see above)')
