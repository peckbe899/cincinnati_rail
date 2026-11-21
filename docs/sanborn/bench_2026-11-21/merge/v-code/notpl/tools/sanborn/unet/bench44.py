"""bench44: the plate-44 benchmark of the block-recognition chain (21 November 2026; in tools with the merged outline
step, 21 November 2026).

Plate 44 is the ground truth (Ben, 21 Nov 2026: "The 44 plate is the ground-truth"): streetmap/22-44.json, his 55
closed blocks and 359 street sides (printed 254, drawn 66, sheet_edge 39). 44 was held out of training of area_ng1 and
lines_ng1. The batch (run_plates.py) wrote 44's two network maps but refused the outline step on 44 (it has a guide),
so the outline step is run here on those maps, into a run folder of this bench (outlines.py --out: nothing is written
in picks22_guided or unet_data).

Made on the bench (data/sanborn/bench_2026-11-21/bench44/bench44.py, docs/sanborn/bench_2026-11-21) and moved here when
the outline step was merged (Ben, 21 Nov 2026: "Yes, merge it"). It now runs the REAL outline step (outlines.py, beside
this file, with --area-png, --lines-png and --out) and the REAL step 4 (blocks_noguide.step4) and the line editor's
own clean() and sheet() (edit_server.py). Scores, JSON keys and folds are the bench's, unchanged.

    cd data/sanborn
    python ../../tools/sanborn/unet/bench44.py [--area PNG] [--lines PNG] [--tag NAME] [--reuse] [--runs DIR]
    python ../../tools/sanborn/unet/bench44.py --grids DIR [--jobs 3]            every grid of the networks' maps

  --area      half-size P(block)*255 map             default unet_data/44_pred_area_ng1.png   (the batch's)
  --lines     full-size P(line)*255 map              default unet_data/44_lines_lines_ng1.png (the batch's)
  --python    interpreter for the outline step       default the networks' venv (the batch ran it there)
  --outline-args="..."  more options for outlines.py, e.g. --outline-args="--hole-parent 2" (quote a path with spaces)
  --keep-unlined, --rail-show   step 4 with KEEP_UNLINED = True / RAIL_DROP = False (blocks_noguide.py)
  --outlines  another outline step (a hook, as on the bench): a .py file run as
                  PY FILE 44 AREA_PNG LINES_PNG RUN_DIR        (cwd data/sanborn)
              It must write RUN_DIR/outlines.json (outlines.py's polygon format) and print its counts json (with
              share_on_printed_line_by_length) as the last stdout line. It may write RUN_DIR/44_blockmask.png
              (half-size block mask) and RUN_DIR/44_blockinst.png (half-size 16-bit block instances) for the
              watershed stage of the breakdown.            default: outlines.py itself
  --step4     a .py file defining step4(polys) -> edges list (N_edges.json format); default blocks_noguide.step4
  --tag       run name -> RUNS/TAG/ (default from the inputs' names)
  --runs      where the run folders go               default data/sanborn/bench44_runs/
  --reuse     reuse RUN_DIR/outlines.json if it is there (score only)
  --faith     faithfulness check only: the outline step (--outlines) on the guided maps (edge_v1 + lines_v2) must give
              the stored picks22_guided/22-44/outlines.json byte for byte. Only the outline step before the merge does
              (the bench's outlines_copy.py); the merged one adds street holes and closed rings
  --grids DIR one subfolder per tile grid, each with 44_area.png and 44_lines.png (data/sanborn/bench44_maps/grid0..5:
              the batch's networks with their tile grids moved, 6 equally valid maps of 44; bench inference agent).
              Every grid is run (tag TAG__GRID) and RUNS/TAG_grids.json gets the mean and sd of every headline score
              (all, A, B) over the grids; with --paired 'PATH/{grid}/bench44.json' (another chain's run on the same
              grids, {grid} standing for the grid's folder name) also the paired gains, grid by grid. A change is
              judged by its paired gain over the grids
              (critic K1, K10: one grid moves PQ by sd 0.015 on the whole plate, about 0.03 in a fold)
  --tol       line tolerance px (default 5.0)   --ang  direction tolerance degrees (default 20)

Writes RUNS/TAG/: outlines.json etc. (from the outline step), 44_edges.json (step 4 = what N_edges.json would hold),
44_shown.json (what the line editor shows: edit_server.clean of the edges, plus edit_server.sheet), bench44.json (all
scores) and 44_bench.jpg (quarter size: shown lines on Ben's lines green, off them red, his lines missed blue). The full
json also goes to stdout; progress goes to stderr. The decided-ground mask is cached in RUNS/cache/.

WHAT IS SCORED (full-size plate px unless said)
 blocks   COCO panoptic quality, match at IoU > 0.5, rasters at half size. merges = predicted blocks that hold >= 50% of
          each of 2+ true blocks; gt_lost_in_merges / gt_split / gt_missed_other say why true blocks were missed.
          '..._decided' = the same restricted to the ground Ben decided, COCO's void rule: ground he did not decide is
          void, a predicted block more than half in void is not a false positive, and void pixels leave its area.
          Decided ground = his 55 blocks + street ground between them: a pixel off his blocks counts when (distance to
          the nearest block) + (distance to the nearest other block or to the paper's edge) <= 260 px (streets up to
          about 120 ft at 200 ft to the inch; the railway corridor and the open land by the creek stay void).
 lines    every line sampled each 1 px; a sample is matched when a sample of the other set is within TOL px (5) and
          the two directions differ by <= ANG degrees (20). recall = matched share of Ben's length, precision =
          matched share of the shown length (against all his lines, sheet_edge included). Interior = printed + drawn.
 closure  shown lines + the sheet outline, each end extended SNAP px, polygonized (as street_map.py does at 1.5 px);
          faces >= 400 px2 are blocks (street_map.py's rule). closed = Ben blocks with a face of IoU >= 0.8.
          intact rings = exported outline polygons whose every side survives step 4 and whose sides join end to end.
 workload a shown line less than half on Ben's lines is one he deletes; a line of his less than half found is one he
          draws (estimates: moving and trimming are not counted).
 folds    A ('north-west grid + east'): (x < 2950 and y < 3560) or x >= 5400; B: the rest. x = 2950 runs along the
          street between his blocks 8/34 and 18/28, y = 3560 along Blue Rock St, x = 5400 along Mad Anthony St.
          A holds 28 of his blocks (49% of block area, 57% of the paper), B 27. Blocks and predicted blocks go by
          centroid, line samples by their own position, whole lines (workload) by midpoint.
 stages   the loss step by step: area map alone (P > 0.5 components) -> watershed regions -> straightened outlines
          -> step 4 (N_edges.json) -> what the editor shows. Region stages are scored on their boundaries (half-size
          raster, so they sit 2-5 px off a line's centre: compare them at 8 px, stages.*.lines.*.tol_sensitivity).
          Stages 3 and 4 make blocks by closing their lines into faces (snap 10 px).

JSON (bench44.json and stdout). Every score is given for 'all' and for the folds 'A' and 'B':
  meta        inputs with sha256[:16], tol, timings (outline_step_seconds, total_seconds), definitions
  headline    {all, A, B}: PQ SQ RQ matched merges gt_split fp PQ_decided fp_decided recall_interior precision
              precision_green precision_orange ben_blocks_closed intact_rings delete_len draw_len
  blocks      outlines / outlines_decided -> {all, A, B}: PQ SQ RQ gt pred matched fp fn merges gt_lost_in_merges
              gt_split gt_missed_other
  lines_shown {all, A, B}: recall_interior recall_printed recall_drawn recall_sheet_edge precision precision_green
              precision_orange (+ *_len in px) recall_interior_decided precision_decided tol_sensitivity{3,4,6,8px}
  sheet       {all, A, B}: Ben's sheet_edge recall by the editor's sheet outline and by the network lines; share of the
              sheet outline that is a street side (sheet_outline_precision)
  closure     faces.<stage>_snap{1.5,10,40}: faces, closure{all,A,B}.ben_blocks_closed_iou80/50, blocks_from_faces(_decided);
              'whatif_all_outline_sides_kept' = the same if step 4 dropped nothing. outline_rings{all,A,B}: outlines,
              all_sides_kept_by_step4, sides_join_end_to_end, intact
  on_print    the batch's own share_on_printed_line_by_length beside the true precision of what is shown
  workload    {all, A, B}: delete_n/len (shown lines < 50% on Ben's), draw_n/len (his interior lines < 50% found),
              shown_len_off_ben, ben_interior_len_missed, sheet_outline_delete_n/len
  stages      <stage>: blocks, blocks_decided, lines

TIME (CPU, 21 Nov 2026): the outline step 11-25 s; scoring 15-25 s; one run 30-60 s in all (system python is faster
than the venv); --grids, 6 grids 3 at a time, about 4 minutes. Memory: a few GB a run at most.
"""
import argparse, concurrent.futures as cf, hashlib, importlib.util, json, os, shlex, subprocess, sys, time
import numpy as np
import cv2
from scipy.spatial import cKDTree
from shapely.geometry import LineString
from shapely.ops import unary_union, polygonize
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'; sys.path.insert(0, HERE); sys.path.insert(0, HERE + '..')
import _ws  # noqa: E402
import edit_server as ES  # noqa: E402   (the line editor's clean() and sheet())
import blocks_noguide as BN  # noqa: E402   (step 4)

SP = _ws.DATA; U = SP + 'unet_data/'; RUNS = SP + 'bench44_runs/'
VPY = HERE + '.venv/Scripts/python.exe'
N = '44'; W, H = 10768, 7219; S = 0.5; h2, w2 = int(H * S), int(W * S)
WMAX = 260.0                     # widest street counted as decided ground (full px)
FX, FY, FX2 = 2950, 3560, 5400   # folds
MIN_FACE = 400.0                 # street_map.py
STATE_OF = {'on print': 'green'}


def log(*a): print(*a, file=sys.stderr, flush=True)
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16] if os.path.exists(p) else None
def is_a(x, y): return ((np.asarray(x) < FX) & (np.asarray(y) < FY)) | (np.asarray(x) >= FX2)


# ------------------------------------------------------------------ truth
def load_truth():
    sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
    assert sm['size'] == [W, H] and len(sm['blocks']) == 55
    rings = [np.array(b['ring'], float) for b in sm['blocks']]
    lines = [(np.array(l['a'], float), np.array(l['b'], float), l['kind']) for l in sm['lines']]
    gt = raster(rings)
    cen = np.array([poly_centroid(r) for r in rings])
    alpha2 = cv2.resize(np.load(SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (w2, h2)) > 0.5
    return dict(rings=rings, lines=lines, gt=gt, ng=len(rings), cen=cen, isA=is_a(cen[:, 0], cen[:, 1]), alpha2=alpha2, decided=decided_ground(gt, len(rings), alpha2))


def poly_centroid(r):
    x, y = r[:, 0], r[:, 1]; c = x * np.roll(y, -1) - np.roll(x, -1) * y; a = c.sum() / 2
    return np.array([((x + np.roll(x, -1)) * c).sum() / (6 * a), ((y + np.roll(y, -1)) * c).sum() / (6 * a)])


def raster(rings, order=None):
    inst = np.zeros((h2, w2), np.int32)
    for k in (order if order is not None else range(len(rings))):
        r = (np.asarray(rings[k]) * S).round().astype(np.int32)
        if len(r) >= 3: cv2.fillPoly(inst, [r], int(k) + 1)
    return inst


def decided_ground(gt, ng, alpha2):
    """Ben's blocks + the street ground between them (half size, cached)"""
    f = RUNS + 'cache/decided_half.png'
    if os.path.exists(f): return cv2.imread(f, 0) > 0
    wm = WMAX * S; d1 = np.full((h2, w2), np.inf, np.float32); l1 = np.zeros((h2, w2), np.int32); d2 = np.full((h2, w2), np.inf, np.float32)
    off = cv2.distanceTransform(np.pad(alpha2.astype(np.uint8), 1), cv2.DIST_L2, 5)[1:-1, 1:-1]   # distance to the paper's edge (label -1)
    obst = [(-1, None)] + [(i, None) for i in range(1, ng + 1)]
    for i, _ in obst:
        if i == -1: y0, y1, x0, x1 = 0, h2, 0, w2; d = off
        else:
            ys, xs = np.nonzero(gt == i); m = int(wm) + 2
            y0, y1, x0, x1 = max(0, ys.min() - m), min(h2, ys.max() + m + 1), max(0, xs.min() - m), min(w2, xs.max() + m + 1)
            d = cv2.distanceTransform((gt[y0:y1, x0:x1] != i).astype(np.uint8), cv2.DIST_L2, 5)
        D1, L1, D2 = d1[y0:y1, x0:x1], l1[y0:y1, x0:x1], d2[y0:y1, x0:x1]
        better = d < D1
        D2[:] = np.where(better, D1, np.minimum(D2, d)); L1[:] = np.where(better, i, L1); D1[:] = np.where(better, d, D1)
    dec = (gt > 0) | (alpha2 & (d1 + d2 <= wm))
    dec &= alpha2 | (gt > 0)
    os.makedirs(RUNS + 'cache', exist_ok=True); cv2.imwrite(f, dec.astype(np.uint8) * 255)
    return dec


# ------------------------------------------------------------------ the editor's own clean() and sheet(), the real step 4
def sheet(n=N): return ES.sheet(n, W, H)
def clean(edges): return ES.clean(edges)


# ------------------------------------------------------------------ blocks
def pq(T, pr, npr, decided=None):
    """COCO panoptic quality of instance raster pr (1..npr) against Ben's blocks; per fold too. With decided (half-size
    mask of the ground Ben decided), everything else is void (COCO's rule)"""
    gt, ng = T['gt'], T['ng']; void = None if decided is None else ~decided
    g = gt.astype(np.int64)
    if void is not None: g = np.where((g == 0) & void, ng + 1, g)
    G = ng + 2; m = (g > 0) | (pr > 0)
    joint = np.bincount(g[m] * (npr + 1) + pr[m], minlength=G * (npr + 1)).reshape(G, npr + 1)
    ga = joint.sum(1); pa = joint.sum(0); vj = joint[ng + 1] if void is not None else np.zeros(npr + 1)
    # predicted centroids
    ys, xs = np.nonzero(pr); lab = pr[ys, xs]; cnt = np.bincount(lab, minlength=npr + 1)
    cx = np.bincount(lab, xs, minlength=npr + 1) / np.maximum(cnt, 1) / S; cy = np.bincount(lab, ys, minlength=npr + 1) / np.maximum(cnt, 1) / S
    pA = is_a(cx, cy)
    tp_iou = {}; best = np.zeros(ng + 1, int)
    for i in range(1, ng + 1):
        if npr == 0: continue
        j = int(np.argmax(joint[i, 1:])) + 1; best[i] = j; inter = joint[i, j]
        iou = inter / max(1, ga[i] + pa[j] - inter - vj[j])
        if iou > 0.5: tp_iou[i] = (j, float(iou))
    matched_p = {j for j, _ in tp_iou.values()}
    covers = (joint[1:ng + 1, 1:] >= 0.5 * ga[1:ng + 1, None])          # [gt, pred]: pred holds >= half of the gt block
    merge_p = np.nonzero(covers.sum(0) >= 2)[0] + 1
    fp_p = [j for j in range(1, npr + 1) if j not in matched_p and cnt[j] > 0 and not (void is not None and vj[j] > 0.5 * pa[j])]
    res = {}
    for f, gsel, psel in (('all', np.ones(ng, bool), np.ones(npr + 1, bool)), ('A', T['isA'], pA), ('B', ~T['isA'], ~pA)):
        gi = [i for i in range(1, ng + 1) if gsel[i - 1]]
        tps = [tp_iou[i][1] for i in gi if i in tp_iou]; tp = len(tps); fn = len(gi) - tp
        fp = sum(1 for j in fp_p if psel[j]); mg = int(sum(1 for j in merge_p if psel[j]))
        lost_m = sum(1 for i in gi if i not in tp_iou and best[i] and best[i] in set(merge_p.tolist()) and covers[i - 1, best[i] - 1])
        split = sum(1 for i in gi if i not in tp_iou and not (best[i] and best[i] in set(merge_p.tolist()) and covers[i - 1, best[i] - 1]) and (joint[i, 1:] >= 0.2 * ga[i]).sum() >= 2)
        sq = float(np.mean(tps)) if tps else 0.0; rq = tp / max(1e-9, tp + 0.5 * fp + 0.5 * fn)
        res[f] = dict(PQ=round(sq * rq, 4), SQ=round(sq, 4), RQ=round(rq, 4), gt=len(gi), pred=int(sum(1 for j in range(1, npr + 1) if cnt[j] > 0 and psel[j])), matched=tp, fp=fp, fn=fn,
                      merges=mg, gt_lost_in_merges=int(lost_m), gt_split=int(split), gt_missed_other=int(fn - lost_m - split))
    ious = np.zeros(ng)
    for i in range(1, ng + 1):
        j = best[i]
        if j: ious[i - 1] = joint[i, j] / max(1, ga[i] + pa[j] - joint[i, j] - vj[j])
    return res, ious


def cc_inst(mask, min_px=0, conn=4):
    n, cc, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=conn)
    keep = np.nonzero(st[:, cv2.CC_STAT_AREA] >= min_px)[0]; keep = keep[keep > 0]
    remap = np.zeros(n, np.int32); remap[keep] = np.arange(1, len(keep) + 1)
    return remap[cc], len(keep)


def faces(segs, snap):
    ext = []
    for a, b in segs:
        a = np.asarray(a, float); b = np.asarray(b, float); L = np.hypot(*(b - a))
        if L < 0.05: continue
        d = (b - a) / L; ext.append(LineString([a - d * snap, b + d * snap]))
    P = [p for p in polygonize(unary_union(ext)) if p.area >= MIN_FACE] if ext else []
    P.sort(key=lambda p: -p.area)                 # big first, so faces inside a face's hole paint over it
    return [np.array(p.exterior.coords)[:-1] for p in P]


# ------------------------------------------------------------------ lines
def sample(segs, step=1.0):
    pts, dirs, idx = [], [], []
    for k, (a, b) in enumerate(segs):
        a = np.asarray(a, float); b = np.asarray(b, float); L = np.hypot(*(b - a))
        if L < 1e-6: continue
        m = max(1, int(np.ceil(L / step))); t = (np.arange(m) + 0.5) / m
        pts.append(a + np.outer(t, b - a)); dirs.append(np.repeat(((b - a) / L)[None], m, 0)); idx.append(np.full(m, k))
    if not pts: return np.zeros((0, 2)), np.zeros((0, 2)), np.zeros(0, int)
    return np.vstack(pts), np.vstack(dirs), np.concatenate(idx)


def near(P, Pd, Q, Qd, ang, rmax=8.0, k=48, chunk=40000):
    """distance from each sample of P to the nearest sample of Q whose direction is within ang degrees (inf if > rmax)"""
    out = np.full(len(P), np.inf)
    if len(P) == 0 or len(Q) == 0: return out
    tr = cKDTree(Q); c = np.cos(np.radians(ang)); kk = min(k, len(Q))
    for s in range(0, len(P), chunk):
        d, j = tr.query(P[s:s + chunk], k=kk, distance_upper_bound=rmax)
        if kk == 1: d, j = d[:, None], j[:, None]
        ok = np.isfinite(d); jj = np.where(ok, j, 0)
        ok &= np.abs((Qd[jj] * Pd[s:s + chunk, None, :]).sum(2)) >= c
        out[s:s + chunk] = np.where(ok, d, np.inf).min(1)
    return out


class LineSet:
    def __init__(self, items, ang, pts=None):
        """items: list of (a, b, label); or pts = (P, Pd, label) for raster boundaries"""
        if pts is None:
            self.items = items; self.P, self.Pd, self.ix = sample([(a, b) for a, b, _ in items])
            self.lab = np.array([items[i][2] for i in self.ix]) if len(self.ix) else np.zeros(0, str)
        else:
            self.items = []; self.P, self.Pd = pts[0], pts[1]; self.ix = np.zeros(len(self.P), int); self.lab = np.full(len(self.P), pts[2])
        self.A = is_a(self.P[:, 0], self.P[:, 1]) if len(self.P) else np.zeros(0, bool); self.ang = ang

    def dist_to(self, other):
        return near(self.P, self.Pd, other.P, other.Pd, self.ang)


def boundary_lines(inst, ang):
    """the boundary of every instance of a half-size raster as full-size samples about 1 px apart; the direction of each is
    taken over +-5 contour points (10 px), so the pixel staircase does not fail the direction test"""
    P, D = [], []
    n = int(inst.max()); ys, xs = np.nonzero(inst); lab = inst[ys, xs]
    if n == 0: return LineSet([], ang, pts=(np.zeros((0, 2)), np.zeros((0, 2)), 'boundary'))
    x0 = np.full(n + 1, 1 << 30); x1 = np.zeros(n + 1, int); y0 = np.full(n + 1, 1 << 30); y1 = np.zeros(n + 1, int)
    np.minimum.at(x0, lab, xs); np.maximum.at(x1, lab, xs); np.minimum.at(y0, lab, ys); np.maximum.at(y1, lab, ys)
    for i in range(1, n + 1):
        if x1[i] < x0[i]: continue
        sub = np.pad((inst[y0[i]:y1[i] + 1, x0[i]:x1[i] + 1] == i).astype(np.uint8), 1)
        for c in cv2.findContours(sub, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)[0]:
            p = (c[:, 0, :].astype(float) + [x0[i] - 1, y0[i] - 1]) * 2 + 0.5
            if len(p) < 12: continue
            d = np.roll(p, -5, 0) - np.roll(p, 5, 0); L = np.hypot(*d.T); ok = L > 0; d = d[ok] / L[ok, None]; p = p[ok]
            P += [p, (p + np.roll(p, -1, 0)) / 2]; D += [d, d]
    return LineSet([], ang, pts=(np.vstack(P), np.vstack(D), 'boundary'))



def in_mask(P, mask2, grow=5):
    m = cv2.dilate(mask2.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * grow + 1, 2 * grow + 1))) > 0 if grow else mask2
    x = np.clip((P[:, 0] * S).astype(int), 0, w2 - 1); y = np.clip((P[:, 1] * S).astype(int), 0, h2 - 1)
    return m[y, x]


def share(ok, sel):
    n = int(sel.sum()); return (round(float(ok[sel].mean()), 4) if n else None), n


def line_scores(pred, ben, T, tol, labels_pred=('green', 'orange')):
    """pred: LineSet of network lines (labels = state), ben: LineSet of Ben's lines (labels = kind)"""
    dp = pred.dist_to(ben); db = ben.dist_to(pred)
    interior = np.isin(ben.lab, ('printed', 'drawn'))
    decb = in_mask(ben.P, T['decided']) if len(ben.P) else np.zeros(0, bool); decp = in_mask(pred.P, T['decided']) if len(pred.P) else np.zeros(0, bool)
    out = {}
    for f, fb, fp in (('all', np.ones(len(ben.P), bool), np.ones(len(pred.P), bool)), ('A', ben.A, pred.A), ('B', ~ben.A, ~pred.A)):
        r = {}
        rec, n = share(db <= tol, fb & interior); r['recall_interior'] = rec; r['ben_interior_len'] = n
        for k in ('printed', 'drawn', 'sheet_edge'): r[f'recall_{k}'] = share(db <= tol, fb & (ben.lab == k))[0]
        pre, n = share(dp <= tol, fp); r['precision'] = pre; r['shown_len'] = n
        for s in labels_pred:
            p_, n_ = share(dp <= tol, fp & (pred.lab == s)); r[f'precision_{s}'] = p_; r[f'{s}_len'] = n_
        r['recall_interior_decided'] = share(db <= tol, fb & interior & decb)[0]; r['precision_decided'] = share(dp <= tol, fp & decp)[0]
        r['tol_sensitivity'] = {f'{t:g}px': dict(recall_interior=share(db <= t, fb & interior)[0], precision=share(dp <= t, fp)[0]) for t in (3, 4, 6, 8)}
        out[f] = r
    return out, dp, db


def per_line(ls, dist, tol):
    """matched share of each line of a LineSet"""
    if not len(ls.ix): return np.zeros(len(ls.items))
    tot = np.bincount(ls.ix, minlength=len(ls.items)); ok = np.bincount(ls.ix, (dist <= tol).astype(float), minlength=len(ls.items))
    return ok / np.maximum(tot, 1)


# ------------------------------------------------------------------ the run
def run_outline_step(a):
    os.makedirs(a.run, exist_ok=True)
    if a.reuse and os.path.exists(a.run + 'outlines.json') and os.path.exists(a.run + 'outline_step.json'):
        log('reusing', a.run + 'outlines.json'); return json.load(open(a.run + 'outline_step.json'))
    t0 = time.time()
    if a.outlines == HERE + 'outlines.py':   # the real outline step: every output into the run folder (--out), nothing into the repo
        cmd = [a.python, a.outlines, N, 'area_ng1', 'lines_ng1', '--area-png', a.area, '--lines-png', a.lines, '--out', a.run] + shlex.split(a.outline_args)
    else: cmd = [a.python, a.outlines, N, a.area, a.lines, a.run]
    r = subprocess.run(cmd, cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace')
    if r.returncode: sys.exit('outline step failed:\n' + r.stdout[-2000:] + r.stderr[-4000:])
    rep = json.loads(r.stdout.strip().splitlines()[-1]); info = dict(rep=rep, seconds=round(time.time() - t0, 1), cmd=cmd[1:])
    json.dump(info, open(a.run + 'outline_step.json', 'w'), indent=1); return info


def grids(a):
    """--grids DIR: the bench on every grid's maps, then the mean and sd of every headline score (and paired gains)"""
    G = sorted(g for g in os.listdir(a.grids) if os.path.exists(os.path.join(a.grids, g, '44_area.png')) and os.path.exists(os.path.join(a.grids, g, '44_lines.png')))
    tag = a.tag or 'merged'; skip = {'--grids', '--tag', '--jobs', '--paired', '--area', '--lines'}; rest = []; k = 1
    while k < len(sys.argv):
        if sys.argv[k] in skip: k += 2; continue
        rest.append(sys.argv[k]); k += 1
    def one(g):
        out = a.runs + f'{tag}__{g}/bench44.json'
        if not (a.reuse and os.path.exists(out)):
            cmd = [sys.executable, os.path.abspath(__file__), '--area', os.path.join(a.grids, g, '44_area.png'), '--lines', os.path.join(a.grids, g, '44_lines.png'), '--tag', f'{tag}__{g}', '--no-pic'] + rest
            r = subprocess.run(cmd, cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace')
            if r.returncode: return g, dict(error=(r.stdout + r.stderr)[-2000:])
        return g, json.load(open(out, encoding='utf8'))['headline']
    with cf.ThreadPoolExecutor(a.jobs) as ex: R = dict(ex.map(one, G))
    bad = {g: r['error'] for g, r in R.items() if 'error' in r}
    if bad: sys.exit('grid runs failed: ' + json.dumps(bad)[:3000])
    stat = lambda v: dict(mean=round(float(np.mean(v)), 4), sd=round(float(np.std(v, ddof=1)), 4) if len(v) > 1 else None, min=round(float(np.min(v)), 4), max=round(float(np.max(v)), 4))
    res = dict(meta=dict(tag=tag, grids=G, grids_dir=a.grids, runs=[a.runs + f'{tag}__{g}/' for g in G]),
               headline={f: {k: stat([R[g][f][k] for g in G]) for k in R[G[0]][f] if all(R[g][f][k] is not None for g in G)} for f in ('all', 'A', 'B')}, per_grid=R)
    if a.paired:   # paired gains: this chain minus the other one on the same grid
        P = {g: json.load(open(os.path.join(a.paired.replace('{grid}', g)), encoding='utf8'))['headline'] for g in G}
        res['paired'] = {f: {k: dict(**stat([R[g][f][k] - P[g][f][k] for g in G]), gains=int(sum(R[g][f][k] > P[g][f][k] for g in G)), of=len(G)) for k in R[G[0]][f]
                             if all(R[g][f][k] is not None and P[g][f].get(k) is not None for g in G)} for f in ('all', 'A', 'B')}
        res['meta']['paired_with'] = a.paired
    json.dump(res, open(a.runs + f'{tag}_grids.json', 'w', encoding='utf8', newline='\n'), indent=1); print(json.dumps(res['headline']['all'], indent=1))


def main():
    global RUNS
    ap = argparse.ArgumentParser()
    ap.add_argument('--area', default=U + '44_pred_area_ng1.png'); ap.add_argument('--lines', default=U + '44_lines_lines_ng1.png')
    ap.add_argument('--outlines', default=HERE + 'outlines.py'); ap.add_argument('--python', default=VPY); ap.add_argument('--outline-args', default='')
    ap.add_argument('--step4', default=None); ap.add_argument('--keep-unlined', action='store_true'); ap.add_argument('--rail-show', action='store_true')
    ap.add_argument('--tag', default=None); ap.add_argument('--reuse', action='store_true'); ap.add_argument('--runs', default=RUNS)
    ap.add_argument('--faith', action='store_true'); ap.add_argument('--tol', type=float, default=5.0); ap.add_argument('--ang', type=float, default=20.0)
    ap.add_argument('--no-pic', action='store_true'); ap.add_argument('--grids', default=None); ap.add_argument('--jobs', type=int, default=3); ap.add_argument('--paired', default=None)
    a = ap.parse_args()
    RUNS = a.runs = os.path.abspath(a.runs).replace('\\', '/') + '/'; os.makedirs(RUNS, exist_ok=True)
    if a.grids: return grids(a)
    a.area, a.lines, a.outlines = [os.path.abspath(p).replace('\\', '/') for p in (a.area, a.lines, a.outlines)]
    if a.faith:
        a.area, a.lines, a.tag = U + '44_pred_edge_v1.png', U + '44_lines_lines_v2.png', a.tag or '_faith'
    tag = a.tag or (os.path.basename(a.area)[:-4].replace('44_pred_', '') + '+' + os.path.basename(a.lines)[:-4].replace('44_lines_', '') + ('' if a.outlines == HERE + 'outlines.py' else '+' + os.path.basename(a.outlines)[:-3]))
    a.run = RUNS + f'{tag}/'
    T0 = time.time(); info = run_outline_step(a)
    if a.faith:
        ref = SP + 'picks22_guided/22-44/outlines.json'; same = open(a.run + 'outlines.json', 'rb').read() == open(ref, 'rb').read()
        bm_same = bool((cv2.imread(a.run + '44_blockmask.png', 0) == cv2.imread(U + '44_blockmask.png', 0)).all())
        out = dict(faithful=same, outlines_sha256=sha(a.run + 'outlines.json'), stored_sha256=sha(ref), blockmask_identical=bm_same, python=a.python, outline_step_seconds=info['seconds'])
        print(json.dumps(out, indent=1)); sys.exit(0 if same else 1)
    log('scoring', tag)
    T = load_truth(); polys = json.load(open(a.run + 'outlines.json', encoding='utf8'))
    if a.step4:
        spec = importlib.util.spec_from_file_location('step4mod', a.step4); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); edges = mod.step4(polys)
    else: edges = BN.step4(polys, keep_unlined=True if a.keep_unlined else None, rail_drop=False if a.rail_show else None)
    json.dump(edges, open(a.run + '44_edges.json', 'w', encoding='utf8', newline='\n'))
    SH = sheet(); shown = clean(edges); json.dump(shown + SH, open(a.run + '44_shown.json', 'w', encoding='utf8', newline='\n'))
    ben = LineSet(T['lines'], a.ang)
    stages, lines_st = {}, {}
    # stage 0: the area map alone
    pa = cv2.imread(a.area, 0)
    if pa.shape != (h2, w2): pa = cv2.resize(pa, (w2, h2), interpolation=cv2.INTER_LINEAR)
    b0 = cv2.morphologyEx(((pa > 127) & T['alpha2']).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)); i0, n0 = cc_inst(b0, 1500)
    # stage 1: watershed regions
    if os.path.exists(a.run + '44_blockinst.png'):
        i1 = cv2.imread(a.run + '44_blockinst.png', cv2.IMREAD_UNCHANGED).astype(np.int32)
        if i1.shape != (h2, w2): i1 = cv2.resize(i1, (w2, h2), interpolation=cv2.INTER_NEAREST)
        u = np.unique(i1); u = u[u > 0]; remap = np.zeros(int(i1.max()) + 1, np.int32); remap[u] = np.arange(1, len(u) + 1); i1, n1 = remap[i1], len(u)
    elif os.path.exists(a.run + '44_blockmask.png'):
        bm = cv2.imread(a.run + '44_blockmask.png', 0)
        if bm.shape != (h2, w2): bm = cv2.resize(bm, (w2, h2), interpolation=cv2.INTER_NEAREST)
        i1, n1 = cc_inst(bm > 127, conn=8)          # outlines.py traces 8-connected outer contours
    else: i1, n1 = None, 0
    # stage 2: straightened outlines
    rings = [np.array([s['a'] for s in p], float) for p in polys]; i2 = raster(rings); n2 = len(rings)
    # stages 3, 4: lines closed into faces (with the sheet's outline, as the editor shows it)
    shs = [(s['a'], s['b']) for s in SH]
    bound_lines = lambda inst: boundary_lines(inst, a.ang)
    for name, inst, n in (('0_area_map_alone', i0, n0), ('1_watershed_regions', i1, n1), ('2_straightened_outlines', i2, n2)):
        if inst is None: continue
        r, _ = pq(T, inst, n); rd, _ = pq(T, inst, n, T['decided']); stages[name] = dict(blocks=r, blocks_decided=rd)
    st_lines = {'0_area_map_alone': bound_lines(i0), '2_straightened_outlines': LineSet([(s['a'], s['b'], 'side') for p in polys for s in p], a.ang),
                '3_step4_edges': LineSet([(e['a'], e['b'], e['state']) for e in edges], a.ang), '4_editor_shows': LineSet([(e['a'], e['b'], e['state']) for e in shown], a.ang)}
    if i1 is not None: st_lines['1_watershed_regions'] = bound_lines(i1)
    keep = {}
    for name in sorted(st_lines):
        ls = st_lines[name]; sc, dp, db = line_scores(ls, ben, T, a.tol, labels_pred=('green', 'orange') if name[0] in '34' else ())
        stages.setdefault(name, {})['lines'] = {f: {k: v for k, v in sc[f].items() if k in ('recall_interior', 'recall_printed', 'recall_drawn', 'precision', 'shown_len', 'precision_green', 'precision_orange', 'tol_sensitivity')} for f in sc}
        keep[name] = (sc, dp, db)
    clos = {}
    for name, segs in (('3_step4_edges', [(e['a'], e['b']) for e in edges] + shs), ('4_editor_shows', [(e['a'], e['b']) for e in shown] + shs),
                       ('whatif_all_outline_sides_kept', [(s_['a'], s_['b']) for p in polys for s_ in p] + shs)):
        for snap in (1.5, 10.0, 40.0):
            F = faces(segs, snap); fi = raster(F); r, ious = pq(T, fi, len(F)); rd, _ = pq(T, fi, len(F), T['decided'])
            c = {f: dict(ben_blocks_closed_iou80=int(((ious >= 0.8) & sel).sum()), ben_blocks_closed_iou50=int(((ious > 0.5) & sel).sum()), ben_blocks=int(sel.sum()))
                 for f, sel in (('all', np.ones(T['ng'], bool)), ('A', T['isA']), ('B', ~T['isA']))}
            clos[f'{name}_snap{snap:g}'] = dict(faces=len(F), closure=c, blocks_from_faces=r, blocks_from_faces_decided=rd)
            if snap == 10.0 and name in stages: stages[name]['blocks'] = r; stages[name]['blocks_decided'] = rd; stages[name]['blocks_note'] = 'faces of the lines + sheet outline, snap 10 px'
    # intact rings
    def ring_state(p):
        kept = all(s['state'] != 'short' and not s.get('paper_edge') for s in p)
        joined = all(np.hypot(*(np.array(p[k]['b']) - np.array(p[(k + 1) % len(p)]['a']))) <= 1.5 for k in range(len(p)))
        return kept, joined
    def area2(r): return abs((r[:, 0] * np.roll(r[:, 1], -1) - np.roll(r[:, 0], -1) * r[:, 1]).sum())
    rs = [ring_state(p) for p in polys]; rc = np.array([poly_centroid(r) if len(r) >= 3 and area2(r) > 1 else r.mean(0) for r in rings]) if rings else np.zeros((0, 2))
    rA = is_a(rc[:, 0], rc[:, 1]) if len(rc) else np.zeros(0, bool)
    rings_out = {f: dict(outlines=int(sel.sum()), all_sides_kept_by_step4=int(sum(k for (k, j), s in zip(rs, sel) if s)), sides_join_end_to_end=int(sum(j for (k, j), s in zip(rs, sel) if s)),
                         intact=int(sum(k and j for (k, j), s in zip(rs, sel) if s))) for f, sel in (('all', np.ones(len(rs), bool)), ('A', rA), ('B', ~rA))}
    # main line scores: what the editor shows
    sc4, dp4, db4 = keep['4_editor_shows']; shown_ls = st_lines['4_editor_shows']
    # sheet outline, separately
    sh_ls = LineSet([(s['a'], s['b'], 'sheet') for s in SH], a.ang); ben_sh = LineSet([l for l in T['lines'] if l[2] == 'sheet_edge'], a.ang)
    d_sh = sh_ls.dist_to(ben); d_bsh = ben_sh.dist_to(sh_ls); d_bsh_net = ben_sh.dist_to(shown_ls)
    sheet_out = {f: dict(ben_sheet_edge_len=share(d_bsh <= a.tol, fb)[1], ben_sheet_edge_recall_by_sheet_outline=share(d_bsh <= a.tol, fb)[0], ben_sheet_edge_recall_by_network_lines=share(d_bsh_net <= a.tol, fb)[0],
                         sheet_outline_len=share(d_sh <= a.tol, fs)[1], sheet_outline_precision=share(d_sh <= a.tol, fs)[0])
                 for f, fb, fs in (('all', np.ones(len(ben_sh.P), bool), np.ones(len(sh_ls.P), bool)), ('A', ben_sh.A, sh_ls.A), ('B', ~ben_sh.A, ~sh_ls.A))}
    # workload
    pl_sh = per_line(shown_ls, dp4, a.tol); pl_ben = per_line(ben, db4, a.tol); pl_sheet = per_line(sh_ls, d_sh, a.tol)
    mid = lambda items: np.array([(np.asarray(x[0]) + np.asarray(x[1])) / 2 for x in items]) if items else np.zeros((0, 2))
    msh, mben, msheet = mid(shown_ls.items), mid(ben.items), mid(sh_ls.items)
    Lsh = np.array([np.hypot(*(np.asarray(b) - np.asarray(a_))) for a_, b, _ in shown_ls.items]); Lben = np.array([np.hypot(*(b - a_)) for a_, b, _ in ben.items]); Lsheet = np.array([np.hypot(*(np.asarray(b) - np.asarray(a_))) for a_, b, _ in sh_ls.items])
    interior = np.array([k in ('printed', 'drawn') for _, _, k in ben.items])
    work = {}
    for f in ('all', 'A', 'B'):
        sel = lambda m: np.ones(len(m), bool) if f == 'all' else (is_a(m[:, 0], m[:, 1]) if f == 'A' else ~is_a(m[:, 0], m[:, 1]))
        ds, dbn, dst = sel(msh) & (pl_sh < 0.5), sel(mben) & interior & (pl_ben < 0.5), sel(msheet) & (pl_sheet < 0.5)
        work[f] = dict(shown_lines=int(sel(msh).sum()), delete_n=int(ds.sum()), delete_len=round(float(Lsh[ds].sum())), shown_len_off_ben=int((dp4[shown_ls.A == (f == 'A')] > a.tol).sum()) if f != 'all' else int((dp4 > a.tol).sum()),
                       ben_interior_lines=int((sel(mben) & interior).sum()), draw_n=int(dbn.sum()), draw_len=round(float(Lben[dbn].sum())),
                       ben_interior_len_missed=int(((db4 > a.tol) & np.isin(ben.lab, ('printed', 'drawn')) & (ben.A == (f == 'A'))).sum()) if f != 'all' else int(((db4 > a.tol) & np.isin(ben.lab, ('printed', 'drawn'))).sum()),
                       sheet_outline_delete_n=int(dst.sum()), sheet_outline_delete_len=round(float(Lsheet[dst].sum())))
    # the batch's own share against the truth
    rep = info['rep']; gl = shown_ls.lab == 'green'
    onprint = dict(batch_share_on_printed_line_by_length=rep.get('share_on_printed_line_by_length'), batch_share_on_detected_line_by_length=rep.get('share_on_detected_line_by_length'),
                   shown_green_share_by_length=round(float(gl.mean()), 4) if len(gl) else None,
                   shown_on_ben_lines_by_length=sc4['all']['precision'], green_on_ben_lines_by_length=sc4['all']['precision_green'])
    headline = {}
    for f in ('all', 'A', 'B'):
        b = stages['2_straightened_outlines']['blocks'][f]; bd = stages['2_straightened_outlines']['blocks_decided'][f]; l = sc4[f]; c = clos['4_editor_shows_snap10']['closure'][f]
        headline[f] = dict(PQ=b['PQ'], SQ=b['SQ'], RQ=b['RQ'], matched=b['matched'], merges=b['merges'], gt_split=b['gt_split'], fp=b['fp'], PQ_decided=bd['PQ'], fp_decided=bd['fp'],
                           recall_interior=l['recall_interior'], precision=l['precision'], precision_green=l['precision_green'], precision_orange=l['precision_orange'],
                           ben_blocks_closed=c['ben_blocks_closed_iou80'], intact_rings=rings_out[f]['intact'], delete_len=work[f]['delete_len'], draw_len=work[f]['draw_len'])
    res = dict(meta=dict(tag=tag, run_dir=a.run, area=a.area, area_sha=sha(a.area), lines=a.lines, lines_sha=sha(a.lines), outlines_py=a.outlines, outlines_py_sha=sha(a.outlines), outline_args=a.outline_args,
                         outline_version=info['rep'].get('version'), step4=a.step4 or f'blocks_noguide.step4 (keep_unlined={a.keep_unlined or BN.KEEP_UNLINED}, rail_drop={BN.RAIL_DROP and not a.rail_show})',
                         python=a.python, tol_px=a.tol, ang_deg=a.ang, outline_step_seconds=info['seconds'], total_seconds=None, truth='streetmap/22-44.json (55 blocks, 359 lines)',
                         decided_ground=f'Ben blocks + street ground with d(nearest block) + d(next block or paper edge) <= {WMAX:g} px', folds=f'A: (x < {FX} and y < {FY}) or x >= {FX2}; B: the rest'),
               headline=headline, blocks=dict(outlines=stages['2_straightened_outlines']['blocks'], outlines_decided=stages['2_straightened_outlines']['blocks_decided']),
               lines_shown=sc4, sheet=sheet_out, closure=dict(faces=clos, outline_rings=rings_out), on_print=onprint, workload=work, stages=stages)
    res['meta']['total_seconds'] = round(time.time() - T0, 1)
    json.dump(res, open(a.run + 'bench44.json', 'w', encoding='utf8', newline='\n'), indent=1)
    if not a.no_pic: picture(a.run, shown_ls, dp4, ben, db4, sh_ls, a.tol)
    print(json.dumps(res, indent=1))


def picture(run, shown_ls, dp, ben, db, sh_ls, tol):
    sc = 0.25; im = cv2.imread(SP + 'cufp/22-44.jpg', cv2.IMREAD_REDUCED_COLOR_4); im = (im * 0.55 + 110).astype(np.uint8)
    def draw(ls, d, col_ok, col_bad, th):
        ok = d <= tol
        q = (ls.P * sc).astype(int); q[:, 0] = np.clip(q[:, 0], 0, im.shape[1] - 1); q[:, 1] = np.clip(q[:, 1], 0, im.shape[0] - 1)
        for sel, col in ((ok, col_ok), (~ok, col_bad)):
            if col is None: continue
            for x, y in q[sel]: cv2.circle(im, (int(x), int(y)), th, col, -1)
    draw(ben, db, None, (255, 80, 0), 1)                 # Ben's lines missed: blue
    draw(sh_ls, np.zeros(len(sh_ls.P)), (150, 150, 150), None, 1)
    draw(shown_ls, dp, (0, 160, 0), (0, 0, 230), 1)       # shown on his lines: green; off them: red
    cv2.imwrite(run + '44_bench.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 85])


if __name__ == '__main__':
    main()
