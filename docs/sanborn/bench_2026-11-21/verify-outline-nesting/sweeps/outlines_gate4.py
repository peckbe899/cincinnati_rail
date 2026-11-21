"""Block outlines of a plate from the two networks (15 November 2026).

BENCH COPY of outlines_proposed.py made by make_bench_copy.py (bench_2026-11-21/outline-nesting): only the input/output lines
differ. Run as: PY outlines_bench_final.py N AREA LINES OUTDIR [MASK_CACHE_DIR]. The proposed file's docstring follows.

    cd data/sanborn
    python ../../tools/sanborn/unet/outlines.py N AREA LINES        e.g. 44 edge_v1 lines_v2

The area network (unet.py, unet_data/N_pred_AREA.png) says which ground is block and which is street; the line network
(edgenet.py, unet_data/N_lines_LINES.png) says where the printed block lines are. Neither alone gives an outline: the
area's edge is a few pixels off the line, and the lines are not joined up.
1. Seeds: ground the area network is sure of (block: P > 0.5, SEED_B px in from its edge; street likewise SEED_S px).
2. The ground between the seeds is shared out by a watershed over the line map, so the boundary between block and
   street settles on the ridge of the detected line where there is one.
3. Each block's boundary is cut into sides; a straight line is fitted to every side of MINLEN px or more, then slid
   (up to SLIDE px) and turned onto the strongest detected line beside it; corners are where neighbouring lines meet.
   Ben, 14 November 2026: a street is never wavy.
4. Check, as the label was checked: every side is tested against the print's black/grey ink (on a printed line or not),
   and against the line network (the detected line runs under it or not).
Writes picks22_guided/22-N/outlines.json (polygons, plate px, each side flagged), unet_data/N_outlines.jpg and
N_outlines.json (the counts).

21 November 2026 (bench_2026-11-21/outline-nesting), three changes after the batch of 109 plates:
- Nested blocks and street holes. Every block region's outer contour is a block, also one lying in a street hole of
  another region (RETR_EXTERNAL dropped those: 154 on 28 plates, most inside the margin ring of an uncut sheet), and every
  hole of MIN_AREA or more gives its street sides as a polygon whose sides carry hole=True. Holes come first in the list,
  then the blocks, outermost first, so a reader that fills the polygons in order paints each block over its holes as
  before; a reader that wants street ground skips the hole polygons. 'blocks' counts blocks only. A hole in a block
  region more than HOLE_PARENT times the plate's median block is left out (counted as holes_in_open_land): on plate 44
  those are pockets of unsure ground by Mill Creek, the canal, the railway and big parcels, not streets (3.1k px of side,
  0.1k px of it on Ben's lines), while the holes in merged pairs of blocks are alleys he drew. On the uncut sheets the same rule
  also leaves out many real streets inside merged districts (bench outline-nesting: set HOLE_PARENT = 0 to keep them).
- Map ground on an uncut sheet taken whole from a PDF (cufp/N/source.json says 'pdf'): its margin, KEY, title, scale
  notes and bars, compass roses and inset frames are not map. map_area.py (made in bench_2026-11-21/visual-pdf; it needs
  its templates/ folder beside it) gives the map ground, which is used as the paper: the rest is seeded as street side,
  and sides along it are paper_edge sides, which step 4 of blocks_noguide.py leaves out. On a cut plate nothing changes.
- QA flag. N_outlines.json gets suspect (true/false) and suspect_why, from the census of the batch (bench_2026-11-21/
  census, classify.py): Q1 the sides step 4 keeps are less than 60% of the line length the line network drew (its
  P > 0.43 lines at half size, thinned, on the paper or map ground); Q2 two or more block regions lie inside another
  one's hole (a ring of block ground round them); Q3 the plate's printed scale is not 100 or 200 ft to the inch, the
  scales the networks were trained at, or is not recorded (scale_table.json, read from the sheets' notes); Q5 an uncut
  sheet whose map ground could not be found. Q4 (the area network calls 90% or more of the paper block) is reported in
  'qa' but does not set the flag.
"""
import json, os, sys
import numpy as np
import cv2
N, AREA, LINES = sys.argv[1], sys.argv[2], sys.argv[3]; SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'; HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[4]).replace('\\', '/') + '/'; MASK_CACHE = sys.argv[5] if len(sys.argv) > 5 else None
AREA_PNG = AREA if AREA.lower().endswith('.png') else U + f'{N}_pred_{AREA}.png'; LINES_PNG = LINES if LINES.lower().endswith('.png') else U + f'{N}_lines_{LINES}.png'
SEED_B, SEED_S, TOL, MINLEN, SLIDE, TURN, CORNER, MIN_AREA, CUT = 14, 8, 8.0, 60.0, 12, 5, 120.0, 6000, 130.0
MAP_AREA_DIRS = (HERE, SP + 'bench_2026-11-21/visual-pdf')                       # map_area.py with its templates/ folder
SCALE_TABLES = (SP + 'scale_table.json', SP + 'bench_2026-11-21/census/scale/scale_table.json')   # {N: {ft_per_inch: ...}}
Q1_KEEP, Q2_NESTED, TRAINED_FT = 0.6, 2, (100, 200)
HOLE_PARENT = 4.0                                        # a hole's sides only in a region <= 3 x the median block (0: every hole)
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
pa = cv2.resize(cv2.imread(AREA_PNG, 0), (W, H), interpolation=cv2.INTER_LINEAR)
pl = cv2.imread(LINES_PNG, 0)
paper = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
alpha, qa_why = paper, []
_src = SP + f'cufp/{N}/source.json'; PDF = os.path.exists(_src) and json.load(open(_src, encoding='utf8')).get('source') == 'pdf'
if PDF and MASK_CACHE: alpha = cv2.resize(cv2.imread(os.path.join(MASK_CACHE, f'{N}_mask8.png'), 0), (W, H), interpolation=cv2.INTER_NEAREST) > 127
elif PDF:                                                # an uncut sheet: its map ground is the paper (map_area.py)
    for _d in MAP_AREA_DIRS:
        if os.path.exists(os.path.join(_d, 'map_area.py')) and os.path.isdir(os.path.join(_d, 'templates')): sys.path.insert(0, _d); break
    try:
        import map_area  # noqa: E402
        alpha = map_area.map_mask(full)
    except ImportError: qa_why.append('Q5 uncut sheet, but map_area.py was not found: margin and KEY are not masked')
hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170))
g = cv2.GaussianBlur(np.where(ink, cv2.cvtColor(full, cv2.COLOR_BGR2GRAY), 255).astype(np.uint8), (3, 3), 0).astype(np.float32)
lp = cv2.GaussianBlur(pl, (5, 5), 0).astype(np.float32)
# 1, 2: seeds and watershed over the line map
blk = (pa > 127) & alpha; stt = (pa <= 127) & alpha
el = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
mk = np.zeros((H, W), np.int32)
mk[cv2.erode(stt.astype(np.uint8), el(SEED_S)) > 0] = 1
mk[cv2.erode(blk.astype(np.uint8), el(SEED_B)) > 0] = 2
mk[~alpha] = 1                                           # off the paper counts with the street side: a block ends at the paper's edge
mk[(pl > 127) & (mk == 2)] = 0                           # a detected line inside a block seed is left for the watershed to decide
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
        if along(lp, a3, b3).mean() > 90: a2, b2 = a3, b3            # only onto a line the network actually drew
        # a fitted side under CUT px that is not on a printed line is the cut corner of the area's rounded shape, not a side
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

# every contour with its depth (RETR_TREE): even depth = a block's outer edge, odd = a hole in a block (street ground)
cs, hier = cv2.findContours(block, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE); dep = []
for i in range(len(cs)):
    j, d = i, 0
    while hier[0][j][3] >= 0: j = hier[0][j][3]; d += 1
    dep.append(d)
outers = sorted((i for i in range(len(cs)) if dep[i] % 2 == 0), key=lambda i: dep[i])     # outermost first; depth 0 in RETR_EXTERNAL's order
holes = [i for i in range(len(cs)) if dep[i] % 2 == 1 and cv2.contourArea(cs[i]) >= MIN_AREA]   # a smaller hole is a speck, not a street
nested = sum(dep[i] > 0 for i in outers)
_med = float(np.median([cv2.contourArea(cs[i]) for i in outers])) if outers else 0.0       # open land: a hole in a region far bigger than a block
open_land = [i for i in holes if HOLE_PARENT and cv2.contourArea(cs[hier[0][i][3]]) > HOLE_PARENT * _med]
holes = [i for i in holes if i not in open_land]
polys = []; vis = (full * 0.7 + 76).astype(np.uint8); cnt = dict(sides=0, on_printed_line=0, on_detected_line=0, len_all=0.0, len_ink=0.0, len_det=0.0, short_pieces=0)
if alpha is not paper: vis[~alpha] = (vis[~alpha] * 0.6).astype(np.uint8)            # off the map ground: darker
inner = cv2.erode(alpha.astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
nblocks = nholes = 0
for ci, is_hole in [(i, True) for i in holes] + [(i, False) for i in outers]:
    sides = straighten(cs[ci][:, 0, :])
    if not sides or len(sides) < 3: continue
    rec = []
    for s in sides:
        a, b = s['a'], s['b']; L = float(np.hypot(*(b - a))); m = ((a + b) / 2).astype(int)
        inside = 0 <= m[0] < W and 0 <= m[1] < H and inner[m[1], m[0]]
        if s['kind'] != 'line' or L < 28:
            cnt['short_pieces'] += 1; rec.append(dict(a=a.round(1).tolist(), b=b.round(1).tolist(), state='short', **({'hole': True} if is_hole else {})))
            cv2.line(vis, tuple(a.round().astype(int)), tuple(b.round().astype(int)), (150, 150, 150), 3, cv2.LINE_AA); continue
        ik = on_ink(a, b); dt = bool(along(lp, a, b).mean() > 90)
        if inside:
            cnt['sides'] += 1; cnt['on_printed_line'] += ik; cnt['on_detected_line'] += dt; cnt['len_all'] += L; cnt['len_ink'] += L * ik; cnt['len_det'] += L * dt
        rec.append(dict(a=a.round(1).tolist(), b=b.round(1).tolist(), state='on print' if ik else ('on detected line only' if dt else 'not on a line'), paper_edge=not inside, **({'hole': True} if is_hole else {})))
        cv2.line(vis, tuple(a.round().astype(int)), tuple(b.round().astype(int)), (0, 150, 0) if ik else ((0, 150, 255) if dt else (0, 0, 230)), 4, cv2.LINE_AA)
    polys.append(rec); nholes += is_hole; nblocks += not is_hole
# QA flag (census of the 21 Nov batch): what reaches the line editor against what the line network drew; nesting; scale
ah = cv2.resize(alpha.astype(np.uint8), (W // 2, H // 2), interpolation=cv2.INTER_NEAREST)
ph = (cv2.resize(pl, (W // 2, H // 2), interpolation=cv2.INTER_AREA) > 110) & (cv2.erode(ah, np.ones((15, 15), np.uint8)) > 0)
_thin = getattr(getattr(cv2, 'ximgproc', None), 'thinning', None)                     # opencv-contrib (the networks' venv has it)
skel = int((_thin(ph.astype(np.uint8) * 255) > 0).sum()) * 2 if _thin else None
keep = round(cnt['len_all'] / skel, 3) if skel else None   # len_all = the sides step 4 keeps (on the paper, not short)
ft = next((json.load(open(f, encoding='utf8')).get(N, {}).get('ft_per_inch') for f in SCALE_TABLES if os.path.exists(f)), None)
if keep is not None and keep < Q1_KEEP: qa_why.append(f'Q1 the editor gets {100 * keep:.0f}% of the line length the line network drew')
if nested >= Q2_NESTED: qa_why.append(f'Q2 {nested} block regions lie inside another block region')
if ft not in TRAINED_FT: qa_why.append(f'Q3 scale {ft} ft to the inch' if ft else 'Q3 scale not recorded')
qa = dict(editor_len_px=round(cnt['len_all']), line_skel_len_px=skel, editor_per_line=keep, nested_regions=nested, ft_per_inch=ft,
          area_block_share=round(float((pa[paper] > 127).mean()), 3), map_ground_share_of_paper=round(float(alpha.sum() / max(1, paper.sum())), 3))
if _thin is None: qa['Q1'] = 'not computed: this OpenCV has no ximgproc.thinning'
if qa['area_block_share'] >= 0.9: qa['Q4'] = 'the area network calls 90% or more of the paper block (not part of the flag)'
for k_, t_ in enumerate(qa_why): cv2.putText(vis, 'SUSPECT ' + t_, (60, 140 + 90 * k_), cv2.FONT_HERSHEY_SIMPLEX, 2.4, (0, 0, 200), 6, cv2.LINE_AA)
os.makedirs(OUT, exist_ok=True)
json.dump(polys, open(OUT + 'outlines.json', 'w', encoding='utf8', newline='\n'))
rep = dict(plate=N, area=AREA, lines=LINES, blocks=nblocks, sides=cnt['sides'], on_printed_line=cnt['on_printed_line'], on_detected_line=cnt['on_detected_line'], short_pieces=cnt['short_pieces'],
           share_on_printed_line_by_length=round(cnt['len_ink'] / max(1.0, cnt['len_all']), 3), share_on_detected_line_by_length=round(cnt['len_det'] / max(1.0, cnt['len_all']), 3),
           holes=nholes, holes_in_open_land=len(open_land), map_ground='map_area.py' if alpha is not paper else 'paper', suspect=bool(qa_why), suspect_why=qa_why, qa=qa)
json.dump(rep, open(OUT + f'{N}_outlines.json', 'w', encoding='utf8', newline='\n'), indent=1)
cv2.imwrite(OUT + f'{N}_outlines.jpg', cv2.resize(vis, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
cv2.imwrite(OUT + f'{N}_blockmask.png', cv2.resize(block * 255, (W // 2, H // 2), interpolation=cv2.INTER_NEAREST))
print(json.dumps(rep))
