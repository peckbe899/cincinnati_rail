# CPU only. Copies the UNet definition from unet.py (lines 35-50) so nothing from the repo's device code runs.
import time, json, numpy as np, cv2, torch, torch.nn as nn, torch.nn.functional as F
torch.set_num_threads(6)
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
def block(i, o): return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.GroupNorm(8, o), nn.ReLU(inplace=True), nn.Conv2d(o, o, 3, padding=1), nn.GroupNorm(8, o), nn.ReLU(inplace=True))
class UNet(nn.Module):
    def __init__(self, classes=3, base=32, depth=4, in_ch=5):
        super().__init__()
        ch = [base * 2 ** k for k in range(depth + 1)]
        self.down = nn.ModuleList([block(in_ch if k == 0 else ch[k - 1], ch[k]) for k in range(depth + 1)])
        self.up = nn.ModuleList([nn.ConvTranspose2d(ch[k + 1], ch[k], 2, stride=2) for k in range(depth)])
        self.dec = nn.ModuleList([block(2 * ch[k], ch[k]) for k in range(depth)])
        self.out = nn.Conv2d(base, classes, 1)
    def forward(self, x):
        skips = []
        for k, d in enumerate(self.down):
            x = d(x if k == 0 else F.max_pool2d(x, 2)); skips.append(x)
        for k in reversed(range(len(self.up))):
            x = self.dec[k](torch.cat([self.up[k](x), skips[k]], 1))
        return self.out(x)
def norm(a): return torch.from_numpy(np.ascontiguousarray(a.transpose(0, 3, 1, 2))).float() / 255.0
net = UNet(); net.load_state_dict(torch.load(U + 'models/area_ng1.pt', map_location='cpu')); net.eval()
img = cv2.imread(U + '44_img.jpg')[:, :, ::-1]; z = np.zeros(img.shape[:2], np.uint8); X = np.dstack([img, z, z])
stored = cv2.imread(U + '44_pred_area_ng1.png', 0).astype(np.float32) / 255
pad, tile = 64, 768; step = tile - 2 * pad
im = cv2.copyMakeBorder(X, pad, pad + tile, pad, pad + tile, cv2.BORDER_REFLECT)
res = {}
with torch.no_grad():
    for (y, x) in [(640, 1280), (1920, 2560)]:
        t0 = time.time(); o = net(norm(im[None, y:y + tile, x:x + tile]))
        p = F.softmax(o[:, :2], 1)[0, 1].numpy()[pad:pad + step, pad:pad + step]; dt = time.time() - t0
        s = stored[y:y + step, x:x + step]
        res[f'tile {y},{x}'] = dict(sec=round(dt, 2), max_abs_diff=round(float(np.abs(p - s).max()), 4), mean_abs_diff=round(float(np.abs(p - s).mean()), 5), decision_flips=int(((p > 0.5) != (s > 0.5)).sum()))
print(json.dumps(res, indent=1))
