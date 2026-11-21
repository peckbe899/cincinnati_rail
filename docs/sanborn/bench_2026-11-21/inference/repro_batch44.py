"""Faithfulness check: do the copied network functions in infer_lib.py give the batch's maps for plate 44?

    VENV_PYTHON repro_batch44.py [--cpu]

1. the D4 transforms invert exactly and (3, True) is the transpose;
2. the repo-copy predict (unet.py / edgenet.py predict_full, copied) on the GPU (DirectML) against the stored
   unet_data/44_pred_area_ng1.png and 44_lines_lines_ng1.png (the batch's own maps);
3. infer_lib.predict(blend='crop', tta=1) against the repo copy (must be identical: same tiles, same calls);
4. the time of each pass.
Writes maps/repro/44_area.png, 44_lines.png and logs/repro_batch44.json (only inside this folder).
"""
import json, os, sys, time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2, torch
import infer_lib as L

out = L.HERE + 'maps/repro/'; os.makedirs(out, exist_ok=True); os.makedirs(L.HERE + 'logs', exist_ok=True)
res = {}
# 1. transforms
x = torch.arange(2 * 3 * 5 * 5, dtype=torch.float32).reshape(2, 3, 5, 5)
res['d4_inverse_exact'] = all(torch.equal(L.inv_t(L.fwd_t(x, k, f), k, f), x) for k, f in L.D4)
res['d4_distinct'] = len({tuple(L.fwd_t(x, k, f).flatten().tolist()) for k, f in L.D4}) == 8
res['transpose_is_(3,True)'] = torch.equal(L.fwd_t(x, 3, True), x.transpose(2, 3))
res['tta4_set'] = L.TTA_SETS[4]
dev = torch.device('cpu') if '--cpu' in sys.argv else L.device(); res['device'] = str(dev)
dev, na, nl = L.load_nets(dev)
full = cv2.imread(L.SP + 'cufp/22-44.jpg'); H, W = full.shape[:2]
img = cv2.resize(full, (W // 2, H // 2), interpolation=cv2.INTER_AREA); z = np.zeros(img.shape[:2], np.uint8)
xa = np.dstack([img[:, :, ::-1], z, z])
t0 = time.time(); p_repo = L.repo_predict_area(na, dev, xa); res['area_repo_s'] = round(time.time() - t0, 2)
t0 = time.time(); p_mine = L.predict(na, dev, xa, L.prob_area, 768, 64, 1, 'crop'); res['area_lib_s'] = round(time.time() - t0, 2)
pa = L.u8(p_repo); stored_a = cv2.imread(L.U + '44_pred_area_ng1.png', 0)
d = np.abs(pa.astype(int) - stored_a.astype(int))
res['area_vs_batch'] = dict(max_abs=int(d.max()), share_differ=round(float((d > 0).mean()), 6), share_differ_gt1=round(float((d > 1).mean()), 6),
                            decision_differs=round(float(((pa > 127) != (stored_a > 127)).mean()), 6))
res['area_lib_vs_repo_max_abs'] = float(np.abs(p_mine - p_repo).max())
cv2.imwrite(out + '44_area.png', pa)
# lines on the stored area map (so the check isolates the line network)
inkimg, _ = L.ink_image(full); Z = np.zeros((H, W), np.uint8)
xl = np.dstack([full[:, :, ::-1], inkimg, Z, Z, cv2.resize(stored_a, (W, H), interpolation=cv2.INTER_LINEAR)])
t0 = time.time(); q_repo = L.repo_predict_lines(nl, dev, xl); res['lines_repo_s'] = round(time.time() - t0, 2)
t0 = time.time(); q_mine = L.predict(nl, dev, xl, L.prob_lines, 1024, 96, 1, 'crop', batch=4); res['lines_lib_s'] = round(time.time() - t0, 2)
pl = L.u8(q_repo); stored_l = cv2.imread(L.U + '44_lines_lines_ng1.png', 0)
d = np.abs(pl.astype(int) - stored_l.astype(int))
res['lines_vs_batch'] = dict(max_abs=int(d.max()), share_differ=round(float((d > 0).mean()), 6), share_differ_gt1=round(float((d > 1).mean()), 6),
                             decision_differs=round(float(((pl > 127) != (stored_l > 127)).mean()), 6))
res['lines_lib_vs_repo_max_abs'] = float(np.abs(q_mine - q_repo).max())
cv2.imwrite(out + '44_lines.png', pl)
# tta timing probe: one 8-way pass of each network on 4 tiles
t0 = time.time()
for _ in range(4): L.run_tile(na, dev, xa[:768, :768], L.prob_area, 8)
res['area_tile_tta8_s'] = round((time.time() - t0) / 4, 3)
t0 = time.time()
for _ in range(4): L.run_tile(nl, dev, xl[:1024, :1024], L.prob_lines, 8, batch=4)
res['lines_tile_tta8_s'] = round((time.time() - t0) / 4, 3)
json.dump(res, open(L.HERE + 'logs/repro_batch44' + ('_cpu' if '--cpu' in sys.argv else '') + '.json', 'w'), indent=1)
print(json.dumps(res, indent=1))
