"""design (25 Nov 2026): the few new numbers round2.md uses. Read-only; writes only diag/design/design_numbers.json.
    cd data/sanborn; python -B bench_2026-11-25/diag/design/scripts/design_numbers.py

1. Plate 5's candidate validation region (right quarter, x >= 0.75 W, the cut make_labels_v2 map uses by default):
   Ben's blocks by ring centroid, his non-sheet deleted lines by the midpoint of their original place.
2. Area-net crop shares of the round-2 plates under three sampling rules (equal per plate, proportional to taught
   half-size px, proportional to its square root). Taught px: diag/verify/label_prior.json (43, 45, 80, 82A, 1A outside
   its valmask) and diag/ben-labels/map_now/5_counts.json (5 outside the right quarter).
3. Seed noise from round 1 (train_v2_runs/summary.md 44 PQ by seed) and the standard errors of seed means.
4. Line-net F1 drop when the 7th input changes from area_ng1's map to a new area net's map (diag/swap/pixel).
5. GPU hours from measured step times.
"""
import json, os, math
import numpy as np
SP = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')) + os.sep
D = SP + 'bench_2026-11-25/diag/'
out = {}

# 1. plate 5 region
sm = json.load(open(D + 'ben-labels/map_now/5_streetmap.json', encoding='utf8'))
cnt = json.load(open(D + 'ben-labels/map_now/5_counts.json', encoding='utf8'))['counts']
W = cnt['size_full'][0]; cut = 0.75 * W
cx = np.array([np.mean([p[0] for p in b['ring']]) for b in sm['blocks']])
eb = json.load(open(SP + 'picks22_guided/22-5/edges_ben.json', encoding='utf8'))['lines']
wr = [l for l in eb if l.get('verdict') == 'wrong' and l.get('src') != 'sheet']
mx = np.array([(l['a0'][0] + l['b0'][0]) / 2 for l in wr])
out['plate5_right_quarter'] = dict(cut_x_full=cut, blocks=int((cx >= cut).sum()), blocks_all=len(cx),
                                   deleted_nonsheet=int((mx >= cut).sum()), deleted_nonsheet_all=len(wr),
                                   paper_share=cnt['val_paper_share'], val_block_half_px=cnt['val_block'], val_street_half_px=cnt['val_street'],
                                   val_line_pos_full_px=cnt['val_line_pos'], line_pos_full_px=cnt['line_pos'],
                                   blocks_by_quarter=[int(((cx >= q * W / 4) & (cx < (q + 1) * W / 4)).sum()) for q in range(4)])
taught5 = cnt['block'] + cnt['street']; val5 = cnt['val_block'] + cnt['val_street']

# 2. crop shares
lp = json.load(open(D + 'verify/label_prior.json', encoding='utf8'))['plates']
tp = {p: lp[p]['taught_px'] for p in ('43', '45', '80', '82A', '1A')}; tp['5'] = taught5 - val5
sh = {}
for rule, f in (('equal', lambda v: 1.0), ('proportional', lambda v: v), ('sqrt', math.sqrt)):
    w = {p: f(v) for p, v in tp.items()}; s = sum(w.values())
    sh[rule] = {p: round(v / s, 3) for p, v in w.items()}
    sh[rule]['old_four'] = round(sum(w[p] for p in ('43', '45', '80', '82A')) / s, 3)
out['area_taught_train_half_px'] = tp; out['area_crop_share'] = sh

# 3. seed noise (round 1, 44 PQ, mean of 6 grids)
pq = dict(V1=(0.368, 0.470), V2=(0.438, 0.482))
sds = {k: abs(a - b) / math.sqrt(2) for k, (a, b) in pq.items()}
pooled = math.sqrt(sum(v * v for v in sds.values()) / len(sds))
out['seed_noise'] = dict(sd_by_variant={k: round(v, 4) for k, v in sds.items()}, pooled_sd=round(pooled, 4),
                         se_mean={n: round(pooled / math.sqrt(n), 4) for n in (2, 3, 4, 6)},
                         se_diff_4v3=round(pooled * math.sqrt(1 / 4 + 1 / 3), 4), se_diff_6v6=round(pooled * math.sqrt(2 / 6), 4),
                         note='estimate: two seeds per variant only')

# 4. 7th-input dependence (pixel F1 on 44 interior lines, mean of 6 grids)
px = json.load(open(D + 'swap/pixel/pixel_maps44.json', encoding='utf8'))
f = lambda k: px[k]['mean']['f1_interior']
dep = {}
for s in ('V1S1', 'V1S2', 'V2S1', 'V2S2'):
    good, own = f(f'lines:{s}best|ch7=ng1'), f(f'lines:{s}best|ch7={s}best')
    ng1_good, ng1_bad = f('lines:ng1|ch7=ng1'), f(f'lines:ng1|ch7={s}best')
    dep[s] = dict(new_line_net_with_area_ng1=good, with_own_area=own, drop=round(good - own, 4),
                  lines_ng1_with_area_ng1=ng1_good, lines_ng1_with_this_area=ng1_bad, lines_ng1_drop=round(ng1_good - ng1_bad, 4))
out['ch7_dependence'] = dep

# 5. GPU hours: the round-1 models' own 'minutes' (train_v2_runs/models/*.json, 4000 iterations each) and eval_v2's
#    2.4-3.2 min per pair (diag/swap run_swaps.log; 3.0 used)
import glob
mins = {k: [json.load(open(f, encoding='utf8'))['minutes'] for f in glob.glob(SP + f'train_v2_runs/models/{k}_v2*_s?.json')] for k in ('area', 'lines')}
area_min, line_min, ev_min = float(np.mean(mins['area'])), float(np.mean(mins['lines'])), 3.0
out['round1_minutes'] = mins
full = dict(area_nets=10, line_nets=5, evals=22); short = dict(area_nets=6, line_nets=2, evals=10)
gh = lambda c: round((c['area_nets'] * area_min + c['line_nets'] * line_min + c['evals'] * ev_min) / 60, 1)
out['gpu'] = dict(area_net_min=round(area_min, 1), line_net_min=round(line_min, 1), eval_min=ev_min,
                  full=dict(full, hours=gh(full)), short=dict(short, hours=gh(short)))
json.dump(out, open(D + 'design/design_numbers.json', 'w', encoding='utf8'), indent=1)
print(json.dumps(out, indent=1))
