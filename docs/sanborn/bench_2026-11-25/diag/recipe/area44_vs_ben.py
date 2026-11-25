"""The area maps of each pair on plate 44 against Ben's own ground (bench44's decided ground: his closed blocks = block,
the street ground between them = street; the cached decided_half_*.png of the baseline runs), mean over the 6 grids.
No outline step involved: this is the area network alone. Reads only; system python."""
import json, glob, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; EV = SP + 'train_v2_runs/eval/'; OUT = SP + 'bench_2026-11-25/diag/recipe/'
dec = cv2.imread(glob.glob(SP + 'bench_2026-11-23/train/integrate/round2/driver_mini/eval/runs_baseline44/cache/decided_half_*.png')[0], 0) > 0; h, w = dec.shape
T = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8')); tb = np.zeros((h, w), np.uint8)
for b in T['blocks']: cv2.fillPoly(tb, [(np.array(b['ring']) / 2).round().astype(np.int32)], 1)
blk = tb == 1; st = dec & ~blk
res = dict(ben_block_px=int(blk.sum()), ben_street_px=int(st.sum()))
for s in ['baseline', 'V1S1', 'V2S1', 'V1S2', 'V2S2']:
    rr = []
    for g in range(6):
        p = cv2.imread(EV + f'{s}/maps44/grid{g}/44_area.png', 0)
        if p.shape != (h, w): p = cv2.resize(p, (w, h), interpolation=cv2.INTER_NEAREST)
        p = p > 127
        rr.append([float((~p & st).sum() / max(1, ((~p) & (st | blk) | st).sum())), float(p[st].mean()), float((~p)[blk].mean()), float(((p & blk).sum() + (~p & st).sum()) / (blk.sum() + st.sum()))])
    m = np.mean(rr, 0); res[s] = dict(iou_street=round(m[0], 4), street_called_block=round(m[1], 4), block_called_street=round(m[2], 4), accuracy=round(m[3], 4))
    print(s, res[s], flush=True)
json.dump(res, open(OUT + 'area44_vs_ben.json', 'w'), indent=1)
