"""The ground of 44 Ben's map leaves undecided (paper outside bench44's decided ground: the Mill Creek valley, the
railways, the canal bed, the estates): how much of it each area net calls block, and into how many pieces the block
ground there falls (4-connected pieces of P(block) > 0.5 of at least 1500 half px, i.e. MIN_AREA 6000 full px), mean
over the 6 grids. Also the old 44 label (21 Nov) there. Reads only; system python."""
import json, glob, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; EV = SP + 'train_v2_runs/eval/'; OUT = SP + 'bench_2026-11-25/diag/recipe/'
dec = cv2.imread(glob.glob(SP + 'bench_2026-11-23/train/integrate/round2/driver_mini/eval/runs_baseline44/cache/decided_half_*.png')[0], 0) > 0; h, w = dec.shape
al = cv2.resize(np.load(SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32), (w, h)) > 0.5; und = al & ~dec
lab = cv2.imread(SP + 'unet_data/44_label.png', 0)
res = dict(undecided_share_of_paper=round(float(und.sum() / al.sum()), 3), old_label_in_undecided=dict(block=round(float((lab[und] == 1).mean()), 3), street=round(float((lab[und] == 0).mean()), 3), untaught=round(float((lab[und] == 255).mean()), 3)))
for s in ['baseline', 'V1S1', 'V2S1', 'V1S2', 'V2S2']:
    rr = []
    for g in range(6):
        p = cv2.imread(EV + f'{s}/maps44/grid{g}/44_area.png', 0) > 127
        b = (p & und).astype(np.uint8); n, cc, st, _ = cv2.connectedComponentsWithStats(b, connectivity=4)
        rr.append([float(p[und].mean()), int((st[1:, cv2.CC_STAT_AREA] >= 1500).sum())])
    m = np.mean(rr, 0); res[s] = dict(block_share_undecided=round(m[0], 4), pieces_ge1500=round(m[1], 1)); print(s, res[s], flush=True)
print(json.dumps(res)); json.dump(res, open(OUT + 'openland44.json', 'w'), indent=1)
