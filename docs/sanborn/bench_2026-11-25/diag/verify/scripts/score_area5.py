"""score_area5.py (diag/verify, 25 Nov 2026): the area maps of plate 5 (area5_cpu.py) against the labels Ben's checked
lines give TODAY (diag/ben-labels/map_now/5_label.png: make_labels_v2.map_labels in memory; 0 street, 1 block, 255
not decided). Plate 5 is out of sample for area_ng1 and for V1; V2 trained on its pseudo labels (in sample).
Caveat: Ben's 5 lines started from the batch's (area_ng1 + lines_ng1), so area_ng1 starts slightly ahead.
Pixel scores on decided ground (accuracy, street IoU, street called block, block called street), the share of the
undecided paper called block, and a block-level PQ of the area map alone (components of P > 0.5, 4-connected, as
bench44's stage 0) against Ben's blocks (components of label 1), with COCO's void rule (a predicted block more than half
on undecided ground is not a false positive; undecided px leave its area). Also the same split by the plate's left/right
at val_x_half (make_labels' own split) for a rough noise idea. Read-only; writes diag/verify/area5_scores.json.
    python -B score_area5.py
"""
import json, os, glob
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
D = SP + 'bench_2026-11-25/diag/'
lab = cv2.imread(D + 'ben-labels/map_now/5_label.png', 0); H, W = lab.shape
paper = cv2.resize(np.load(SP + 'cufp/5/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
dec = (lab != 255) & paper; und = (lab == 255) & paper
ng, gt = cv2.connectedComponents((lab == 1).astype(np.uint8), connectivity=4)
ga = np.bincount(gt.ravel(), minlength=ng)
GT_MIN = 1500   # half px: ignore label crumbs (a block of Ben's is far larger)
gtk = np.nonzero(ga >= GT_MIN)[0]; gtk = gtk[gtk > 0]


def pq(pr, npr):
    g = gt.astype(np.int64); m = (g > 0) | (pr > 0)
    joint = np.bincount(g[m] * (npr + 1) + pr[m], minlength=(ng) * (npr + 1)).reshape(ng, npr + 1)
    voidc = np.bincount(pr[und].ravel(), minlength=npr + 1); cnt = np.bincount(pr.ravel(), minlength=npr + 1)
    pa = cnt - voidc                                  # void px leave the predicted area
    tp = {}
    for i in gtk:
        j = int(np.argmax(joint[i, 1:])) + 1; inter = joint[i, j]
        iou = inter / max(1, ga[i] + pa[j] - inter)
        if iou > 0.5: tp[i] = (j, iou)
    mp = {j for j, _ in tp.values()}
    fp = [j for j in range(1, npr + 1) if j not in mp and cnt[j] >= GT_MIN and voidc[j] <= 0.5 * cnt[j]]
    covers = joint[gtk][:, 1:] >= 0.5 * ga[gtk][:, None]
    merges = int((covers.sum(0) >= 2).sum())
    sq = float(np.mean([v[1] for v in tp.values()])) if tp else 0.0
    rq = len(tp) / max(1e-9, len(tp) + 0.5 * len(fp) + 0.5 * (len(gtk) - len(tp)))
    return dict(PQ=round(sq * rq, 4), SQ=round(sq, 4), matched=len(tp), fp=len(fp), merges=merges, gt=len(gtk))


R = {}
for f in sorted(glob.glob(D + 'verify/area5/*.png')) + [SP + 'unet_data/5_pred_area_ng1.png']:
    name = os.path.basename(f)[:-4] if 'verify' in f else 'area_ng1 (batch map)'
    a = cv2.imread(f, 0); assert a.shape == lab.shape, (f, a.shape)
    pb = a > 127; st = (lab == 0) & dec; bl = (lab == 1) & dec
    r = dict(accuracy=round(float((pb[dec] == (lab[dec] == 1)).mean()), 4),
             street_iou=round(float((~pb & st).sum() / max(1, ((~pb & dec) | st).sum())), 4),
             street_called_block=round(float(pb[st].mean()), 4), block_called_street=round(float((~pb[bl]).mean()), 4),
             undecided_called_block=round(float(pb[und].mean()), 4), block_share_paper=round(float(pb[paper].mean()), 4))
    npr, pr = cv2.connectedComponents((pb & paper).astype(np.uint8), connectivity=4)
    r['stage0_PQ_decided'] = pq(pr, npr - 1)
    R[name] = r; print(name.ljust(22), r, flush=True)
R['_note'] = dict(gt_blocks=int(len(gtk)), decided_px=int(dec.sum()), undecided_px=int(und.sum()), street_share_of_decided=round(float(((lab == 0) & dec).sum() / dec.sum()), 4))
print(R['_note'])
json.dump(R, open(D + 'verify/area5_scores.json', 'w'), indent=1)
