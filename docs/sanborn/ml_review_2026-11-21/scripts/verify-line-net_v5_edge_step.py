"""Read-only: at the verified edges (half size), how often does area_ng1's P(block) step from street to block? training plates vs 44."""
import json, numpy as np, cv2
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
S = 'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/verify-line-net/'
out = {}
for n in ('82A', '80', '43', '45', '44'):
    p = cv2.imread(S + f'snap/{n}_pred_area_ng1.png', 0).astype(np.float32) / 255; h, w = p.shape
    V = json.load(open(D + f'{n}_verified.json', encoding='utf8'))
    diffs = []; steps = 0; tot = 0
    for a, b in V:
        a = np.array(a) / 2; b = np.array(b) / 2; d = b - a; L = np.hypot(*d)
        if L < 4: continue
        nr = np.array([-d[1], d[0]]) / L
        for s in np.linspace(0, 1, max(2, int(L / 4))):
            c = a + d * s; q1 = (c + nr * 6).round().astype(int); q2 = (c - nr * 6).round().astype(int)
            if not (0 <= q1[0] < w and 0 <= q1[1] < h and 0 <= q2[0] < w and 0 <= q2[1] < h): continue
            v1, v2 = p[q1[1], q1[0]], p[q2[1], q2[0]]; tot += 1; diffs.append(abs(v1 - v2)); steps += (min(v1, v2) < 0.5 < max(v1, v2))
    diffs = np.array(diffs)
    out[n] = dict(samples=tot, step_across_0p5=round(steps / tot, 4), mean_abs_step=round(float(diffs.mean()), 4), clean_step_gt_0p8=round(float((diffs > 0.8).mean()), 4), no_step_lt_0p2=round(float((diffs < 0.2).mean()), 4))
    print(n, out[n])
json.dump(out, open(S + 'v5_edge_step.json', 'w'), indent=1)
