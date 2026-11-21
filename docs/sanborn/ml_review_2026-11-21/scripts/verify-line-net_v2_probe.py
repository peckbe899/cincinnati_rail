"""CPU only, read-only. lines_ng1 on a sub-region of held-out plate 44: channel-7 variants and tiling variants.
usage: v2_probe.py VARIANTS   (comma list of: area, none, oracle, shift, pad192, tile2048)
All variants are scored on the same INNER box, which is >= 250 px from the sub-region's border (so reflect padding at the
sub-region border does not reach it; the receptive field is ~170 px)."""
import sys, time, os, json
VARS = sys.argv[1].split(',')
S = 'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/verify-line-net/'
sys.argv = [sys.argv[0], '--no-guide', '--area', 'area_ng1']
sys.path.insert(0, 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet')
import numpy as np, cv2, torch
torch.set_num_threads(8)
import edgenet as E
assert E.NOGUIDE and E.AREA == 'area_ng1'
net = E.UNet(classes=2, in_ch=7); net.load_state_dict(torch.load(E.DATA + 'models/lines_ng1.pt', map_location='cpu', weights_only=False)); net.eval()
# channel 7 from the scratch snapshot (identical to the repo file at the time of training; the batch may rewrite it)
E.DATA_SNAP = S + 'snap/'
x, t, _ = E.load('44'); H, W = t.shape
snap = cv2.imread(S + 'snap/44_pred_area_ng1.png', 0); x[:, :, 6] = cv2.resize(snap, (W, H), interpolation=cv2.INTER_LINEAR)
Y0, Y1, X0, X1 = 600, 2400, 1800, 4500           # sub-region
IY0, IY1, IX0, IX1 = 850, 2150, 2050, 4250       # inner box, scored
sub = np.ascontiguousarray(x[Y0:Y1, X0:X1]); tin = t[IY0:IY1, IX0:IX1]
def inner(p, oy=Y0, ox=X0): return p[IY0 - oy:IY1 - oy, IX0 - ox:IX1 - ox]
res = {}; base = None
fn = S + 'v2_area_inner.npy'
if os.path.exists(fn): base = np.load(fn).astype(np.float32) / 255
for v in VARS:
    t1 = time.time()
    if v == 'area': p = inner(E.predict_full(net, 'cpu', sub)); np.save(fn, (p * 255).astype(np.uint8)); base = p
    elif v == 'none': s2 = sub.copy(); s2[:, :, 6] = 128; p = inner(E.predict_full(net, 'cpu', s2))
    elif v == 'oracle':
        lab = cv2.imread(E.DATA + '44_label.png', 0); o = np.where(lab == 1, 255, np.where(lab == 0, 0, snap)).astype(np.uint8)
        s2 = sub.copy(); s2[:, :, 6] = cv2.resize(o, (W, H), interpolation=cv2.INTER_LINEAR)[Y0:Y1, X0:X1]; p = inner(E.predict_full(net, 'cpu', s2))
    elif v == 'shift':     # same tiles, grid moved by half a step (416 px): only seam positions change
        s2 = np.ascontiguousarray(x[Y0 - 416:Y1, X0 - 416:X1]); p = inner(E.predict_full(net, 'cpu', s2), Y0 - 416, X0 - 416)
    elif v == 'pad192': p = inner(E.predict_full(net, 'cpu', sub, tile=1024, pad=192))
    elif v == 'tile2048': p = inner(E.predict_full(net, 'cpu', sub, tile=2048, pad=96))
    r = dict(score=E.score(p, tin), drawn_px=int((p > 0.5).sum()))
    if base is not None and v != 'area':
        r['flipped_vs_area'] = int(((p > 0.5) != (base > 0.5)).sum()); r['flipped_share_of_area_drawn'] = round(r['flipped_vs_area'] / max(1, int((base > 0.5).sum())), 4)
        r['mean_abs_diff'] = round(float(np.abs(p - base).mean()), 5)
    r['seconds'] = round(time.time() - t1); res[v] = r; print(v, json.dumps(r), flush=True)
old = json.load(open(S + 'v2_probe.json')) if os.path.exists(S + 'v2_probe.json') else {}
old.update(res); json.dump(old, open(S + 'v2_probe.json', 'w'), indent=1)
