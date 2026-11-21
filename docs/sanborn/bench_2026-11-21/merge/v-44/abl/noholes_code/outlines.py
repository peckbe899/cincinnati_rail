"""Block outlines of a plate from the two networks (15 November 2026; one merged outline step 21 November 2026).

    cd data/sanborn
    python ../../tools/sanborn/unet/outlines.py N AREA LINES        e.g. 44 edge_v1 lines_v2
    python ../../tools/sanborn/unet/outlines.py N AREA LINES --area-png P --lines-png P --out DIR     (a bench run)
      [--bins-png P | none] [--hole-parent X] [--force]

The area network (unet.py, unet_data/N_pred_AREA.png) says which ground is block and which is street; the line network
(edgenet.py, unet_data/N_lines_LINES.png) says where the printed block lines are. Neither alone gives an outline: the
area's edge is a few pixels off the line, and the lines are not joined up.
1. Seeds: ground the area network is sure of (block: P > 0.5, SEED_B px in from its edge; street likewise SEED_S px).
   Every block seed is cut by the detected lines (dilated MK_CUT px) and each piece of MK_SEED_MIN px or more is a marker
   of its own, so two blocks the area network joins across an alley stay apart where the line network drew the line
   between them (one marker per closed basin).
2. The ground between the seeds is shared out by a watershed over the line map, so the boundary between block and
   street (or between two blocks) settles on the ridge of the detected line where there is one. Each block is then
   opened, size-checked and traced on its own, with its holes (RETR_CCOMP).
3. Each block's boundary, and each street hole in it, is cut into sides; a straight line is fitted to every side of
   MINLEN px or more, then slid (up to SLIDE px) and turned onto the strongest detected line beside it. Ben, 14 November
   2026: a street is never wavy. The sides are closed into a ring, so a block closes in the line editor: neighbouring
   sides on one straight line are joined into one side (and slid again); each side runs on to meet the next where their
   lines cross (within RING_CORNER px); where they do not cross, ends within SNAP_JOIN px are joined and a wider gap gets
   a bridging side. Short pieces are dropped.
4. Check, as the label was checked: every side is tested against the print's black/grey ink (on a printed line or not),
   against the line network (the detected line runs under it or not) and against the rail the ink rules found.
Side states: 'on print' (on ink AND on the detected line; green in the editor), 'on print only' (ink, no detected line),
'on detected line only', 'not on a line', 'on rail' (with 'was', the state it would have had, and 'rail', the share of
its length on the rail). Every side has paper_edge; bridging sides carry 'bridge' (why: parallel, far, back); the
sides of a street hole carry hole=True.
Writes picks22_guided/22-N/outlines.json (polygons, plate px), unet_data/N_outlines.json (the counts, the QA flag and
the outline step's 'version'), N_outlines.jpg, N_blockmask.png and, on an uncut sheet, N_mapground.png (the map ground
at 1/8 size, 255 = map; ink_bins.py reads it). With --out DIR all of them go to DIR instead (outlines.json as
DIR/outlines.json), with DIR/N_blockinst.png (the blocks as 16-bit labels at half size, for bench44.py), and nothing is
written in the repo. --area-png and --lines-png read other maps than unet_data's (AREA and LINES are then only names in
the counts); --bins-png reads other ink bins than unet_data/N_bins.png for the rail test ('none': as if there were
none); --hole-parent sets HOLE_PARENT (for the bench).

21 November 2026, after the batch of 109 plates (run_plates.py). Ben: "Yes, merge it". The changes measured on the bench
(data/sanborn/bench_2026-11-21: outline-quality, outline-nesting and the critic; docs/sanborn/bench_2026-11-21) are
merged here into one step (merge/impl has the measurements), with three more:
- One watershed marker per block, each block traced on its own (outline-quality). Tracing the union of the blocks
  joined touching blocks again. Plate 44, the batch's maps: PQ 0.431 -> 0.543; over 6 tile grids +0.07 (sd 0.03).
- Closed rings (outline-quality): before, step 4 of blocks_noguide.py dropped the short pieces and no outline stayed a
  ring (0 of Ben's 55 blocks closed on 44). The ring settings were chosen on one fold of 44 and held on the other.
- Green gate (outline-quality): 'on print' needs the detected line too; ink alone is 'on print only' (orange). Green
  lines on 44 right 78% -> 84%.
- Street holes (outline-nesting): each block is traced with RETR_CCOMP; every hole of MIN_AREA or more gives its street
  sides as a polygon with hole=True. Holes come first in the list, then the blocks, outermost first, so a reader that
  fills the polygons in order paints each block over its holes; 'blocks' counts blocks only. A hole in a block more than
  HOLE_PARENT times the plate's median block is left out (holes_in_open_land): on 44 those are pockets of unsure ground
  by Mill Creek, the canal, the railway and big parcels, not streets. HOLE_PARENT was chosen on fold A of 44 and checked
  on fold B (merge/impl hole_sweep.sh, hole_table.py): on A every value from 1.5 to 4 gives the same best numbers (0
  and 6 or more show more wrong lines); on B 2 to 4 are the same and 1.5 loses recall. 3 is kept. On the uncut sheets
  the gate also leaves out many real streets inside merged districts (HOLE_PARENT = 0 keeps every hole).
- Map ground on an uncut sheet taken whole from a PDF (cufp/N/source.json says 'pdf'; outline-nesting): map_area.py,
  beside this file with its templates/, finds the map ground, and the rest (margin, KEY, title, scale notes and bars,
  compass roses, inset frames) is seeded as street side. A side is paper_edge (step 4 leaves it out) only where it runs
  along the paper's edge (within map_area's EDGE_BAND of it, where map_area reads no ink) or along the printed
  furniture and frames map_area found. A side along the plain edge of the map ground, where the drawing simply stops, is
  judged like any other side: a street along the map's border is on ink and kept, an imagined side on blank paper is
  'not on a line' and step 4 drops it. (The bench version made every side along the map edge paper_edge.) On the 24
  200-ft sheets step 4 now keeps 817 lines (203k px) within 40 px of the map's edge, against the bench version's 196
  (26k px); most are orange (on ink, no detected line), e.g. Ruth Ave and Madison Rd on 79. Not fixed by this: the far
  side of the outermost street (Madison Rd's north side on 79), which the batch had as a side of the margin it called
  block. With the margin masked no block lies beyond it, so it is not a side at all: of the 250 batch lines the bench
  version lost along the map edge, 20 come back (merge/impl pdf_edge.py). On a cut plate nothing changes.
- Rail (new; bench visual-cut VC-3 and critic K8: on 44 the 32 editor lines lying mostly on the rail ink were all
  wrong). A side with more than RAIL_SHARE of its length within RAIL_TOL px of railroad ink is 'on rail';
  blocks_noguide.py's RAIL_DROP says whether step 4 leaves it out or shows it orange. On 44 the 34 'on rail' sides are
  2.7% on Ben's lines (11.7k px), so step 4 leaves them out. The railroad ink is the ink sorting's bin 4
  (unet_data/N_bins.png, ink_bins.py) where the plate was sorted with a block ground (N_bins.json 'ground_from': Ben's
  street map, this step's blocks, or the old label). Otherwise the railroad rule (ink_bins.railroad) is run here once,
  on the block ground of these outlines and with Ben's tracks (rail_ben.json), as the ink sorting will run it next:
  on a plate never sorted (run_plates.py now runs this step BEFORE the ink sorting, which needs these block lines)
  and on the plates the batch of 21 Nov sorted with no blocks at all. Those bins call railroad what the tick rule finds
  on block lines lettered with house numbers: on plate 5 they put 5 real green block sides on the railroad; run here on
  the blocks, the rule puts 1. Streetcar ink (bin 5) is not used: a streetcar runs down a street, and on 5 its dashes
  lay along 6 more real block sides, while on 44 no wrong side lay on it. Cost: the step takes 10-20 s more where the
  rule runs here. N_outlines.json 'rail' says which railroad ink was used.
- QA flag (outline-nesting, thresholds from the census of the batch): N_outlines.json gets suspect and suspect_why:
  Q1 the lines step 4 keeps (blocks_noguide.step4: what the line editor gets) are less than 60% of the line length the
  line network drew (its P > 0.43 lines at half size, thinned, on the paper or map ground; needs cv2.ximgproc, which the
  networks' venv has); Q2 two or more block regions of the union of the blocks lie inside another one's hole (a ring of
  block ground round them); Q3 the plate's printed scale is not 100 or 200 ft to the inch, the scales the networks were
  trained at, or is not recorded (data/sanborn/scale_table.json, read from the sheets' notes); Q5 an uncut sheet whose
  map ground could not be found. Q4 (the area network calls 90% or more of the paper block) is reported in 'qa' only.
- 'version' in N_outlines.json: blocks_noguide.outline_version(), a short hash of outlines.py, blocks_noguide.py and
  map_area.py; run_plates.py keeps it per plate and redoes only this step where it changed.
- Guard: make_labels.py and crop.py read picks22_guided/22-N/outlines.json of the placed plates (43, 44, 45, 80, 82A)
  as training input (the line targets of the next training). On a plate with a guide (unet_data/N_guide.png) an
  existing outlines.json is not written over unless --force is given; --out writes elsewhere.
"""
import argparse, json, os, sys, time
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, HERE)
import _ws  # noqa: E402
from blocks_noguide import step4, outline_version  # noqa: E402   (step 4: what the line editor gets of these outlines, for Q1)
ap = argparse.ArgumentParser(description='block outlines of plate N from the area and line networks (see the docstring)')
ap.add_argument('N'); ap.add_argument('AREA'); ap.add_argument('LINES')
ap.add_argument('--area-png', help='area map to read (default unet_data/N_pred_AREA.png)'); ap.add_argument('--lines-png', help='line map to read (default unet_data/N_lines_LINES.png)')
ap.add_argument('--bins-png', help="ink bins for the rail test (default unet_data/N_bins.png; 'none': as if there were none)")
ap.add_argument('--out', help='write every output into this folder, and nothing into the repo')
ap.add_argument('--hole-parent', type=float, help='HOLE_PARENT for this run (bench)')
ap.add_argument('--force', action='store_true', help="write over a placed plate's outlines.json (a training target)")
ARG = ap.parse_args(); N, AREA, LINES = ARG.N, ARG.AREA, ARG.LINES; SP = _ws.DATA; U = SP + 'unet_data/'; T0 = time.time()
SCALE_TABLE = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'data', 'sanborn', 'scale_table.json'))   # data/sanborn/scale_table.json of the repo this file is in
SEED_B, SEED_S, TOL, MINLEN, SLIDE, TURN, CORNER, MIN_AREA, CUT = 14, 8, 8.0, 60.0, 12, 5, 120.0, 6000, 130.0
MK_CUT, MK_SEED_MIN = 3, 2000                                                  # block markers: seeds cut by the detected lines
RING_CORNER, COLIN_ANG, COLIN_OFF, COLIN_GAP, SNAP_JOIN = 400.0, 4.0, 12.0, 250.0, 12.0   # closing the rings
HOLE_PARENT = 3.0 if ARG.hole_parent is None else ARG.hole_parent   # a hole's sides only in a block <= 3 x the median block (0: every hole)
RAIL_TOL, RAIL_SHARE = 3, 0.5                            # 'on rail': more than half the side within 3 px of rail ink
Q1_KEEP, Q2_NESTED, TRAINED_FT = 0.6, 2, (100, 200)
el = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))

if ARG.out:
    O = os.path.abspath(ARG.out).replace('\\', '/') + '/'; os.makedirs(O, exist_ok=True)
    F_POLYS, F_REP, F_JPG, F_MASK, F_MAP = O + 'outlines.json', O + f'{N}_outlines.json', O + f'{N}_outlines.jpg', O + f'{N}_blockmask.png', O + f'{N}_mapground.png'
else:
    F_POLYS, F_REP, F_JPG, F_MASK, F_MAP = SP + f'picks22_guided/22-{N}/outlines.json', U + f'{N}_outlines.json', U + f'{N}_outlines.jpg', U + f'{N}_blockmask.png', U + f'{N}_mapground.png'
    if os.path.exists(U + f'{N}_guide.png') and os.path.exists(F_POLYS) and not ARG.force:
        sys.exit(f'plate {N} is placed (unet_data/{N}_guide.png): picks22_guided/22-{N}/outlines.json is left as it is, because make_labels.py and '
                 f'crop.py read it as training input (the line targets of the next training). Use --out DIR to write elsewhere, or --force to write over it.')
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
pa = cv2.resize(cv2.imread(ARG.area_png or U + f'{N}_pred_{AREA}.png', 0), (W, H), interpolation=cv2.INTER_LINEAR)
pl = cv2.imread(ARG.lines_png or U + f'{N}_lines_{LINES}.png', 0)
paper = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
alpha, fixed, qa_why, ma_flags, mask8 = paper, None, [], None, None   # alpha: where blocks may lie; fixed: what a side along is paper_edge (None: off alpha)
_src = SP + f'cufp/{N}/source.json'; PDF = os.path.exists(_src) and json.load(open(_src, encoding='utf8')).get('source') == 'pdf'
if PDF:                                                  # an uncut sheet: its map ground is the paper (map_area.py)
    try:
        import map_area  # noqa: E402
        _m = map_area.map_area(full); alpha, ma_flags, mask8 = _m['mask'], _m['flags'], _m['mask8']
        _in8 = cv2.erode(_m['paper8'].astype(np.uint8), el(map_area.EDGE_BAND)) > 0           # the paper less the band where map_area reads no ink
        fixed = cv2.resize((~_in8 | _m['furniture8'] | _m['frames8']).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
        del _m, _in8
    except Exception as e: qa_why.append(f'Q5 uncut sheet, but its map ground was not found ({type(e).__name__}: {e}): margin and KEY are not masked')
hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170))
g = cv2.GaussianBlur(np.where(ink, cv2.cvtColor(full, cv2.COLOR_BGR2GRAY), 255).astype(np.uint8), (3, 3), 0).astype(np.float32)
lp = cv2.GaussianBlur(pl, (5, 5), 0).astype(np.float32); del hsv, ink
# 1, 2: seeds, one marker per block, and the watershed over the line map
blk = (pa > 127) & alpha; stt = (pa <= 127) & alpha
mk = np.zeros((H, W), np.int32)
mk[cv2.erode(stt.astype(np.uint8), el(SEED_S)) > 0] = 1
seed = (cv2.erode(blk.astype(np.uint8), el(SEED_B)) > 0) & (cv2.dilate((pl > 127).astype(np.uint8), el(MK_CUT)) == 0)   # a detected line cuts the seed
n, cc, st, _ = cv2.connectedComponentsWithStats(seed.astype(np.uint8), connectivity=4)
lut = np.where(st[:, cv2.CC_STAT_AREA] >= MK_SEED_MIN, np.arange(n) + 1, 0).astype(np.int32); lut[0] = 0   # markers 2 .. n; crumbs left to the watershed
lab = lut[cc]; mk[lab > 0] = lab[lab > 0]
mk[~alpha] = 1                                           # off the paper (or the map ground) counts with the street side: a block ends there
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
del cc, lab, ws, cc4, wl, seed, mk, blk, stt

def along(img, a, b, o=0.0):
    d = b - a; L = np.hypot(*d); nrm = np.array([-d[1], d[0]]) / (L or 1); t = np.linspace(0.06, 0.94, max(10, int(L))); q = a + np.outer(t, d) + nrm * o
    x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1); return img[y, x]
def on_ink(a, b):
    d = b - a; nrm = np.array([-d[1], d[0]]) / np.hypot(*d)
    return bool(max(np.mean([along(g, a + nrm * s, b + nrm * s, o).mean() for o in (-6, -3, 3, 6)]) - along(g, a + nrm * s, b + nrm * s).mean() for s in (-2, -1, 0, 1, 2)) > 25)

SHORT = [0]                                              # short pieces dropped from the rings (counted)
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
    SHORT[0] += sum(l['kind'] != 'line' for l in lines)
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

# 3: each block traced on its own (tracing the union would join touching blocks again), with its holes (RETR_CCOMP)
ys, xs = np.nonzero(inst); lab = inst[ys, xs]; K = len(keep)
bx0 = np.full(K + 1, 1 << 30); bx1 = np.zeros(K + 1, int); by0 = np.full(K + 1, 1 << 30); by1 = np.zeros(K + 1, int)
np.minimum.at(bx0, lab, xs); np.maximum.at(bx1, lab, xs); np.minimum.at(by0, lab, ys); np.maximum.at(by1, lab, ys); del ys, xs, lab
outs, hls = [], []                                       # block outlines; holes as (contour, area of their block)
for i in range(1, K + 1):
    cs_, hr_ = cv2.findContours((inst[by0[i]:by1[i] + 1, bx0[i]:bx1[i] + 1] == i).astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE, offset=(int(bx0[i]), int(by0[i])))
    for c, h in zip(cs_, hr_[0]):
        if h[3] < 0: outs.append(c)
        else: hls.append((c, cv2.contourArea(cs_[h[3]])))
_med = float(np.median([cv2.contourArea(c) for c in outs])) if outs else 0.0        # open land: a hole in a block far bigger than a block
_hb = [cv2.boundingRect(c) for c, _ in hls]; dep = []                                # a block lying in another block's hole comes after it
for c in outs:
    x_, y_ = (float(v) for v in c[0, 0])
    dep.append(sum(1 for (h, _), (hx, hy, hw, hh) in zip(hls, _hb) if hx <= x_ < hx + hw and hy <= y_ < hy + hh and cv2.pointPolygonTest(h, (x_, y_), False) > 0))
holes = [(c, pa_) for c, pa_ in hls if cv2.contourArea(c) >= MIN_AREA]           # a smaller hole is a speck, not a street
open_land = [c for c, pa_ in holes if HOLE_PARENT and pa_ > HOLE_PARENT * _med]; n_found = len(holes)
holes = []   # v-44 ablation: no street holes
_cs, _hr = cv2.findContours(block, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE); nested = 0   # Q2: regions of the union of the blocks nested in another's hole
for i in range(len(_cs)):
    j, d = i, 0
    while _hr[0][j][3] >= 0: j = _hr[0][j][3]; d += 1
    nested += d > 0 and d % 2 == 0
del _cs, _hr, _hb
inner = cv2.erode((alpha if fixed is None else ~fixed).astype(np.uint8), np.ones((31, 31), np.uint8)) > 0   # a side whose middle is outside runs along the edge
polys, kinds = [], []
for c, is_hole in [(c, True) for c in holes] + [(outs[j], False) for j in sorted(range(len(outs)), key=lambda j: dep[j])]:
    sides = straighten(c[:, 0, :])
    if not sides or len(sides) < 3: continue
    rec = []
    for s in sides:
        a, b = s['a'], s['b']; m = ((a + b) / 2).astype(int)
        inside = 0 <= m[0] < W and 0 <= m[1] < H and inner[m[1], m[0]]
        ik = on_ink(a, b); dt = bool(along(lp, a, b).mean() > 90)
        state = 'on print' if (ik and dt) else ('on print only' if ik else ('on detected line only' if dt else 'not on a line'))   # green needs the line network too
        r = dict(a=a.round(1).tolist(), b=b.round(1).tolist(), state=state, paper_edge=not inside)
        if s['kind'] == 'bridge': r['bridge'] = s['why']
        if is_hole: r['hole'] = True
        rec.append(r); kinds.append((ik, dt))
    polys.append(rec)
# 4b: the rail (railroad only: bin 4). The ink sorting's railroad where its bins were sorted with a block ground; else
# the railroad rule run here on the block ground of these outlines, with Ben's tracks, as the ink sorting will run it
_bf = None if (ARG.bins_png or '').lower() == 'none' else (ARG.bins_png or U + f'{N}_bins.png')
_bins = cv2.imread(_bf, cv2.IMREAD_UNCHANGED) if _bf and os.path.exists(_bf) else None
_bj = json.load(open(_bf[:-4] + '.json', encoding='utf8')) if _bf and os.path.exists(_bf[:-4] + '.json') else {}
_blocks_known = bool(ARG.bins_png) or _bj.get('ground_from') in ('map', 'nets', 'label') or ('ground_from' not in _bj and 'NO STREET MAP' not in _bj.get('note', 'NO STREET MAP')) \
    or ('ground_from' not in _bj and os.path.exists(U + f'{N}_label.png'))   # bins sorted before 21 Nov 2026 have no 'ground_from': a street map or the old label
if _bins is not None and _bins.shape == (H, W) and _blocks_known:
    rail = (_bins == 4).astype(np.uint8); rail_how = f'railroad bin of {os.path.basename(_bf)} (made {time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(_bf)))})'
else:
    import ink_bins as IB  # noqa: E402   (the same railroad rule, block ground and handling of Ben's tracks the ink sorting uses)
    _al = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy'), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    _ink = (cv2.cvtColor(full, cv2.COLOR_BGR2LAB)[..., 0] < IB.INK_L) & _al
    _rr, _ = IB.railroad(_ink, IB.block_ground(polys, H, W), _al)
    _rf = SP + f'picks22_guided/22-{N}/rail_ben.json'; _rb = json.load(open(_rf, encoding='utf8')) if os.path.exists(_rf) else {}
    if _rb.get('tracks'): _rr = IB.ben_railroad(_rr, _ink, IB.ben_masks(_rb['tracks'], H, W), bool(_rb.get('complete')))
    rail = _rr.astype(np.uint8); del _al, _rr, _ink
    rail_how = 'railroad rule run here (ink_bins.railroad on these blocks' + (', with the tracks in rail_ben.json' if _rb.get('tracks') else '') + '): ' + \
               ('no ink bins' if _bins is None else ('the ink bins were sorted with no blocks at all' if not _blocks_known else 'the ink bins are another size')) + (' (--bins-png none)' if _bf is None else '')
del _bins
rail = cv2.dilate(rail, el(RAIL_TOL))
cnt = dict(sides=0, on_printed_line=0, on_detected_line=0, on_rail=0, len_all=0.0, len_ink=0.0, len_det=0.0, short_pieces=SHORT[0], bridges=0)
vis = (full * 0.7 + 76).astype(np.uint8)
if alpha is not paper: vis[~alpha] = (vis[~alpha] * 0.6).astype(np.uint8)            # off the map ground: darker
k_ = 0
for rec in polys:
    for r in rec:
        a, b = np.array(r['a']), np.array(r['b']); L = float(np.hypot(*(b - a))); ik, dt = kinds[k_]; k_ += 1
        rs = float(along(rail, a, b).mean())
        if rs > RAIL_SHARE: r['was'] = r['state']; r.update(state='on rail', rail=round(rs, 2))
        if not r['paper_edge']:
            cnt['sides'] += 1; cnt['on_printed_line'] += ik; cnt['on_detected_line'] += dt; cnt['on_rail'] += r['state'] == 'on rail'; cnt['len_all'] += L; cnt['len_ink'] += L * ik; cnt['len_det'] += L * dt
        cnt['bridges'] += 'bridge' in r
        col = (150, 150, 150) if r['paper_edge'] else {'on print': (0, 150, 0), 'on rail': (200, 0, 200), 'not on a line': (0, 0, 230)}.get(r['state'], (0, 150, 255))
        cv2.line(vis, tuple(a.round().astype(int)), tuple(b.round().astype(int)), col, 3 if r['paper_edge'] else 4, cv2.LINE_AA)
nholes = sum(1 for p in polys if p[0].get('hole')); nblocks = len(polys) - nholes
# QA flag (census of the 21 Nov batch): what reaches the line editor against what the line network drew; nesting; scale
ed = step4(polys); ed_len = float(sum(np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1]) for e in ed))
ah = cv2.resize(alpha.astype(np.uint8), (W // 2, H // 2), interpolation=cv2.INTER_NEAREST)
ph = (cv2.resize(pl, (W // 2, H // 2), interpolation=cv2.INTER_AREA) > 110) & (cv2.erode(ah, np.ones((15, 15), np.uint8)) > 0)
_thin = getattr(getattr(cv2, 'ximgproc', None), 'thinning', None)                     # opencv-contrib (the networks' venv has it)
skel = int((_thin(ph.astype(np.uint8) * 255) > 0).sum()) * 2 if _thin else None
keep_share = round(ed_len / skel, 3) if skel else None
ft = (json.load(open(SCALE_TABLE, encoding='utf8')).get(N) or {}).get('ft_per_inch') if os.path.exists(SCALE_TABLE) else None
if keep_share is not None and keep_share < Q1_KEEP: qa_why.append(f'Q1 the editor gets {100 * keep_share:.0f}% of the line length the line network drew')
if nested >= Q2_NESTED: qa_why.append(f'Q2 {nested} block regions lie inside another block region')
if ft not in TRAINED_FT: qa_why.append(f'Q3 scale {ft} ft to the inch' if ft else 'Q3 scale not recorded')
qa = dict(editor_len_px=round(ed_len), editor_sides=len(ed), line_skel_len_px=skel, editor_per_line=keep_share, nested_regions=nested, ft_per_inch=ft,
          area_block_share=round(float((pa[paper] > 127).mean()), 3), map_ground_share_of_paper=round(float(alpha.sum() / max(1, paper.sum())), 3))
if ma_flags is not None: qa['map_area_flags'] = ma_flags
if _thin is None: qa['Q1'] = 'not computed: this OpenCV has no ximgproc.thinning'
if qa['area_block_share'] >= 0.9: qa['Q4'] = 'the area network calls 90% or more of the paper block (not part of the flag)'
for k_, t_ in enumerate(qa_why): cv2.putText(vis, 'SUSPECT ' + t_, (60, 140 + 90 * k_), cv2.FONT_HERSHEY_SIMPLEX, 2.4, (0, 0, 200), 6, cv2.LINE_AA)
if not ARG.out: os.makedirs(SP + f'picks22_guided/22-{N}', exist_ok=True)
json.dump(polys, open(F_POLYS, 'w', encoding='utf8', newline='\n'))
rep = dict(plate=N, area=AREA, lines=LINES, version=outline_version(), blocks=nblocks, sides=cnt['sides'], on_printed_line=cnt['on_printed_line'], on_detected_line=cnt['on_detected_line'], short_pieces=cnt['short_pieces'],
           share_on_printed_line_by_length=round(cnt['len_ink'] / max(1.0, cnt['len_all']), 3), share_on_detected_line_by_length=round(cnt['len_det'] / max(1.0, cnt['len_all']), 3), bridges=cnt['bridges'],
           holes=nholes, holes_found=n_found, holes_in_open_land=len(open_land), hole_parent=HOLE_PARENT, on_rail=cnt['on_rail'], rail=rail_how,
           map_ground='map_area.py' if alpha is not paper else 'paper', suspect=bool(qa_why), suspect_why=qa_why, qa=qa, seconds=round(time.time() - T0, 1))
if ARG.area_png or ARG.lines_png: rep['maps'] = dict(area=ARG.area_png or U + f'{N}_pred_{AREA}.png', lines=ARG.lines_png or U + f'{N}_lines_{LINES}.png')
json.dump(rep, open(F_REP, 'w', encoding='utf8', newline='\n'), indent=1)
cv2.imwrite(F_JPG, cv2.resize(vis, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
cv2.imwrite(F_MASK, cv2.resize(block * 255, (W // 2, H // 2), interpolation=cv2.INTER_NEAREST))
if mask8 is not None: cv2.imwrite(F_MAP, mask8.astype(np.uint8) * 255)
if ARG.out: cv2.imwrite(O + f'{N}_blockinst.png', cv2.resize(inst.astype(np.uint16), (W // 2, H // 2), interpolation=cv2.INTER_NEAREST))
print(json.dumps(rep))
