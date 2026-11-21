"""Read-only check: COCO-style panoptic quality (PQ = SQ x RQ, match at IoU > 0.5) of plate 44's block outlines
against Ben's hand-checked street map (streetmap/22-44.json blocks). Works at half size. Writes nothing to the repo."""
import json, sys
import numpy as np, cv2
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
S = 0.5

def gt_instances():
    sm = json.load(open(D + 'streetmap/22-44.json', encoding='utf8'))
    W, H = sm['size']; h, w = int(H * S), int(W * S)
    inst = np.zeros((h, w), np.int32)
    for k, b in enumerate(sm['blocks'], 1):
        r = (np.array(b['ring']) * S).round().astype(np.int32)
        cv2.fillPoly(inst, [r], k)
    return inst, len(sm['blocks']), (h, w)

def pred_from_outlines(path, shape):
    polys = json.load(open(path, encoding='utf8')); inst = np.zeros(shape, np.int32)
    for k, poly in enumerate(polys, 1):
        pts = []
        for s in poly: pts.append(s['a'])
        r = (np.array(pts) * S).round().astype(np.int32)
        if len(r) >= 3: cv2.fillPoly(inst, [r], k)
    return inst, len(polys)

def pred_from_mask(mask):
    n, cc = cv2.connectedComponents((mask > 0).astype(np.uint8), connectivity=4)
    return cc, n - 1

def pq(gt, ng, pr, npr, label=''):
    # IoU between every gt and pred instance via a joint histogram
    m = (gt > 0) | (pr > 0)
    g, p = gt[m].astype(np.int64), pr[m].astype(np.int64)
    joint = np.bincount(g * (npr + 1) + p, minlength=(ng + 1) * (npr + 1)).reshape(ng + 1, npr + 1)
    ga = joint.sum(1); pa = joint.sum(0)
    tp, ious, matched_p = 0, [], set()
    merges = 0; splits = 0; gmiss = []
    for i in range(1, ng + 1):
        j = int(np.argmax(joint[i, 1:])) + 1 if npr else 0
        inter = joint[i, j] if npr else 0
        iou = inter / (ga[i] + pa[j] - inter) if npr else 0
        if iou > 0.5: tp += 1; ious.append(iou); matched_p.add(j)
        else:
            gmiss.append(i)
            # why missed: merged (the pred that covers most of it covers >= 2 gt blocks), or split / shrunk
            if npr and inter > 0.5 * ga[i] and (joint[1:, j] > 0.2 * ga[1:]).sum() >= 2: merges += 1
            elif npr and (joint[i, 1:] > 0.1 * ga[i]).sum() >= 2: splits += 1
    fp = npr - len(matched_p); fn = ng - tp
    sq = float(np.mean(ious)) if ious else 0.0; rq = tp / max(1e-9, tp + 0.5 * fp + 0.5 * fn)
    r = dict(src=label, gt=ng, pred=npr, tp=tp, fp=fp, fn=fn, SQ=round(sq, 3), RQ=round(rq, 3), PQ=round(sq * rq, 3),
             missed_by_merge=merges, missed_by_split=splits, missed_other=fn - merges - splits)
    return r

if __name__ == '__main__':
    gt, ng, shape = gt_instances()
    pr, npr = pred_from_outlines(D + 'picks22_guided/22-44/outlines.json', shape)
    print(json.dumps(pq(gt, ng, pr, npr, 'outlines.json (edge_v1 + lines_v2, straightened)')))
    bm = cv2.imread(D + 'unet_data/44_blockmask.png', 0); bm = cv2.resize(bm, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
    pr2, npr2 = pred_from_mask(bm)
    print(json.dumps(pq(gt, ng, pr2, npr2, '44_blockmask.png (watershed before straightening)')))
    # the area network alone: P(block) > 0.5, connected components
    for nm in ('edge_v1', 'area_ng1'):
        pa = cv2.imread(D + f'unet_data/44_pred_{nm}.png', 0); pa = cv2.resize(pa, (shape[1], shape[0]), interpolation=cv2.INTER_LINEAR)
        al = cv2.resize(np.load(D + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (shape[1], shape[0])) > 0.5
        b = ((pa > 127) & al).astype(np.uint8); b = cv2.morphologyEx(b, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        pr3, npr3 = pred_from_mask(b)
        # drop specks below 1500 px at half size (outlines.py MIN_AREA 6000 at full size)
        areas = np.bincount(pr3.ravel()); keep = np.where(areas >= 1500)[0]; keep = keep[keep > 0]
        remap = np.zeros(npr3 + 1, np.int32); remap[keep] = np.arange(1, len(keep) + 1); pr3 = remap[pr3]
        print(json.dumps(pq(gt, ng, pr3, len(keep), f'{nm} P(block)>0.5 components only')))
