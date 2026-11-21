"""Read-only: how clean is the area network's P(block) (the line net's 7th channel) on its TRAINING plates vs held-out 44.
Half-size labels N_label.png (0 street, 1 block, 255 ignore), preds N_pred_<model>.png (0-255), edges N_edge.png."""
import json, sys
import numpy as np, cv2
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
out = {}
for model in ('area_ng1', 'edge_v1'):
    for plate in ('82A', '80', '43', '45', '44'):
        lab = cv2.imread(D + f'{plate}_label.png', 0); p = cv2.imread(D + f'{plate}_pred_{model}.png', 0)
        if p is None: continue
        pf = p.astype(np.float32) / 255
        m = lab != 255; pr = pf[m] > 0.5; gt = lab[m] == 1
        iou = lambda a, b: float((a & b).sum() / max(1, (a | b).sum()))
        e = cv2.imread(D + f'{plate}_edge.png', 0); et = cv2.dilate(e, np.ones((3, 3), np.uint8)) > 0
        b = cv2.morphologyEx((pf > 0.5).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
        near_b = cv2.dilate(b.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        # false boundary: predicted block/street boundary on labelled ground that is > 4 px (half size) from any label edge
        lab_edge = cv2.morphologyEx((lab == 1).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
        near_le = cv2.dilate((lab_edge | et).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
        bm = b & m
        unsure = (pf > 0.1) & (pf < 0.9)
        # P(block) sampled 6 px (half size) either side of verified edges: a clean street/block step means |P_a - P_b| near 1
        out[f'{model}/{plate}'] = dict(
            accuracy=round(float((pr == gt).mean()), 4), iou_street=round(iou(~pr, ~gt), 4), iou_block=round(iou(pr, gt), 4),
            err_street_called_block=round(float((pr & ~gt).sum() / max(1, (~gt).sum())), 4),
            green_edge_met_by_boundary=round(float(near_b[et].mean()), 4),
            false_boundary_share=round(float((bm & ~near_le).sum() / max(1, bm.sum())), 4),
            unsure_share_labelled=round(float(unsure[m].mean()), 4),
            mean_conf_labelled=round(float(np.abs(pf[m] - 0.5).mean() * 2), 4),
            unsure_share_within_6px_of_green=round(float(unsure[cv2.dilate(et.astype(np.uint8), np.ones((13, 13), np.uint8)) > 0].mean()), 4))
        print(model, plate, json.dumps(out[f'{model}/{plate}']), flush=True)
json.dump(out, open(sys.argv[1], 'w'), indent=1)
