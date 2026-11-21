"""v-final: on plate 44 (batch grid), (1) shown editor lines (44_shown.json, sheet lines left out) lying mostly (> 50% of
their length) within 3 px of the railroad bin of unet_data/44_bins.png, for the repo step (orig/runs/base__grid0) and the
merged step (staged_runs/staged__grid0); (2) intact rings recounted here: block outlines (no holes) whose every side
survives the merged step 4 (not short, paper_edge, 'not on a line' or 'on rail') and whose sides join end to end
within 1.5 px, on each grid.
    python -B rail_rings44.py -> v-final/rail_rings44.json"""
import json
import numpy as np, cv2
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-final/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
rr = cv2.dilate((cv2.imread(SP + 'unet_data/44_bins.png', cv2.IMREAD_UNCHANGED) == 4).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))); H, W = rr.shape
def share(e):
    a, b = np.array(e['a'], float), np.array(e['b'], float); t = np.linspace(0.06, 0.94, max(10, int(np.hypot(*(b - a))))); q = a + np.outer(t, b - a)
    return float(rr[np.clip(q[:, 1].round().astype(int), 0, H - 1), np.clip(q[:, 0].round().astype(int), 0, W - 1)].mean())
res = {}
for tag, d in (('repo_step', V + 'orig/runs/base__grid0/'), ('merged', V + 'staged_runs/staged__grid0/')):
    S = [e for e in json.load(open(d + '44_shown.json')) if e.get('src') != 'sheet']; on = [e for e in S if share(e) > 0.5]
    res[tag] = dict(shown=len(S), mostly_on_rail=len(on), mostly_on_rail_len=round(sum(np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1]) for e in on)))
def intact(P):
    j = lambda p: all(np.hypot(*(np.array(p[k]['b']) - np.array(p[(k + 1) % len(p)]['a']))) <= 1.5 for k in range(len(p)))
    return sum(1 for p in P if p and not p[0].get('hole') and all(s['state'] not in ('short', 'not on a line', 'on rail') and not s.get('paper_edge') for s in p) and j(p))
res['intact_rings_recount'] = {f'grid{k}': dict(recount=intact(json.load(open(V + f'staged_runs/staged__grid{k}/outlines.json'))),
                                                staged_bench=json.load(open(V + f'staged_runs/staged__grid{k}/bench44.json'))['headline']['all']['intact_rings'],
                                                orig_bench_old_rule=json.load(open(V + f'orig/runs/merged__grid{k}/bench44.json'))['headline']['all']['intact_rings']) for k in range(6)}
json.dump(res, open(V + 'rail_rings44.json', 'w'), indent=1); print(json.dumps(res, indent=1))
