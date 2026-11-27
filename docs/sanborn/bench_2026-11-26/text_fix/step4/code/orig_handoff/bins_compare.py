"""bins_compare.py (text_v1/handoff, 26 Nov 2026): plate 44's ink bins with the text mask taken first, against the sort made
with Ben's street map (unet_data/44_bins.png, read only; runs/bins/44_map_ben_before.png is the same, 0 px differ).
    cd data/sanborn; python -B bench_2026-11-25/text_v1/handoff/code/bins_compare.py
1. What moved, by bin: R = the map sort (Ben's map, Ben's rail), X = the same with the mask first (44_map_ben_after); the
   10 x 10 table of ink px (0 = ink left unsorted: pieces under 6 px, as ink_bins.py leaves them).
2. The sort without truth (44_nets44: the outline step's own lines and blocks, rail off) against the map sort (44_map, rail
   off), per bin, before and after the mask (the after nets sort against the after map sort).
3. Eye-check sheets: for each of the biggest moves in 1, 16 moved pieces drawn pixel-weighted at random (seed 0), each cut
   out of the scan (left) and shown with R (middle) and X (right); handoff/pics/bins44_<from>to<to>.png.
Writes handoff/scores/bins44.json and bins44.txt."""
import json, os
import numpy as np, cv2
SP = os.getcwd().replace('\\', '/') + '/'; HO = SP + 'bench_2026-11-25/text_v1/handoff/'; RU = HO + 'runs/bins/'
NAMES = {0: 'unsorted speck', 1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text', 9: 'not sorted'}
COL = {1: (0, 150, 0), 2: (255, 140, 0), 3: (20, 70, 120), 4: (0, 0, 230), 5: (0, 150, 255), 6: (160, 0, 0), 7: (160, 170, 0), 8: (255, 0, 255), 9: (120, 120, 120)}
R = cv2.imread(SP + 'unet_data/44_bins.png', 0); X = cv2.imread(RU + '44_map_ben_after.png', 0); B0 = cv2.imread(RU + '44_map_ben_before.png', 0)
assert int((R != B0).sum()) == 0, 'the before run does not reproduce unet_data/44_bins.png'
im = cv2.imread(SP + 'cufp/22-44.jpg'); ink = (cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0] < 140)
m = (R > 0) | (X > 0); T = np.bincount(R[m].astype(np.int64) * 10 + X[m], minlength=100).reshape(10, 10)
out = dict(table_R_rows_X_cols=T.tolist(), names=NAMES, bins={})
L = ['1. Plate 44, map sort (Ben map + Ben rail) -> the same with the text mask first. px; rows = before, cols = after']
for k in range(10):
    if T[k].sum() == 0 and T[:, k].sum() == 0: continue
    to = {NAMES[j]: int(T[k, j]) for j in np.argsort(-T[k]) if j != k and T[k, j] >= 500}
    fr = {NAMES[j]: int(T[j, k]) for j in np.argsort(-T[:, k]) if j != k and T[j, k] >= 500}
    out['bins'][NAMES[k]] = dict(before=int(T[k].sum()), after=int(T[:, k].sum()), change=int(T[:, k].sum() - T[k].sum()), change_pct=round(100 * float(T[:, k].sum() - T[k].sum()) / max(1, T[k].sum()), 2), kept=int(T[k, k]), to=to, from_=fr)
    o = out['bins'][NAMES[k]]; L.append(f"  {NAMES[k]:16s} {o['before']:9d} -> {o['after']:9d} ({o['change']:+8d}, {o['change_pct']:+6.2f}%) | out: {to} | in: {fr}")
moved = int(m.sum() - np.trace(T)); out['moved_px'] = moved; out['ink_px'] = int(m.sum()); L.append(f'  moved {moved:,} of {int(m.sum()):,} px ({100 * moved / m.sum():.2f}%)')
# 2. the sort without truth against the map sort, before and after
L.append('2. Plate 44, sort without truth (outline step\'s own blocks, grid 0; rail off) against the map sort (rail off): share of each map-sort bin the no-truth sort puts in the same bin')
out['nets_vs_map'] = {}
for when in ('before', 'after'):
    M = cv2.imread(RU + f'44_map_{when}.png', 0); Nn = cv2.imread(RU + f'44_nets44_{when}.png', 0); mm = M > 0
    T2 = np.bincount(M[mm].astype(np.int64) * 10 + Nn[mm], minlength=100).reshape(10, 10)
    o = dict(all_ink_same_bin=round(float(np.trace(T2[1:, 1:]) / max(1, T2[1:, 1:].sum())), 4), **{NAMES[k]: round(float(T2[k, k] / max(1, T2[k].sum())), 4) for k in (1, 2, 3, 6, 7, 8)})
    out['nets_vs_map'][when] = o; L.append(f'  {when:6s} ' + ' | '.join(f'{k} {v}' for k, v in o.items()))
# 3. eye-check sheets of the biggest moves
rng = np.random.default_rng(0); sheets = []
pairs = sorted(((int(T[a, b]), a, b) for a in range(1, 10) for b in range(0, 10) if a != b and T[a, b] >= 3000), reverse=True)[:8]
for cnt, a, b in pairs:
    mv = ((R == a) & (X == b)).astype(np.uint8); n, lb, st, cs = cv2.connectedComponentsWithStats(mv, connectivity=8)
    if n <= 1: continue
    w = st[1:, 4].astype(float); pick = rng.choice(np.arange(1, n), size=min(16, n - 1), replace=False, p=w / w.sum())
    tiles = []
    for i in pick:
        cx, cy = cs[i].round().astype(int); x0, y0 = max(0, cx - 45), max(0, cy - 45); x1, y1 = min(R.shape[1], cx + 45), min(R.shape[0], cy + 45)
        sc = im[y0:y1, x0:x1]
        def bp(Bm):
            c = (sc * 0.4 + 150).astype(np.uint8); s = Bm[y0:y1, x0:x1]
            for k, col in COL.items(): c[s == k] = col
            c[(lb[y0:y1, x0:x1] == i)] = (0, 255, 255) if False else c[(lb[y0:y1, x0:x1] == i)]
            return c
        t = np.hstack([sc, bp(R), bp(X)]); t = cv2.copyMakeBorder(cv2.resize(t, (270 * 2, 90 * 2), interpolation=cv2.INTER_NEAREST), 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(0, 0, 0))
        cv2.putText(t, f'{cx},{cy}', (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1); tiles.append(t)
    while len(tiles) % 2: tiles.append(np.full_like(tiles[0], 255))
    sheet = np.vstack([np.hstack(tiles[k:k + 2]) for k in range(0, len(tiles), 2)])
    f = HO + f'pics/bins44_{a}to{b}.png'; cv2.imwrite(f, sheet); sheets.append(dict(move=f'{NAMES[a]} -> {NAMES[b]}', px=cnt, sheet=os.path.basename(f), samples=[tuple(int(v) for v in cs[i].round()) for i in pick]))
out['eye_sheets'] = sheets
json.dump(out, open(HO + 'scores/bins44.json', 'w', encoding='utf8', newline='\n'), indent=1)
open(HO + 'scores/bins44.txt', 'w', encoding='utf8', newline='\n').write('\n'.join(L) + '\n'); print('\n'.join(L)); print(json.dumps(sheets, indent=0)[:3000])
