"""CPU-only (no DirectML) run of the saved lines_ng1 line network on plate 44, as blocks_noguide.py would feed it
(scan, ink image, blank guide, area_ng1's P(block)). Architecture copied from tools/sanborn/unet/unet.py:35-50 so that no
repo module is imported. Reads the repo, writes only into this scratch folder.
    python lines_ng1_cpu.py time      -> time one 1024 tile
    python lines_ng1_cpu.py run       -> whole plate -> 44_lines_lines_ng1_cpu.png here"""
import sys, time, os
import numpy as np, cv2, torch, torch.nn as nn, torch.nn.functional as F
torch.set_num_threads(8)
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = D + 'unet_data/'
OUT = os.path.dirname(os.path.abspath(__file__)) + '/44_lines_lines_ng1_cpu.png'

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

import torch._utils; torch.serialization.add_safe_globals([torch._utils._rebuild_device_tensor_from_numpy])   # the .pt was saved from DirectML tensors
net = UNet(classes=2, in_ch=7); net.load_state_dict(torch.load(U + 'models/lines_ng1.pt', map_location='cpu', weights_only=False)); net.eval()
full = cv2.imread(D + 'cufp/22-44.jpg'); H, W = full.shape[:2]
hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); gray = cv2.cvtColor(full, cv2.COLOR_BGR2GRAY)
ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170)); inkimg = np.where(ink, gray, 255).astype(np.uint8); del hsv, gray, ink
sp = cv2.resize(cv2.imread(U + '44_pred_area_ng1.png', 0), (W, H), interpolation=cv2.INTER_LINEAR); Z = np.zeros((H, W), np.uint8)
x = np.dstack([full[:, :, ::-1], inkimg, Z, Z, sp]); del sp, inkimg
tile, pad = 1024, 96; step = tile - 2 * pad
if sys.argv[1] == 'time':
    t0 = time.time()
    with torch.no_grad(): o = net(norm(x[None, 2000:2000 + tile, 3000:3000 + tile]))
    print('one tile', round(time.time() - t0, 2), 's; tiles in plate', ((H + step - 1) // step) * ((W + step - 1) // step)); sys.exit()
im = cv2.copyMakeBorder(x, pad, pad + tile, pad, pad + tile, cv2.BORDER_REFLECT); out = np.zeros((H, W), np.float32); t0 = time.time()
with torch.no_grad():
    for y in range(0, H, step):
        for xx in range(0, W, step):
            p = F.softmax(net(norm(im[None, y:y + tile, xx:xx + tile])), 1)[0, 1].numpy()[pad:pad + step, pad:pad + step]
            out[y:y + step, xx:xx + step] = p[:min(step, H - y), :min(step, W - xx)]
cv2.imwrite(OUT, (out * 255).astype(np.uint8)); print('wrote', OUT, round(time.time() - t0), 's', 'drawn share', round(float((out > 0.5).mean()), 4))
