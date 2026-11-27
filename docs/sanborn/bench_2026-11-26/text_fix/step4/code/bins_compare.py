"""bins_compare.py (text_fix/step4, 27 Nov 2026): copy of text_v1/handoff/code/bins_compare.py for both mask sets, plus the
direct finder3 -> finder4 move table. Plate 44's ink bins with the text mask taken first, against the sort made with Ben's
street map (unet_data/44_bins.png, read only; runs/bins/<set>/44_map_ben_before.png must be the same, 0 px differ).
    cd data/sanborn; python -B bench_2026-11-26/text_fix/step4/code/bins_compare.py
For SET f3 and f4 (as the hand-off did for its one mask):
1. What moved, by bin: R = the map sort (Ben's map, Ben's rail), X = the same with the mask first (44_map_ben_after).
2. The sort without truth (44_nets44, rail off) against the map sort (44_map, rail off), per bin, before and after.
3. Eye-check sheets of the 8 biggest moves, 16 pieces each, pixel-weighted at random (seed 0): pics/bins/<set>/.
Then 'f3 -> f4': X(f3) against X(f4), every move of 500 px or more, with sheets of every move of 300 px or more in
pics/bins/f3_to_f4/ (16 pieces each, seed 0; scan | f3 sort | f4 sort).
Writes step4/scores/bins44.json and bins44.txt."""
import json, os
import numpy as np, cv2
SP = os.getcwd().replace('\\', '/') + '/'; ST = SP + 'bench_2026-11-26/text_fix/step4/'
NAMES = {0: 'unsorted speck', 1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text', 9: 'not sorted'}
COL = {1: (0, 150, 0), 2: (255, 140, 0), 3: (20, 70, 120), 4: (0, 0, 230), 5: (0, 150, 255), 6: (160, 0, 0), 7: (160, 170, 0), 8: (255, 0, 255), 9: (120, 120, 120)}
R = cv2.imread(SP + 'unet_data/44_bins.png', 0); im = cv2.imread(SP + 'cufp/22-44.jpg')


def table(R, X):
    m = (R > 0) | (X > 0); return np.bincount(R[m].astype(np.int64) * 10 + X[m], minlength=100).reshape(10, 10), m


def sheets(R, X, T, pairs, outdir, tag):
    os.makedirs(outdir, exist_ok=True); rng = np.random.default_rng(0); res = []
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
                return c
            t = np.hstack([sc, bp(R), bp(X)])
            if t.shape[:2] != (90, 270): t = cv2.copyMakeBorder(t, 0, 90 - t.shape[0], 0, 270 - t.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255))
            t = cv2.copyMakeBorder(cv2.resize(t, (270 * 2, 90 * 2), interpolation=cv2.INTER_NEAREST), 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(0, 0, 0))
            cv2.putText(t, f'{cx},{cy}', (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1); tiles.append(t)
        while len(tiles) % 2: tiles.append(np.full_like(tiles[0], 255))
        sheet = np.vstack([np.hstack(tiles[k:k + 2]) for k in range(0, len(tiles), 2)])
        f = outdir + f'{tag}_{a}to{b}.png'; cv2.imwrite(f, sheet)
        res.append(dict(move=f'{NAMES[a]} -> {NAMES[b]}', px=cnt, pieces=int(n - 1), sheet=os.path.relpath(f, ST).replace('\\', '/'), samples=[tuple(int(v) for v in cs[i].round()) for i in pick]))
    return res


out = {}; L = []; XS = {}
for S in ('f3', 'f4'):
    RU = ST + f'runs/bins/{S}/'
    X = cv2.imread(RU + '44_map_ben_after.png', 0); B0 = cv2.imread(RU + '44_map_ben_before.png', 0); XS[S] = X
    assert int((R != B0).sum()) == 0, 'the before run does not reproduce unet_data/44_bins.png'
    T, m = table(R, X); o = dict(table_R_rows_X_cols=T.tolist(), names=NAMES, bins={})
    L.append(f'[{S}] 1. Plate 44, map sort (Ben map + Ben rail) -> the same with the text mask first. px; rows = before, cols = after')
    for k in range(10):
        if T[k].sum() == 0 and T[:, k].sum() == 0: continue
        to = {NAMES[j]: int(T[k, j]) for j in np.argsort(-T[k]) if j != k and T[k, j] >= 500}
        fr = {NAMES[j]: int(T[j, k]) for j in np.argsort(-T[:, k]) if j != k and T[j, k] >= 500}
        o['bins'][NAMES[k]] = dict(before=int(T[k].sum()), after=int(T[:, k].sum()), change=int(T[:, k].sum() - T[k].sum()), change_pct=round(100 * float(T[:, k].sum() - T[k].sum()) / max(1, T[k].sum()), 2), kept=int(T[k, k]), to=to, from_=fr)
        b = o['bins'][NAMES[k]]; L.append(f"  {NAMES[k]:16s} {b['before']:9d} -> {b['after']:9d} ({b['change']:+8d}, {b['change_pct']:+6.2f}%) | out: {to} | in: {fr}")
    moved = int(m.sum() - np.trace(T)); o['moved_px'] = moved; o['ink_px'] = int(m.sum()); L.append(f'  moved {moved:,} of {int(m.sum()):,} px ({100 * moved / m.sum():.2f}%)')
    L.append(f'[{S}] 2. Plate 44, sort without truth (grid 0 blocks; rail off) against the map sort (rail off): share of each map-sort bin put in the same bin')
    o['nets_vs_map'] = {}
    for when in ('before', 'after'):
        M = cv2.imread(RU + f'44_map_{when}.png', 0); Nn = cv2.imread(RU + f'44_nets44_{when}.png', 0); mm = M > 0
        T2 = np.bincount(M[mm].astype(np.int64) * 10 + Nn[mm], minlength=100).reshape(10, 10)
        q = dict(all_ink_same_bin=round(float(np.trace(T2[1:, 1:]) / max(1, T2[1:, 1:].sum())), 4), **{NAMES[k]: round(float(T2[k, k] / max(1, T2[k].sum())), 4) for k in (1, 2, 3, 6, 7, 8)})
        o['nets_vs_map'][when] = q; L.append(f'  {when:6s} ' + ' | '.join(f'{k} {v}' for k, v in q.items()))
    pairs = sorted(((int(T[a, b]), a, b) for a in range(1, 10) for b in range(0, 10) if a != b and T[a, b] >= 3000), reverse=True)[:8]
    o['eye_sheets'] = sheets(R, X, T, pairs, ST + f'pics/bins/{S}/', 'bins44'); out[S] = o
# f3 -> f4
X3, X4 = XS['f3'], XS['f4']; T, m = table(X3, X4); moved = int(m.sum() - np.trace(T))
o = dict(table_f3_rows_f4_cols=T.tolist(), moved_px=moved, moves={})
L.append(f'[f3 -> f4] Plate 44, the masked map sort with finder3 against the same with finder4: moved {moved:,} px')
for a in range(10):
    for b in range(10):
        if a != b and T[a, b] >= 500: o['moves'][f'{NAMES[a]} -> {NAMES[b]}'] = int(T[a, b])
for k, v in sorted(o['moves'].items(), key=lambda kv: -kv[1]): L.append(f'  {k:32s} {v:8d} px')
for k in range(10):
    if T[k].sum() or T[:, k].sum(): L.append(f'  bin {NAMES[k]:16s} f3 {int(T[k].sum()):9d} -> f4 {int(T[:, k].sum()):9d} ({int(T[:, k].sum() - T[k].sum()):+d})')
pairs = sorted(((int(T[a, b]), a, b) for a in range(0, 10) for b in range(0, 10) if a != b and T[a, b] >= 300), reverse=True)
o['eye_sheets'] = sheets(X3, X4, T, pairs, ST + 'pics/bins/f3_to_f4/', 'f3f4'); out['f3_to_f4'] = o
json.dump(out, open(ST + 'scores/bins44.json', 'w', encoding='utf8', newline='\n'), indent=1)
open(ST + 'scores/bins44.txt', 'w', encoding='utf8', newline='\n').write('\n'.join(L) + '\n'); print('\n'.join(L))
for S in out: print(S, json.dumps([(s['move'], s['px'], s['pieces'], s['sheet']) for s in out[S]['eye_sheets']]))
