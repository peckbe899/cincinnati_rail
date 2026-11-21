# CPU only; no repo imports (no device code), reads repo files only.
import time, numpy as np, cv2, torch, torch.nn as nn, torch.nn.functional as F
torch.set_num_threads(6)
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
def block(i, o): return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.GroupNorm(8, o), nn.ReLU(inplace=True), nn.Conv2d(o, o, 3, padding=1), nn.GroupNorm(8, o), nn.ReLU(inplace=True))
class UNet(nn.Module):
    def __init__(self, classes=3, base=32, depth=4, in_ch=5):
        super().__init__(); ch = [base * 2 ** k for k in range(depth + 1)]
        self.down = nn.ModuleList([block(in_ch if k == 0 else ch[k - 1], ch[k]) for k in range(depth + 1)])
        self.up = nn.ModuleList([nn.ConvTranspose2d(ch[k + 1], ch[k], 2, stride=2) for k in range(depth)])
        self.dec = nn.ModuleList([block(2 * ch[k], ch[k]) for k in range(depth)]); self.out = nn.Conv2d(base, classes, 1)
    def forward(self, x):
        s = []
        for k, d in enumerate(self.down): x = d(x if k == 0 else F.max_pool2d(x, 2)); s.append(x)
        for k in reversed(range(len(self.up))): x = self.dec[k](torch.cat([self.up[k](x), s[k]], 1))
        return self.out(x)
net = UNet(); net.load_state_dict(torch.load(U + 'models/area_ng1.pt', map_location='cpu')); net.eval()
def P(t):
    with torch.no_grad(): return F.softmax(net(torch.from_numpy(np.ascontiguousarray(t.transpose(2,0,1))[None]).float()/255)[:, :2], 1)[0, 1].numpy()
img = cv2.imread(U + '44_img.jpg')[:, :, ::-1]; z = np.zeros(img.shape[:2], np.uint8); X = np.dstack([img, z, z]); lab = cv2.imread(U + '44_label.png', 0)
t0 = time.time()
# (a) GroupNorm far-context: tiles at positions not used by the reviewer
print('(a) replace content >=136 px from centre 256x256 with paper / 255 guide box (train-only pattern)')
for yy, xx in [(1900, 1000), (300, 4200), (2600, 2200)]:
    t = X[yy:yy+768, xx:xx+768].copy(); base = P(t)[256:512, 256:512]
    paper = np.median(t[:, :, :3].reshape(-1, 3), 0); t2 = t.copy(); mk = np.ones((768, 768), bool); mk[120:648, 120:648] = False; t2[mk, :3] = paper
    p2 = P(t2)[256:512, 256:512]
    t3 = t.copy(); t3[0:160, 0:160, 3:] = 255; p3 = P(t3)[256:512, 256:512]
    t4 = t.copy(); t4[304:464, 304:464, 3:] = 255; p4 = P(t4)[256:512, 256:512]
    f = lambda q: (round(float(np.abs(q-base).mean()),4), round(float(((q>.5)!=(base>.5)).mean()),4))
    print(f'  tile {yy},{xx}: ring->paper {f(p2)}  corner 255 box {f(p3)}  centre 255 box {f(p4)}')
print('  time', round(time.time()-t0)); t0 = time.time()
# (b) tile size: 384/64 (training crop size) vs stored 768/64 on a sub-region
y0, y1, x0, x1 = 640, 1920, 1280, 3200
def tiled(tile, pad):
    step = tile - 2*pad; h, w = X.shape[:2]; im = cv2.copyMakeBorder(X, pad, pad+tile, pad, pad+tile, cv2.BORDER_REFLECT); out = np.full((h, w), np.nan, np.float32)
    for y in range(0, h, step):
        if y+step <= y0 or y >= y1: continue
        for x in range(0, w, step):
            if x+step <= x0 or x >= x1: continue
            p = P(im[y:y+tile, x:x+tile])[pad:pad+step, pad:pad+step]; out[y:y+step, x:x+step] = p[:min(step, h-y), :min(step, w-x)]
    return out[y0:y1, x0:x1]
A = cv2.imread(U + '44_pred_area_ng1.png', 0).astype(np.float32)[y0:y1, x0:x1] / 255
L = lab[y0:y1, x0:x1]; m = L != 255
acc = lambda Q: round(float(((Q[m] > .5) == (L[m] == 1)).mean()), 4)
S = tiled(384, 64); print('(b) region acc stored 768/64', acc(A), ' 384/64', acc(S), ' differ', round(float(((S>.5)!=(A>.5)).mean()),4), ' time', round(time.time()-t0))
