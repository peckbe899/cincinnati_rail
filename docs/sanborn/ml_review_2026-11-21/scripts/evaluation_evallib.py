"""Scoring against Ben's checked street map (read-only on the repo; scratch use only).

Line score: both line sets are sampled every 1 px along their segments. A sample counts as matched when a sample of the
other set lies within TOL px AND the two directions differ by less than ANG degrees (so a line crossing at a right angle
does not count). Recall = matched share of Ben's length; precision = matched share of the predicted length.
"""
import json
import numpy as np
import cv2
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union, polygonize_full

REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
SP = REPO + 'data/sanborn/'
U = SP + 'unet_data/'


def truth(n='44'):
    d = json.load(open(SP + f'streetmap/22-{n}.json', encoding='utf8'))
    return d


def sample(segs, step=1.0):
    pts, dirs, idx = [], [], []
    for k, (a, b) in enumerate(segs):
        a = np.asarray(a, float); b = np.asarray(b, float); L = np.hypot(*(b - a))
        if L < 1e-6: continue
        m = max(1, int(np.ceil(L / step))); t = (np.arange(m) + 0.5) / m
        pts.append(a + np.outer(t, b - a)); d = (b - a) / L; dirs.append(np.repeat(d[None], m, 0)); idx.append(np.full(m, k))
    if not pts: return np.zeros((0, 2)), np.zeros((0, 2)), np.zeros(0, int)
    return np.vstack(pts), np.vstack(dirs), np.concatenate(idx)


def matched(P, Pd, Q, Qd, tol, ang):
    """for each sample of P: is there a sample of Q within tol px whose direction is within ang degrees"""
    if len(P) == 0 or len(Q) == 0: return np.zeros(len(P), bool)
    tr = cKDTree(Q); c = np.cos(np.radians(ang)); out = np.zeros(len(P), bool)
    nb = tr.query_ball_point(P, tol)
    for i, js in enumerate(nb):
        if js and (np.abs(Qd[js] @ Pd[i]) >= c).any(): out[i] = True
    return out


def line_scores(pred, tru, tol=4.0, ang=20.0, step=2.0):
    P, Pd, _ = sample(pred, step); Q, Qd, _ = sample(tru, step)
    rec = matched(Q, Qd, P, Pd, tol, ang); pre = matched(P, Pd, Q, Qd, tol, ang)
    return dict(recall=round(float(rec.mean()) if len(rec) else 0.0, 4), precision=round(float(pre.mean()) if len(pre) else 0.0, 4),
                pred_len=round(len(P) * step), truth_len=round(len(Q) * step))


def map_scores(binmap, tru, W, H, tol=4.0):
    """pixel map (full size bool) against Ben's lines: precision = share of drawn px within tol of a Ben line,
    recall = share of Ben's length within tol of a drawn px (no direction test: a map has none)"""
    t = np.zeros((H, W), np.uint8)
    for a, b in tru: cv2.line(t, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), 1, 1)
    dt = cv2.distanceTransform((t == 0).astype(np.uint8), cv2.DIST_L2, 5)
    dp = cv2.distanceTransform((~binmap).astype(np.uint8), cv2.DIST_L2, 5)
    Q, _, _ = sample(tru, 1.0); qx = np.clip(Q[:, 0].round().astype(int), 0, W - 1); qy = np.clip(Q[:, 1].round().astype(int), 0, H - 1)
    return dict(precision=round(float((dt[binmap] <= tol).mean()), 4), recall=round(float((dp[qy, qx] <= tol).mean()), 4), drawn_px=int(binmap.sum()))


def polys_from_lines(segs, tol=1.5, min_area=400):
    """as street_map.py: every segment extended tol px at both ends, then polygonized"""
    ext = []
    for a, b in segs:
        a = np.asarray(a, float); b = np.asarray(b, float); L = np.hypot(*(b - a))
        if L < 0.05: continue
        d = (b - a) / L; ext.append(LineString([a - d * tol, b + d * tol]))
    P = list(polygonize_full(unary_union(ext))[0].geoms)
    return [p for p in P if p.area >= min_area]


def block_match(pred_polys, ben_polys):
    """for each of Ben's blocks: the best IoU of any predicted polygon; plus one-to-one counts"""
    pred = [p if p.is_valid else p.buffer(0) for p in pred_polys]; ben = [p if p.is_valid else p.buffer(0) for p in ben_polys]
    from shapely.strtree import STRtree
    tree = STRtree(pred) if pred else None; best = []; used_by = {}
    for i, b in enumerate(ben):
        bi, bj = 0.0, None
        if tree is not None:
            for j in tree.query(b):
                p = pred[int(j)]; inter = b.intersection(p).area
                if inter <= 0: continue
                iou = inter / b.union(p).area
                if iou > bi: bi, bj = iou, int(j)
        best.append((bi, bj))
    ious = np.array([x[0] for x in best])
    # split / merge: a Ben block that 2+ predicted polygons each cover >= 20% of; a predicted polygon covering 2+ Ben blocks >= 50% each
    split = 0; merged = 0
    if tree is not None:
        for b in ben:
            k = sum(1 for j in tree.query(b) if b.intersection(pred[int(j)]).area >= 0.2 * b.area)
            split += k >= 2
        btree = STRtree(ben)
        for p in pred:
            k = sum(1 for j in btree.query(p) if ben[int(j)].intersection(p).area >= 0.5 * ben[int(j)].area)
            merged += k >= 2
    return dict(ben_blocks=len(ben), pred_polys=len(pred), iou_gt_0_9=int((ious > 0.9).sum()), iou_gt_0_8=int((ious > 0.8).sum()), iou_gt_0_5=int((ious > 0.5).sum()),
                median_best_iou=round(float(np.median(ious)), 3) if len(ious) else 0.0, ben_blocks_split=int(split), pred_polys_merging_2plus=int(merged)), ious


# ---- copies of edit_server.clean and edit_server.sheet (so nothing in the repo is imported or compiled) ----
def sheet(n, W, H):
    a = np.load(SP + f'cufp/{n}/png_alpha_s4.npy').astype(np.float32); m = (a > 0.5).astype(np.uint8)
    sx, sy = W / m.shape[1], H / m.shape[0]; out = []
    for c in cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]:
        if cv2.contourArea(c) < 500: continue
        p = cv2.approxPolyDP(c, 2.0, True)[:, 0, :].astype(float) * [sx, sy]
        for k in range(len(p)):
            q0, q1 = p[k], p[(k + 1) % len(p)]
            if np.hypot(*(q1 - q0)) >= 40: out.append(dict(src='sheet', state='sheet', a=q0.round(1).tolist(), b=q1.round(1).tolist()))
    return out


def clean(edges, ang=2.5, off=5.0, gap=25.0):
    out = []; cosang = np.cos(np.radians(ang))
    for state in sorted({e['state'] for e in edges}):
        segs = sorted([e for e in edges if e['state'] == state], key=lambda e: -np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1])); tracks = []
        for e in segs:
            a, b = np.array(e['a'], float), np.array(e['b'], float); L = np.hypot(*(b - a))
            if L < 1: continue
            hit = None
            for t in tracks:
                d, p0 = t['d'], t['p']; n = np.array([-d[1], d[0]])
                if abs(((b - a) / L) @ d) < cosang or abs((a - p0) @ n) > off or abs((b - p0) @ n) > off: continue
                lo, hi = sorted(((a - p0) @ d, (b - p0) @ d))
                if any(lo <= i1 + gap and hi >= i0 - gap for i0, i1 in t['iv']): hit = (t, lo, hi); break
            if hit: hit[0]['iv'].append((hit[1], hit[2])); hit[0]['names'].add(e.get('name', '')); hit[0]['src'].add(e['src'])
            else: tracks.append(dict(d=(b - a) / L, p=a, iv=[(0.0, L)], names={e.get('name', '')}, src={e['src']}))
        for t in tracks:
            iv = sorted(t['iv']); runs = [list(iv[0])]
            for i0, i1 in iv[1:]:
                if i0 <= runs[-1][1] + gap: runs[-1][1] = max(runs[-1][1], i1)
                else: runs.append([i0, i1])
            nm = sorted(x for x in t['names'] if x and not x.startswith(('Junction', 'Street between')))
            for i0, i1 in runs:
                if i1 - i0 >= 12: out.append(dict(src='read' if 'read' in t['src'] else sorted(t['src'])[0], state=state, name=nm[0] if nm else '', a=(t['p'] + t['d'] * i0).round(1).tolist(), b=(t['p'] + t['d'] * i1).round(1).tolist()))
    G = [(np.array(o['a']), np.array(o['b'])) for o in out if o['state'] == 'green']; keep = []
    for o in out:
        if o['state'] in ('blue', 'orange', 'grey'):
            m = (np.array(o['a']) + np.array(o['b'])) / 2; dup = False
            for p0, p1 in G:
                d = p1 - p0; L = np.hypot(*d); t_ = ((m - p0) @ d) / L ** 2
                if 0 <= t_ <= 1 and abs((m - p0) @ np.array([-d[1], d[0]])) / L < off + 2 and abs((np.array(o['b']) - np.array(o['a'])) @ d) / (L * np.hypot(*(np.array(o['b']) - np.array(o['a'])))) > cosang: dup = True; break
            if dup: continue
        keep.append(o)
    return keep
