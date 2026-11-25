"""Line nets fed area_ng1's map (the swap agent's maps, diag/swap/eval/a__ng1+L_*): their F1 on 1A's validation region
(the trainers' score, whole plate predicted) against the trainers' own best F1 (bounding box only, area_ng1's map as
the 7th input) and against the F1 when fed their own partner area map (train_v2_runs/eval/STEP/maps1A). Also the
44 line F1 against the 21 Nov target and Ben-line recall within 3 px (grid0) where the swap maps44 exist.
Reads only (the swap folder is read, never written); system python."""
import json, os, numpy as np, cv2, importlib.util
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; OUT = SP + 'bench_2026-11-25/diag/recipe/'; SW = SP + 'bench_2026-11-25/diag/swap/eval/'
spec = importlib.util.spec_from_file_location('vv', OUT + 'val_vs_44.py')
src = open(OUT + 'val_vs_44.py', encoding='utf8').read().split('lab1 = cv2.imread')[0]   # the helper functions only
ns = {}; exec(src, ns)
lab1 = cv2.imread(SP + 'train_v2/1A/label.png', 0); vm1 = cv2.imread(SP + 'train_v2/1A/valmask.png', 0) > 0
t1 = cv2.imread(SP + 'train_v2/1A/lines.png', 0); H1, W1 = t1.shape
vf = cv2.resize(vm1.astype(np.uint8), (W1, H1), interpolation=cv2.INTER_NEAREST) > 0
ys, xs = np.nonzero(vf.any(1))[0], np.nonzero(vf.any(0))[0]; y0, y1, x0, x1 = ys[0], ys[-1] + 1, xs[0], xs[-1] + 1
tv = t1[y0:y1, x0:x1].copy(); mv = vf[y0:y1, x0:x1]; tv[~mv] = 255
t44 = ns['lines_target_44']()
T = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
def ben_recall(pl):
    mx = cv2.dilate(pl, np.ones((7, 7), np.uint8)); H, W = pl.shape; v = []
    for l in T['lines']:
        if l['kind'] not in ('printed', 'drawn'): continue
        a, b = np.array(l['a'], float), np.array(l['b'], float); n = max(2, int(np.hypot(*(b - a)) / 4)); q = a + np.outer(np.linspace(0.05, 0.95, n), b - a)
        v.append(mx[np.clip(q[:, 1].round().astype(int), 0, H - 1), np.clip(q[:, 0].round().astype(int), 0, W - 1)])
    return round(float((np.concatenate(v) > 127).mean()), 4)
res = {}
for s in ['V1S1', 'V2S1', 'V1S2', 'V2S2']:
    d = SP + f'train_v2_runs/models/lines_v2{"a" if s[1] == "1" else "b"}_s{s[3]}.json'
    r = dict(trainer_best=json.load(open(d))['best'])
    f = SW + f'a__ng1+L_{s}/maps1A/1A_lines.png'
    if os.path.exists(f): r['val1A_f1_with_area_ng1_map'] = ns['line_counts'](cv2.imread(f, 0)[y0:y1, x0:x1], tv, mv)
    r['val1A_f1_with_own_area_map'] = ns['line_counts'](cv2.imread(SP + f'train_v2_runs/eval/{s}/maps1A/1A_lines.png', 0)[y0:y1, x0:x1], tv, mv)
    g = SW + f'a__ng1+L_{s}/maps44/grid0/44_lines.png'
    if os.path.exists(g):
        pl = cv2.imread(g, 0); r['t44_with_area_ng1_map'] = ns['line_counts'](pl, t44); r['ben_recall3px_with_area_ng1_map'] = ben_recall(pl)
    pl = cv2.imread(SP + f'train_v2_runs/eval/{s}/maps44/grid0/44_lines.png', 0); r['t44_with_own_area_map'] = ns['line_counts'](pl, t44); r['ben_recall3px_with_own_area_map'] = ben_recall(pl)
    res[s] = r; print(s, json.dumps(r), flush=True)
pl = cv2.imread(SP + 'train_v2_runs/eval/baseline/maps44/grid0/44_lines.png', 0); res['baseline'] = dict(t44=ns['line_counts'](pl, t44), ben_recall3px=ben_recall(pl)); print('baseline', res['baseline'])
json.dump(res, open(OUT + 'swap_lines_check.json', 'w'), indent=1)
