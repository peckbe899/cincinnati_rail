"""CPU only, read-only: lines_ng1 on a region of held-out plate 44 with different 7th channels / tile sizes.
usage: ng1_region.py OUTDIR variant[,variant...]   variants: area (as deployed), none (=128), oracle (from 44_label.png),
       tile448, tile2048 (area channel, other tile sizes, on a sub-region)"""
import sys, time, os, json
OUT = sys.argv[1]; VARS = sys.argv[2].split(',')
sys.argv = [sys.argv[0], '--no-guide', '--area', 'area_ng1']
sys.path.insert(0, 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet')
import numpy as np, cv2, torch
torch.set_num_threads(6)
import edgenet as E
net = E.UNet(classes=2, in_ch=7); net.load_state_dict(torch.load(E.DATA + 'models/lines_ng1.pt', map_location='cpu', weights_only=False)); net.eval()
t0 = time.time(); x, t, _ = E.load('44'); H, W = t.shape; print('loaded', round(time.time() - t0), 's', x.shape, flush=True)
Y0, Y1, X0, X1 = 0, 3328, 0, 6656; C = 96
def run(xr, tile=1024, pad=96):
    ys, xs = max(0, Y0 - C), max(0, X0 - C); ye, xe = min(H, Y1 + C), min(W, X1 + C)
    p = E.predict_full(net, 'cpu', np.ascontiguousarray(xr[ys:ye, xs:xe]), tile=tile, pad=pad)
    return p[Y0 - ys:Y0 - ys + (Y1 - Y0), X0 - xs:X0 - xs + (X1 - X0)]
tr = t[Y0:Y1, X0:X1]; res = {}
for v in VARS:
    t1 = time.time(); xv = x
    if v == 'none':
        xv = x.copy(); xv[:, :, 6] = 128
    elif v == 'oracle':
        lab = cv2.imread(E.DATA + '44_label.png', 0); pa = cv2.imread(E.DATA + '44_pred_area_ng1.png', 0)
        o = np.where(lab == 1, 255, np.where(lab == 0, 0, pa)).astype(np.uint8)
        xv = x.copy(); xv[:, :, 6] = cv2.resize(o, (W, H), interpolation=cv2.INTER_LINEAR)
    if v.startswith('tile'):
        ts = int(v[4:]); sub = (slice(0, 1664), slice(0, 2496))
        Y1, X1 = 1664, 2496; p = run(x, tile=ts); pb = run(x, tile=1024); Y1, X1 = 3328, 6656
        res[v] = dict(tile=ts, mean_abs_diff_vs_1024=round(float(np.abs(p - pb).mean()), 5), px_flipped_at_05=int(((p > 0.5) != (pb > 0.5)).sum()),
                      share_flipped_of_drawn=round(float(((p > 0.5) != (pb > 0.5)).sum() / max(1, (pb > 0.5).sum())), 4),
                      score_tile=E.score(p, tr[:1664, :2496]), score_1024=E.score(pb, tr[:1664, :2496]))
    else:
        p = run(xv); np.save(os.path.join(OUT, f'ng1_44_{v}.npy'), (p * 255).astype(np.uint8))
        res[v] = dict(score=E.score(p, tr), sweep={str(th): E.score(np.where(p > th, 1.0, 0.0), tr) for th in (0.3, 0.7)})
    res[v]['seconds'] = round(time.time() - t1); print(v, json.dumps(res[v]), flush=True)
# lines_v2 (guided) on the same region, today's target
pv = cv2.imread(E.DATA + '44_lines_lines_v2.png', 0)[Y0:Y1, X0:X1].astype(np.float32) / 255
res['lines_v2_saved'] = E.score(pv, tr); print('lines_v2 saved', json.dumps(res['lines_v2_saved']))
json.dump(res, open(os.path.join(OUT, 'ng1_region_' + '_'.join(VARS) + '.json'), 'w'), indent=1)
