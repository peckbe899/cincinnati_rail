"""CPU only, read-only: lines_ng1 on the top half of the earlier 44 region (y 0:1664, x 0:6656) with an oracle 7th channel
(44_label.png: block 255, street 0, unlabelled -> area_ng1's own value), against the saved deployed-channel run; and a
tile-size check (2048 vs 1024) on y 0:1664, x 0:2496."""
import sys, time, os, json
OUT = sys.argv[1]
sys.argv = [sys.argv[0], '--no-guide', '--area', 'area_ng1']
sys.path.insert(0, 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet')
import numpy as np, cv2, torch
torch.set_num_threads(6)
import edgenet as E
net = E.UNet(classes=2, in_ch=7); net.load_state_dict(torch.load(E.DATA + 'models/lines_ng1.pt', map_location='cpu', weights_only=False)); net.eval()
x, t, _ = E.load('44'); H, W = t.shape; C = 96; res = {}
def run(xr, Y0, Y1, X0, X1, tile=1024, pad=96):
    ys, xs = max(0, Y0 - C), max(0, X0 - C); ye, xe = min(H, Y1 + C), min(W, X1 + C)
    p = E.predict_full(net, 'cpu', np.ascontiguousarray(xr[ys:ye, xs:xe]), tile=tile, pad=pad)
    return p[Y0 - ys:Y0 - ys + (Y1 - Y0), X0 - xs:X0 - xs + (X1 - X0)]
lab = cv2.imread(E.DATA + '44_label.png', 0); pa = cv2.imread(E.DATA + '44_pred_area_ng1.png', 0)
o = np.where(lab == 1, 255, np.where(lab == 0, 0, pa)).astype(np.uint8)
xo = x[:1664 + C, :6656 + C].copy(); xo[:, :, 6] = cv2.resize(o, (W, H), interpolation=cv2.INTER_LINEAR)[:1664 + C, :6656 + C]
t1 = time.time(); po = run(xo, 0, 1664, 0, 6656); tr = t[:1664, :6656]
pd = np.load(os.path.join(OUT, 'ng1_44_area.npy'))[:1664, :6656].astype(np.float32) / 255
res['oracle'] = E.score(po, tr); res['deployed_area_same_region'] = E.score(pd, tr); res['oracle_seconds'] = round(time.time() - t1)
print(json.dumps(res), flush=True)
t1 = time.time(); p2 = run(x, 0, 1664, 0, 2496, tile=2048); p1 = pd[:, :2496]
res['tile2048_vs_1024'] = dict(mean_abs_diff=round(float(np.abs(p2 - p1).mean()), 5), flipped=int(((p2 > 0.5) != (p1 > 0.5)).sum()), drawn_1024=int((p1 > 0.5).sum()),
                               score_2048=E.score(p2, tr[:, :2496]), score_1024=E.score(p1, tr[:, :2496]), seconds=round(time.time() - t1))
print(json.dumps(res['tile2048_vs_1024']), flush=True)
json.dump(res, open(os.path.join(OUT, 'ng1_oracle.json'), 'w'), indent=1)
