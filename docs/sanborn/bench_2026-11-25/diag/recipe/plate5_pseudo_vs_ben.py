"""V2 trained plate 5 on pseudo labels taken from the batch. Ben has now checked 5 (edges_ben.json, saved 25 Nov). How
did V2's line target for 5 (train_v2/5/lines.png: 1 line, 0 not, 255 unscored) treat the lines he deleted as wrong,
and the lines he kept or added? Each line sampled every 2 px; a sample counts as taught positive if lines.png is 1
within 2 px, else negative if 0 at the point, else unscored. Also 1A's target (train_v2/1A/lines.png, V1 and V2):
the same for his wrong lines there. Reads only (edges_ben.json is read, never written); system python."""
import json, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; OUT = SP + 'bench_2026-11-25/diag/recipe/'
res = {}
for p in ['5', '1A']:
    B = json.load(open(SP + f'picks22_guided/22-{p}/edges_ben.json', encoding='utf8')); t = cv2.imread(SP + f'train_v2/{p}/lines.png', 0); H, W = t.shape
    pos = cv2.dilate((t == 1).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    g = {}
    for l in B['lines']:
        k = 'wrong' if l.get('verdict') == 'wrong' else ('added' if l.get('added') else 'kept')
        a, b = np.array(l['a'], float), np.array(l['b'], float); L = np.hypot(*(b - a)); n = max(2, int(L / 2)); q = a + np.outer(np.linspace(0, 1, n), b - a)
        x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1)
        isp = pos[y, x]; isn = ~isp & (t[y, x] == 0); isu = ~isp & ~isn
        r = g.setdefault(k, dict(lines=0, length=0.0, pos=0.0, neg=0.0, unscored=0.0, lines_mostly_pos=0))
        r['lines'] += 1; r['length'] += L; r['pos'] += L * isp.mean(); r['neg'] += L * isn.mean(); r['unscored'] += L * isu.mean(); r['lines_mostly_pos'] += int(isp.mean() > 0.5)
    for r in g.values():
        for k in ('pos', 'neg', 'unscored'): r[k + '_share'] = round(r[k] / max(1, r['length']), 3)
        r['length'] = round(r['length'])
        for k in ('pos', 'neg', 'unscored'): r.pop(k)
    res[p] = dict(saved_at=B.get('saved_at'), by_verdict=g); print(p, json.dumps(res[p]), flush=True)
json.dump(res, open(OUT + 'plate5_pseudo_vs_ben.json', 'w'), indent=1)
