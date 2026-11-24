"""review-code: how much the trainers' validation score on 1A changes when the validation ground is predicted from its
own bounding box (as the staged train_data does) rather than from the whole plate (as the batch and eval_v2 predict it).
Uses the batch's area_ng1 and lines_ng1 (never trained on 1A) on the CPU. Reads unet_data/models and train_v2/1A only.

    VENV -B test_valcontext.py
"""
import json, os, sys, time
sys.dont_write_bytecode = True
REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
STAGED = REPO + 'data/sanborn/bench_2026-11-23/train/staged/tools/sanborn/unet/'
RC = REPO + 'data/sanborn/bench_2026-11-23/train/review-code/'
sys.argv = [sys.argv[0]]
sys.path.insert(0, REPO + 'tools/sanborn'); sys.path.insert(0, STAGED)
import numpy as np, cv2, torch
import unet as U, edgenet as E
torch.set_num_threads(12); dev = torch.device('cpu'); D = REPO + 'data/sanborn/train_v2/'; M = REPO + 'data/sanborn/unet_data/models/'
res = {}
# area
x, lab, wm, et, _ = U.load_data(D, '1A'); vm = U.read_valmask(D, '1A', lab.shape); y0, y1, x0, x1 = U.bbox(vm)
lv = lab[y0:y1, x0:x1].copy(); lv[~vm[y0:y1, x0:x1]] = 255
na = U.UNet(); na.load_state_dict(torch.load(M + 'area_ng1.pt', map_location='cpu')); na.eval()
t0 = time.time(); pb = U.predict_full(na, dev, np.ascontiguousarray(x[y0:y1, x0:x1])); pw = U.predict_full(na, dev, x)[y0:y1, x0:x1]
cb, cw = U.counts(pb, lv), U.counts(pw, lv)
band = np.zeros_like(lv); band[:, :200] = 1
res['area'] = dict(bbox_only=U.pooled(cb), whole_plate=U.pooled(cw), decisions_differ_share=round(float(((pb > 0.5) != (pw > 0.5))[lv != 255].mean()), 5),
                   decisions_differ_share_first_200px=round(float(((pb > 0.5) != (pw > 0.5))[(lv != 255) & (band > 0)].mean()), 5), seconds=round(time.time() - t0, 1))
print(json.dumps(res['area']), flush=True)
# lines
S, _ = E.load_data(D, '1A'); H, W = S.shape[:2]; vh = U.read_valmask(D, '1A', (H // 2, W // 2))
vf = cv2.resize(vh.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0; y0, y1, x0, x1 = U.bbox(vf)
xv, tv, _ = E.build(S, y0, y1, x0, x1); mv = vf[y0:y1, x0:x1]; tv[~mv] = 255
nl = U.UNet(classes=2, in_ch=7); nl.load_state_dict(torch.load(M + 'lines_ng1.pt', map_location='cpu')); nl.eval()
t0 = time.time(); qb = E.predict_full(nl, dev, xv)
xa, _, _ = E.build(S, 0, H, 0, W); qw = E.predict_full(nl, dev, xa)[y0:y1, x0:x1]; del xa
res['lines'] = dict(bbox_only=E.prf(E.line_counts(qb, tv, mv)), whole_plate=E.prf(E.line_counts(qw, tv, mv)),
                    decisions_differ_px=int(((qb > 0.5) != (qw > 0.5))[mv].sum()), seconds=round(time.time() - t0, 1))
print(json.dumps(res['lines']), flush=True)
json.dump(res, open(RC + 'test_valcontext.json', 'w'), indent=1)
