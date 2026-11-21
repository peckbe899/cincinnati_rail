"""infer_lib: network inference for the blank-guide pair (area_ng1, lines_ng1) with test-time options (21 Nov 2026).

Run with the networks' venv python (torch 2.4.1, torch-directml). Nothing here writes into the repo:
- the network code is COPIED from the repo (unet.py:26-50 device/block/UNet, unet.py:73 norm, unet.py:75-89 and
  edgenet.py:67-75 predict_full, edgenet.py:37-40 ink_image), so importing it does not run _ws._mirror() or write
  __pycache__ under tools/. repro_batch44.py checks that these copies give the batch's own maps for 44.
- the weights are loaded exactly as blocks_noguide.py:63-65 loads them.

Options (all inference only, no training):
- tta: number of dihedral transforms averaged per tile, in probability space: 1 (none), 2 (id + h-flip),
  4 (id, h-flip, v-flip, transpose: the review's c_tta set), 8 (all rotations and flips). Training used all 8
  (unet.py:125-126, edgenet.py:100-101), so every transform is in the training distribution.
- blend: 'crop' (the repo: tile, hard-cropped centre, outer pad thrown away) or 'hann' (overlapping tiles, each
  weighted by a 2-D Hann window, then normalised by the summed weights).
- scale: the image is resampled by s before the network and the map is resampled back (cv2 INTER_LINEAR).
- pen: after resampling, a k x k max filter (pen = k > 0) makes every dark line about k - 1 px thinner, or a min filter
  (pen = -k) makes it thicker. Resampling by s changes the street widths AND the pen width together; this undoes the
  pen part.
"""
import os, sys, time
sys.dont_write_bytecode = True
import numpy as np
import cv2
import torch, torch.nn as nn, torch.nn.functional as F

REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
SP = REPO + 'data/sanborn/'; U = SP + 'unet_data/'
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'


# ---------------------------------------------------------------- copied from the repo (unchanged)
def device():                                                     # unet.py:26-32
    try:
        import torch_directml as d
        k = max(range(d.device_count()), key=lambda i: ('RX' in d.device_name(i)) + ('NVIDIA' in d.device_name(i)))
        print('device', d.device_name(k), file=sys.stderr, flush=True); return d.device(k)
    except Exception:
        return torch.device('cuda' if torch.cuda.is_available() else 'cpu')


def block(i, o): return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.GroupNorm(8, o), nn.ReLU(inplace=True), nn.Conv2d(o, o, 3, padding=1), nn.GroupNorm(8, o), nn.ReLU(inplace=True))
class UNet(nn.Module):                                            # unet.py:36-50
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


def norm(a): return torch.from_numpy(np.ascontiguousarray(a.transpose(0, 3, 1, 2))).float() / 255.0   # unet.py:73 / edgenet.py:65


def ink_image(bgr):                                               # edgenet.py:37-40
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV); gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170))
    return np.where(ink, gray, 255).astype(np.uint8), ink


def repo_predict_area(net, dev, img, tile=768, pad=64):           # unet.py:75-89 (P(block) only)
    h, w = img.shape[:2]; out = np.zeros((h, w), np.float32); step = tile - 2 * pad
    im = cv2.copyMakeBorder(img, pad, pad + tile, pad, pad + tile, cv2.BORDER_REFLECT)
    net.eval()
    with torch.no_grad():
        for y in range(0, h, step):
            for x in range(0, w, step):
                o = net(norm(im[None, y:y + tile, x:x + tile]).to(dev))
                p = F.softmax(o[:, :2], 1)[0, 1].cpu().numpy()[pad:pad + step, pad:pad + step]
                out[y:y + step, x:x + step] = p[:min(step, h - y), :min(step, w - x)]
    return out


def repo_predict_lines(net, dev, x, tile=1024, pad=96):           # edgenet.py:67-75
    h, w = x.shape[:2]; out = np.zeros((h, w), np.float32); step = tile - 2 * pad
    im = cv2.copyMakeBorder(x, pad, pad + tile, pad, pad + tile, cv2.BORDER_REFLECT); net.eval()
    with torch.no_grad():
        for y in range(0, h, step):
            for xx in range(0, w, step):
                p = F.softmax(net(norm(im[None, y:y + tile, xx:xx + tile]).to(dev)), 1)[0, 1].cpu().numpy()[pad:pad + step, pad:pad + step]
                out[y:y + step, xx:xx + step] = p[:min(step, h - y), :min(step, w - xx)]
    return out


def load_nets(dev=None, area='area_ng1', lines='lines_ng1'):
    """as blocks_noguide.py:63-65"""
    dev = dev if dev is not None else device()
    na = UNet(); na.load_state_dict(torch.load(U + f'models/{area}.pt', map_location='cpu')); na.to(dev)
    nl = UNet(classes=2, in_ch=7); nl.load_state_dict(torch.load(U + f'models/{lines}.pt', map_location='cpu')); nl.to(dev)
    na.eval(); nl.eval()
    return dev, na, nl


# ---------------------------------------------------------------- test-time options
# dihedral transforms of a (N, C, T, T) tensor: (k quarter turns, then flip of the last axis)
D4 = [(0, False), (0, True), (2, True), (1, False), (1, True), (2, False), (3, False), (3, True)]
TTA_SETS = {1: [(0, False)], 2: [(0, False), (0, True)],
            4: [(0, False), (0, True), (2, True), (3, True)],          # id, h-flip, v-flip (= rot180 + h-flip), transpose (= rot270 + h-flip; checked in repro_batch44.py)
            8: D4}


def fwd_t(x, k, f):
    y = torch.rot90(x, k, (2, 3)) if k else x
    return torch.flip(y, (3,)) if f else y


def inv_t(y, k, f):
    y = torch.flip(y, (3,)) if f else y
    return torch.rot90(y, -k, (2, 3)) if k else y


def prob_area(o): return F.softmax(o[:, :2], 1)[:, 1]
def prob_lines(o): return F.softmax(o, 1)[:, 1]


def run_tile(net, dev, tile_u8, prob, tta=1, batch=8):
    """tile_u8: T x T x C uint8. Returns T x T float32 probability, mean over the TTA set."""
    x = norm(tile_u8[None])                      # 1 x C x T x T, on the CPU
    ts = TTA_SETS[tta]; acc = None
    for s in range(0, len(ts), batch):
        part = ts[s:s + batch]
        xb = torch.cat([fwd_t(x, k, f) for k, f in part], 0).to(dev)
        with torch.no_grad():
            pb = prob(net(xb)).cpu()[:, None]
        for i, (k, f) in enumerate(part):
            p = inv_t(pb[i:i + 1], k, f)[0, 0]
            acc = p.clone() if acc is None else acc + p
    return (acc / len(ts)).numpy()


def predict(net, dev, img, prob, tile, pad, tta=1, blend='crop', batch=8, hann_step=None, offset=None):
    """img: h x w x C uint8 (already in the network's channel order). 'crop' with tta=1 is the repo's predict_full.
    offset (oy, ox): move the tile grid by that much (the image is reflected on the top and left first, and the map
    cropped back), to measure how much the answer depends on where the tiles happen to fall."""
    if offset and (offset[0] or offset[1]):
        oy, ox = offset; im2 = cv2.copyMakeBorder(img, oy, 0, ox, 0, cv2.BORDER_REFLECT)
        return predict(net, dev, im2, prob, tile, pad, tta, blend, batch, hann_step)[oy:, ox:]
    h, w = img.shape[:2]
    if blend == 'crop':
        out = np.zeros((h, w), np.float32); step = tile - 2 * pad
        im = cv2.copyMakeBorder(img, pad, pad + tile, pad, pad + tile, cv2.BORDER_REFLECT)
        for y in range(0, h, step):
            for x in range(0, w, step):
                p = run_tile(net, dev, im[y:y + tile, x:x + tile], prob, tta, batch)[pad:pad + step, pad:pad + step]
                out[y:y + step, x:x + step] = p[:min(step, h - y), :min(step, w - x)]
        return out
    # Hann: tiles every S px (default T/2), each weighted by a 2-D Hann window; the image is reflected by T on every
    # side so that every pixel gets the full set of overlapping tiles
    T = tile; S = hann_step or T // 2
    w1 = np.hanning(T + 2)[1:-1].astype(np.float32); win = np.outer(w1, w1) + 1e-6
    im = cv2.copyMakeBorder(img, T, T, T, T, cv2.BORDER_REFLECT)
    acc = np.zeros((h, w), np.float32); wsum = np.zeros((h, w), np.float32)
    for ty in range(-T + S, h, S):
        for tx in range(-T + S, w, S):
            p = run_tile(net, dev, im[ty + T:ty + 2 * T, tx + T:tx + 2 * T], prob, tta, batch)
            a0, b0 = max(ty, 0), min(ty + T, h); c0, d0 = max(tx, 0), min(tx + T, w)
            if a0 >= b0 or c0 >= d0: continue
            acc[a0:b0, c0:d0] += (p * win)[a0 - ty:b0 - ty, c0 - tx:d0 - tx]; wsum[a0:b0, c0:d0] += win[a0 - ty:b0 - ty, c0 - tx:d0 - tx]
    return acc / np.maximum(wsum, 1e-12)


def area_map(na, dev, full, scale=1.0, tta=1, blend='crop', tile=768, pad=64, batch=8, offset=None, pen=0):
    """P(block) at half size (W//2 x H//2), as blocks_noguide.py:38-39 makes it when scale=1, tta=1, blend='crop'.
    scale s: the half-size image is made at s times half size straight from the full scan, and the map is resized back."""
    H, W = full.shape[:2]; w2, h2 = W // 2, H // 2
    if scale == 1.0: img = cv2.resize(full, (w2, h2), interpolation=cv2.INTER_AREA)
    else:
        ws, hs = max(8, int(round(w2 * scale))), max(8, int(round(h2 * scale)))
        img = cv2.resize(full, (ws, hs), interpolation=cv2.INTER_AREA if ws < W else cv2.INTER_CUBIC)
    if pen > 0: img = cv2.dilate(img, np.ones((pen, pen), np.uint8))      # pen > 0: thinner pen (max filter: dark lines lose pen - 1 px)
    if pen < 0: img = cv2.erode(img, np.ones((-pen, -pen), np.uint8))     # pen < 0: thicker pen
    z = np.zeros(img.shape[:2], np.uint8)
    p = predict(na, dev, np.dstack([img[:, :, ::-1], z, z]), prob_area, tile, pad, tta, blend, batch, offset=offset)
    if p.shape != (h2, w2): p = cv2.resize(p, (w2, h2), interpolation=cv2.INTER_LINEAR)
    return p


def lines_map(nl, dev, full, pa_u8, scale=1.0, tta=1, blend='crop', tile=1024, pad=96, batch=4, offset=None, pen=0):
    """P(block line) at full size, as blocks_noguide.py:40-42 makes it when scale=1, tta=1, blend='crop'.
    pa_u8: the half-size P(block)*255 map (uint8), the 7th input. scale s: the scan is resampled by s, the ink image is
    made from the resampled scan, the area map is resized to it, and the line map is resized back to full size."""
    H, W = full.shape[:2]
    if scale == 1.0: f = full
    else:
        ws, hs = int(round(W * scale)), int(round(H * scale))
        f = cv2.resize(full, (ws, hs), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
    if pen > 0: f = cv2.dilate(f, np.ones((pen, pen), np.uint8))
    if pen < 0: f = cv2.erode(f, np.ones((-pen, -pen), np.uint8))
    h, w = f.shape[:2]
    inkimg, _ = ink_image(f); Z = np.zeros((h, w), np.uint8)
    x = np.dstack([f[:, :, ::-1], inkimg, Z, Z, cv2.resize(pa_u8, (w, h), interpolation=cv2.INTER_LINEAR)])
    del inkimg
    q = predict(nl, dev, x, prob_lines, tile, pad, tta, blend, batch, offset=offset)
    del x
    if q.shape != (H, W): q = cv2.resize(q, (W, H), interpolation=cv2.INTER_LINEAR)
    return q


def u8(p): return (p * 255).astype(np.uint8)          # as blocks_noguide.py:39, 42 (truncation, not rounding)


def chain(nets, full, area_opt=None, lines_opt=None, area_u8=None):
    """the two networks as blocks_noguide.py runs them, with options. Returns (pa_u8 half size, pl_u8 full size, times)"""
    dev, na, nl = nets; area_opt = area_opt or {}; lines_opt = lines_opt or {}; t = {}
    t0 = time.time()
    if area_u8 is None: pa = u8(area_map(na, dev, full, **area_opt))
    else: pa = area_u8
    t['area_s'] = round(time.time() - t0, 2); t1 = time.time()
    pl = u8(lines_map(nl, dev, full, pa, **lines_opt))
    t['lines_s'] = round(time.time() - t1, 2)
    return pa, pl, t
