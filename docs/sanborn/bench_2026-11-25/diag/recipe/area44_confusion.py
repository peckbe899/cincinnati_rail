"""Where do the new area nets lose IoU street on plate 44? Confusion of each pair's grid0 area map against the 21 Nov
44 label (unet_data/44_label.png, the label area_ng1 was watched on) and against Ben's map ground (decided ground:
his closed blocks = block; street = the street ground make_labels_v2 'map' mode would teach, approximated here by the
label's street), split by distance from the paper edge (half px). Reads only; system python."""
import json, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
EV = SP + 'train_v2_runs/eval/'; OUT = SP + 'bench_2026-11-25/diag/recipe/'
STEPS = ['baseline', 'V1S1', 'V2S1', 'V1S2', 'V2S2']
lab = cv2.imread(SP + 'unet_data/44_label.png', 0); h, w = lab.shape
alpha = cv2.resize(np.load(SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (w, h)) > 0.5
dpe = cv2.distanceTransform(alpha.astype(np.uint8), cv2.DIST_L2, 5)     # distance to the paper edge, half px
T = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8')); tb = np.zeros((h, w), np.uint8)
for b in T['blocks']: cv2.fillPoly(tb, [(np.array(b['ring']) / 2).round().astype(np.int32)], 1)
zones = {'edge<60': (dpe < 60) & alpha, '60-200': (dpe >= 60) & (dpe < 200), 'interior>=200': dpe >= 200}
res = {'label_counts': {z: dict(block=int(((lab == 1) & m).sum()), street=int(((lab == 0) & m).sum()), untaught=int(((lab == 255) & m).sum())) for z, m in zones.items()}}
for s in STEPS:
    p = cv2.imread(EV + f'{s}/maps44/grid0/44_area.png', 0) > 127; r = {}
    for z, m in list(zones.items()) + [('all', alpha)]:
        st = (lab == 0) & m; bl = (lab == 1) & m
        r[z] = dict(street_called_block=round(float(p[st].mean()), 4) if st.any() else None, block_called_street=round(float((~p)[bl].mean()), 4) if bl.any() else None,
                    iou_street=round(float((~p & st).sum() / max(1, ((~p & (st | bl)) | st).sum())), 4))
    inb = tb == 1
    r['ben_blocks_called_street'] = round(float((~p)[inb & alpha].mean()), 4)
    r['untaught_called_block'] = round(float(p[(lab == 255) & alpha].mean()), 4)
    res[s] = r; print(s, json.dumps(r), flush=True)
json.dump(res, open(OUT + 'area44_confusion.json', 'w'), indent=1); print(json.dumps(res['label_counts']))
