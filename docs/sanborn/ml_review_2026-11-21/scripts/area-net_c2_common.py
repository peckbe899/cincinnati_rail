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
lab = cv2.imread(U + '44_label.png', 0)
def tiled(X, tile, pad, y0, y1, x0, x1):
    """P(block) for rows y0:y1, cols x0:x1 of the plate, with the same tiling scheme as unet.predict_full run on the whole plate"""
    step = tile - 2 * pad; h, w = X.shape[:2]
    im = cv2.copyMakeBorder(X, pad, pad + tile, pad, pad + tile, cv2.BORDER_REFLECT); out = np.full((h, w), np.nan, np.float32)
    with torch.no_grad():
        for y in range(0, h, step):
            if y + step <= y0 or y >= y1: continue
            for x in range(0, w, step):
                if x + step <= x0 or x >= x1: continue
                o = net(norm(im[None, y:y + tile, x:x + tile]))
                p = F.softmax(o[:, :2], 1)[0, 1].numpy()[pad:pad + step, pad:pad + step]
                out[y:y + step, x:x + step] = p[:min(step, h - y), :min(step, w - x)]
    return out[y0:y1, x0:x1]
