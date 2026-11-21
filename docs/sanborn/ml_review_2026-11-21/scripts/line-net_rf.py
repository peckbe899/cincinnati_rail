"""CPU only: effective receptive field of lines_ng1 (gradient of the centre output wrt the input, real 44 crop) and the
per-channel share of the input gradient (how much the output leans on each of the 7 channels)."""
import sys, json
sys.argv = [sys.argv[0], '--no-guide', '--area', 'area_ng1']
sys.path.insert(0, 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet')
import numpy as np, cv2, torch
torch.set_num_threads(4)
import edgenet as E
net = E.UNet(classes=2, in_ch=7); net.load_state_dict(torch.load(E.DATA + 'models/lines_ng1.pt', map_location='cpu', weights_only=False)); net.eval()
full = cv2.imread(E.SP + 'cufp/22-44.jpg'); inkimg, _ = E.ink_image(full[1000:1448 + 400, 1500:1948 + 400])
pa = cv2.imread(E.DATA + '44_pred_area_ng1.png', 0); pa = cv2.resize(pa, (full.shape[1], full.shape[0]), interpolation=cv2.INTER_LINEAR)
res = {}
for (y0, x0) in ((1000, 1500), (1200, 1700), (1400, 1900)):
    S = 448; c = full[y0:y0 + S, x0:x0 + S]; ik, _ = E.ink_image(c)
    x = np.dstack([c[:, :, ::-1], ik, np.zeros((S, S), np.uint8), np.zeros((S, S), np.uint8), pa[y0:y0 + S, x0:x0 + S]])
    xt = E.norm(x[None]).requires_grad_(True)
    out = net(xt); F = torch.nn.functional
    pr = F.softmax(out, 1)[0, 1]
    # take the 32 most line-like pixels near the centre and sum their logits
    lg = (out[0, 1] - out[0, 0]); cen = lg[S // 2 - 48:S // 2 + 48, S // 2 - 48:S // 2 + 48]
    cen.sum().backward()
    g = xt.grad[0].abs().numpy()
    tot = g.sum(); share = (g.sum((1, 2)) / tot).round(4).tolist()
    gm = g.sum(0); yy, xx = np.mgrid[:S, :S]; r = np.maximum(np.abs(yy - S / 2), np.abs(xx - S / 2)) - 48
    rad = {f'{q}': int(np.min([k for k in range(0, S // 2) if gm[r <= k].sum() >= q * gm.sum()])) for q in (0.9, 0.99)}
    res[f'{y0},{x0}'] = dict(channel_grad_share=dict(zip(['R', 'G', 'B', 'ink', 'guide_edge', 'guide_centre', 'area'], share)), radius_beyond_centre_box_px=rad)
    print(json.dumps(res[f'{y0},{x0}']), flush=True)
json.dump(res, open('C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/line-net/rf.json', 'w'), indent=1)
