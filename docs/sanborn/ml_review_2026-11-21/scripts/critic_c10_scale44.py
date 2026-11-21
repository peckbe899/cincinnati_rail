"""Scale sensitivity of area_ng1 on held-out plate 44 (CPU only, never imports torch_directml or repo modules).
Plate 44 is at the training scale (~200 ft/in). Resampling its half-size image by s simulates a plate at 200/s ft per inch:
s=0.5 ~ the 400 ft sheets (46-50), s=2 ~ the 100 ft cut plates (1A, 5, 10, 53). The prediction is mapped back and
scored against 44_label.png as unet.score does (accuracy, iou_street over labelled pixels)."""
import sys, time, json, os
import numpy as np, cv2, torch, torch.nn as nn, torch.nn.functional as F
torch.set_num_threads(4)
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
def block(i, o): return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.GroupNorm(8, o), nn.ReLU(inplace=True), nn.Conv2d(o, o, 3, padding=1), nn.GroupNorm(8, o), nn.ReLU(inplace=True))
class UNet(nn.Module):            # copied from unet.py:36-50
    def __init__(self, classes=3, base=32, depth=4, in_ch=5):
        super().__init__(); ch = [base * 2 ** k for k in range(depth + 1)]
        self.down = nn.ModuleList([block(in_ch if k == 0 else ch[k - 1], ch[k]) for k in range(depth + 1)])
        self.up = nn.ModuleList([nn.ConvTranspose2d(ch[k + 1], ch[k], 2, stride=2) for k in range(depth)])
        self.dec = nn.ModuleList([block(2 * ch[k], ch[k]) for k in range(depth)]); self.out = nn.Conv2d(base, classes, 1)
    def forward(self, x):
        skips = []
        for k, d in enumerate(self.down): x = d(x if k == 0 else F.max_pool2d(x, 2)); skips.append(x)
        for k in reversed(range(len(self.up))): x = self.dec[k](torch.cat([self.up[k](x), skips[k]], 1))
        return self.out(x)
def norm(a): return torch.from_numpy(np.ascontiguousarray(a.transpose(0, 3, 1, 2))).float() / 255.0
def predict_full(net, img, tile=768, pad=64):   # copied from unet.py:75-89 (area output only)
    h, w = img.shape[:2]; out = np.zeros((h, w), np.float32); step = tile - 2 * pad
    im = cv2.copyMakeBorder(img, pad, pad + tile, pad, pad + tile, cv2.BORDER_REFLECT)
    with torch.no_grad():
        for y in range(0, h, step):
            for x in range(0, w, step):
                o = net(norm(im[None, y:y + tile, x:x + tile]))
                p = F.softmax(o[:, :2], 1)[0, 1].numpy()[pad:pad + step, pad:pad + step]
                out[y:y + step, x:x + step] = p[:min(step, h - y), :min(step, w - x)]
    return out
net = UNet(); net.load_state_dict(torch.load(D + 'models/area_ng1.pt', map_location='cpu')); net.eval()
img = cv2.imread(D + '44_img.jpg')[:, :, ::-1]; lab = cv2.imread(D + '44_label.png', 0); h, w = lab.shape
# a central window keeps the s=2 run short; every scale is scored on the same window
y0, y1, x0, x1 = h // 4, h // 4 + 1800, w // 4, w // 4 + 2700
res = {}
for s in (1.0, 0.5, 2.0):
    t0 = time.time(); src = img[y0:y1, x0:x1]
    a = src if s == 1 else cv2.resize(src, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    z = np.zeros(a.shape[:2], np.uint8); p = predict_full(net, np.dstack([a, z, z]))
    p = cv2.resize(p, (x1 - x0, y1 - y0), interpolation=cv2.INTER_LINEAR)
    L = lab[y0:y1, x0:x1]; m = L != 255; pr = p[m] > 0.5; gt = L[m] == 1
    iou = lambda u, v: float((u & v).sum() / max(1, (u | v).sum()))
    res[s] = dict(ft_per_inch_simulated=round(200 / s), accuracy=round(float((pr == gt).mean()), 4), iou_street=round(iou(~pr, ~gt), 4), iou_block=round(iou(pr, gt), 4),
                  pred_block_share=round(float(pr.mean()), 3), unsure=round(float(((p[m] > 0.1) & (p[m] < 0.9)).mean()), 3), seconds=round(time.time() - t0))
    print(s, res[s], flush=True)
json.dump(res, open(os.path.dirname(os.path.abspath(__file__)) + '/scale44.json', 'w'), indent=1)
