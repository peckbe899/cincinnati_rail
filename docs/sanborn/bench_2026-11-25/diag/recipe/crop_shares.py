"""Crops per plate: ng1 (estimated: its sampler drew a plate uniformly, then a crop, and on a reject drew a new plate,
so each plate's share is proportional to its crop acceptance rate) against V1 and V2 (measured: crops_drawn in the
model jsons). Acceptance: area net, >= 20% taught pixels in a 384 crop of label.png (the V1 json's crop_ok_share uses
the same rule); line net, >= 60 line pixels in a 448 crop of lines.png, else kept with probability 0.2 (edgenet
train()). Also how many times each taught pixel / line pixel is seen, and the learning rate at the chosen
checkpoints. Reads only; system python. Line acceptance from 3000 random positions per plate (seed 7)."""
import json, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; OUT = SP + 'bench_2026-11-25/diag/recipe/'; M = SP + 'train_v2_runs/models/'
P4 = ['43', '45', '80', '82A']; rng = np.random.default_rng(7); JIT = 24
la = {}
for p in P4 + ['1A']:
    t = cv2.imread(SP + f'train_v2/{p}/lines.png', 0); H, W = t.shape; ii = cv2.integral((t == 1).astype(np.uint8)); n = 3000; ok = 0.0
    vx = 2841 if p == '1A' else W   # 1A: training crops stop before the validation ground
    for _ in range(n):
        y = rng.integers(JIT, H - 448 - JIT); x = rng.integers(JIT, min(W - 448 - JIT, vx - 448 - 3))
        s = ii[y + 448, x + 448] - ii[y, x + 448] - ii[y + 448, x] + ii[y, x]
        ok += 1.0 if s >= 60 else 0.2
    la[p] = dict(accept=round(ok / n, 4), line_px=int((t[:, :vx] == 1).sum()))
area_ok = {r['plate']: r for r in json.load(open(M + 'area_v2a_s1.json'))['plates']}
A = {p: area_ok[p]['crop_ok_share'] for p in P4}; sA = sum(A.values()); L = {p: la[p]['accept'] for p in P4}; sL = sum(L.values())
ng1_area = {p: round(32000 * A[p] / sA) for p in P4}; ng1_lines = {p: round(24000 * L[p] / sL) for p in P4}
res = dict(line_accept=la, area_accept={p: area_ok[p]['crop_ok_share'] for p in P4 + ['1A']}, ng1_area_crops_est=ng1_area, ng1_lines_crops_est=ng1_lines, runs={})
for nm in ['area_v2a_s1', 'area_v2a_s2', 'area_v2b_s1', 'area_v2b_s2', 'lines_v2a_s1', 'lines_v2a_s2', 'lines_v2b_s1', 'lines_v2b_s2']:
    d = json.load(open(M + nm + '.json')); cd = d['crops_drawn']; tot = sum(cd.values()); ref = ng1_area if nm.startswith('area') else ng1_lines
    pl = {r['plate']: r for r in d['plates']}; C = 384 * 384 if nm.startswith('area') else 448 * 448
    res['runs'][nm] = dict(total=tot, label_plates_vs_ng1={p: round(cd[p] / ref[p], 3) for p in P4}, share_1A=round(cd['1A'] / tot, 3),
                           share_label4=round(sum(cd[p] for p in P4) / tot, 3), share_pseudo=round(sum(v for k, v in cd.items() if pl[k]['source'] == 'pseudo') / tot, 3),
                           best=d['best'])
    if nm.startswith('area'):
        res['runs'][nm]['crop_views_per_taught_px'] = {p: round(cd[p] * C / pl[p]['train_px'], 1) for p in ['43', '45', '80', '82A', '1A']}
    else:
        res['runs'][nm]['crops_per_1000_line_px'] = {p: round(1000 * cd[p] / pl[p]['train_line_px'], 2) for p in ['43', '45', '80', '82A', '1A']}
res['ng1_crop_views_per_taught_px_est'] = {p: round(ng1_area[p] * 384 * 384 / area_ok[p]['train_px'], 1) for p in P4}
res['ng1_crops_per_1000_line_px_est'] = {p: round(1000 * ng1_lines[p] / la[p]['line_px'], 2) for p in P4}
lr = lambda it: 1e-3 * 0.5 * (1 + np.cos(np.pi * it / 4000))
res['lr_at'] = {it: float('%.3g' % lr(it)) for it in (2500, 3000, 3250, 3500, 3750, 4000)}
json.dump(res, open(OUT + 'crop_shares.json', 'w'), indent=1); print(json.dumps(res, indent=1))
