"""review-leak: can a training crop of either staged trainer touch 1A's validation ground? Uses the STAGED code's own
functions (draw_crop, box_sum, overlaps_val) on the real train_v2/1A files. Exhaustive over every crop column the
samplers can draw, plus random draws with the seeds the driver uses. Reads only; CPU only (no network is built).
cd data/sanborn; ../../tools/sanborn/unet/.venv/Scripts/python.exe -B bench_2026-11-23/train/review-leak/scripts/crop_leak.py"""
import json, os, sys, time
import numpy as np, cv2
REPO = os.path.abspath('../..'); STAGED = os.path.normpath(os.path.join(REPO, 'data/sanborn/bench_2026-11-23/train/staged/tools/sanborn/unet'))
sys.path.insert(0, os.path.join(REPO, 'tools/sanborn')); sys.path.insert(0, STAGED)
import unet as U, edgenet as E  # noqa: E402  (the staged copies)
assert os.path.dirname(os.path.abspath(U.__file__)) == STAGED and os.path.dirname(os.path.abspath(E.__file__)) == STAGED, (U.__file__, E.__file__)
OUT = 'bench_2026-11-23/train/review-leak/'; root = os.path.abspath('train_v2'); R = {}

# ---------------------------------------------------------------- area net (half size), as unet.train_data builds 1A
x, lab, wm, et, _ = U.load_data(root, '1A'); vm = U.read_valmask(root, '1A', lab.shape)
vint = cv2.integral(vm.astype(np.uint8)); tl = lab.copy(); tl[vm] = 255
P = dict(plate='1A', x=x, lab=tl, wm=wm, et=et, vint=vint); H, W = lab.shape; C = U.CROP
# exhaustive: every (y, x) the sampler can draw (y in [0, H-C), x in [0, W-C)); the staged test vs the truth
bad, rejected_ok, n = 0, 0, 0
colany = np.concatenate([[False], np.cumsum(vm.any(0)) > 0])  # unused helper
for yy in range(0, H - C, 7):
    for xx in range(0, W - C):
        hit = U.box_sum(vint, yy, xx, yy + C, xx + C) > 0; truth = bool(vm[yy:yy + C, xx:xx + C].any()) if xx + C > 1400 else False
        n += 1
        if truth and not hit: bad += 1
R['area_exhaustive'] = dict(positions=n, val_touching_but_accepted=bad, note='y every 7th row, every x')
# random draws through the real draw_crop, as the trainer draws (rng = default_rng(seed))
for seed in (1, 2):
    rng = np.random.default_rng(seed); mx, touch = 0, 0; t0 = time.time()
    for _ in range(200000):
        yy, xx = U.draw_crop(rng, P); mx = max(mx, xx + C)
        if vm[yy:yy + C, xx:xx + C].any(): touch += 1
    R[f'area_draws_seed{seed}'] = dict(draws=200000, touching_val=touch, max_crop_end_col=int(mx), val_first_col=int(np.nonzero(vm.any(0))[0][0]), s=round(time.time() - t0, 1))
print(json.dumps(R), flush=True)
# what of the val ground still reaches the training arrays indirectly: the edge weight map and target near the cut
e = cv2.imread(os.path.join(root, '1A', 'edge.png'), 0); ev = e.copy(); ev[vm] = 0
wm_no_val, et_no_val = U.edge_maps(ev, lab)
reach = slice(0, 1420)
R['area_weight_map_from_val_edges'] = dict(train_px_weight_changed=int((np.abs(wm[:, reach] - wm_no_val[:, reach]) > 1e-3).sum()), max_abs_change=round(float(np.abs(wm[:, reach] - wm_no_val[:, reach]).max()), 4),
                                           of_which_in_reachable_crops=int((np.abs(wm[:, :1420] - wm_no_val[:, :1420]) > 1e-3).sum()),
                                           edge_target_changed_in_train=int((et[:, reach] != et_no_val[:, reach]).sum()))
print(json.dumps(R['area_weight_map_from_val_edges']), flush=True)
del x, P

# ---------------------------------------------------------------- line net (full size), as edgenet.train_data builds 1A
S, _ = E.load_data(root, '1A'); Hf, Wf = S.shape[:2]
vh = U.read_valmask(root, '1A', (Hf // 2, Wf // 2)); vf = cv2.resize(vh.astype(np.uint8), (Wf, Hf), interpolation=cv2.INTER_NEAREST) > 0
vinth = cv2.integral(vh.astype(np.uint8)); Cf = E.CROP; J = E.JIT
first_full = int(np.nonzero(vf.any(0))[0][0])
bad, n, accepted_max_end = 0, 0, 0
for xx in range(J, Wf - Cf - J):
    for yy in (J, (Hf - Cf) // 2, Hf - Cf - J - 1):
        hit = E.overlaps_val(vinth, yy, xx, Cf); truth = bool(vf[yy:yy + Cf, xx:xx + Cf].any()); n += 1
        if truth and not hit: bad += 1
        if not hit: accepted_max_end = max(accepted_max_end, xx + Cf)
R['lines_exhaustive'] = dict(positions=n, val_touching_but_accepted=bad, accepted_crop_end_col_max=int(accepted_max_end), val_first_full_col=first_full, margin_cols=first_full - accepted_max_end)
# the +-1 half-pixel margin, on random masks (not only a half-plane) at 1A's size: is overlaps_val always conservative?
rng = np.random.default_rng(7); miss = 0; tests = 0
for k in range(300):
    m = np.zeros((Hf // 2, Wf // 2), np.uint8); cy, cx = rng.integers(0, Hf // 2), rng.integers(0, Wf // 2); m[cy:cy + rng.integers(1, 4), cx:cx + rng.integers(1, 4)] = 1
    mf = cv2.resize(m, (Wf, Hf), interpolation=cv2.INTER_NEAREST) > 0; ii = cv2.integral(m)
    ys, xs = np.nonzero(mf)
    for _ in range(40):
        yy = int(np.clip(ys.min() - rng.integers(0, Cf + 3), 0, Hf - Cf)); xx = int(np.clip(xs.min() - rng.integers(0, Cf + 3), 0, Wf - Cf))
        tr = bool(mf[yy:yy + Cf, xx:xx + Cf].any()); tests += 1
        if tr and not E.overlaps_val(ii, yy, xx, Cf): miss += 1
R['lines_margin_random_masks'] = dict(tests=tests, missed=miss)
for seed in (1, 2):
    rng = np.random.default_rng(seed); P = dict(plate='1A', S=S, vint=vinth); mx, touch = 0, 0; t0 = time.time()
    for _ in range(100000):
        yy, xx = E.draw_crop(rng, P); mx = max(mx, xx + Cf)
        if vf[yy:yy + Cf, xx:xx + Cf].any(): touch += 1
    R[f'lines_draws_seed{seed}'] = dict(draws=100000, touching_val=touch, max_crop_end_col=int(mx), s=round(time.time() - t0, 1))
# the val ground's line positives near the cut: how close do they come to what a crop can reach?
t = S[:, :, 4]; pos_val = (t == 1) & vf; cols = np.nonzero(pos_val.any(0))[0]
R['lines_val_positive_first_col'] = int(cols[0]) if len(cols) else None
print(json.dumps(R, indent=1), flush=True)
json.dump(R, open(OUT + 'crop_leak.json', 'w'), indent=1)
