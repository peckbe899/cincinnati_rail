"""Is train_v2's 7th input (area_in.png) for 43/45/80/82A the map lines_ng1 actually trained with?
lines_ng1 trained 21 Nov 00:58-01:45 on unet_data/N_pred_area_ng1.png made by unet.py predict from N_img.jpg (JPEG q92).
The batch (blocks_noguide, 21 Nov 10:06-10:35) rewrote those files from a fresh INTER_AREA resize (no JPEG).
ml_review_2026-11-21/verify-line-net/snap/ holds snapshots taken before the overwrite (where its mtime says so).
Compares, per plate: sha, share of pixels whose >127 decision flips, mean |diff|, on the paper. Reads only."""
import json, os, hashlib, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
OUT = SP + 'bench_2026-11-25/diag/recipe/'
res = {}
for n in ['43', '45', '80', '82A']:
    a = cv2.imread(SP + f'train_v2/{n}/area_in.png', 0)
    r = {}
    for nm, f in [('snap_verify_line_net', SP + f'ml_review_2026-11-21/verify-line-net/snap/{n}_pred_area_ng1.png'),
                  ('snap_fromimgjpg', SP + f'ml_review_2026-11-21/evaluation/snap/{n}_pred_area_ng1_fromimgjpg.png'),
                  ('legacy_data', SP + f'bench_2026-11-23/train/trainer/legacy_data/{n}_pred_area_ng1.png')]:
        if not os.path.exists(f): continue
        b = cv2.imread(f, 0)
        if b.shape != a.shape: r[nm] = f'shape {b.shape} vs {a.shape}'; continue
        al = cv2.resize(np.load(SP + f'cufp/{n}/png_alpha_s4.npy').astype(np.float32), (a.shape[1], a.shape[0])) > 0.5
        lab = cv2.imread(SP + f'train_v2/{n}/label.png', 0); m = lab != 255
        r[nm] = dict(identical=bool((a == b).all()), mtime=os.path.getmtime(f), flip_share_paper=round(float(((a > 127) != (b > 127))[al].mean()), 5),
                     mean_abs=round(float(np.abs(a.astype(int) - b.astype(int))[al].mean()), 3),
                     acc_area_in=round(float(((a > 127) == (lab == 1))[m].mean()), 5), acc_other=round(float(((b > 127) == (lab == 1))[m].mean()), 5))
    res[n] = r
json.dump(res, open(OUT + 'ch7_vs_ng1_training.json', 'w'), indent=1); print(json.dumps(res, indent=1))
