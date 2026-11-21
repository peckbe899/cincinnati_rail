exec(open('c2_common.py').read())
# 1) receptive field: gradient of one centre output pixel w.r.t. the input, on a real tile
y, x = 1280, 2560; T = 512
a = torch.tensor(np.ascontiguousarray(X[y:y + T, x:x + T].transpose(2, 0, 1))[None].astype(np.float32) / 255, requires_grad=True)
o = net(a); o[0, 1, T // 2, T // 2].backward(); g = a.grad[0].abs().sum(0).numpy()
nz = np.argwhere(g > 0); print('theoretical RF extent (px):', nz.min(0), nz.max(0), 'size', nz.max(0) - nz.min(0) + 1)
r = np.hypot(*(np.indices(g.shape) - T // 2)); tot = g.sum()
for q in (0.5, 0.9, 0.99): print(f'  radius holding {int(q*100)}% of |grad|:', int(np.sort(r.ravel())[np.searchsorted(np.cumsum(g.ravel()[np.argsort(r.ravel())]), q * tot)]))
# 2) GroupNorm: change content far outside the receptive field and watch the centre
with torch.no_grad():
    for (yy, xx) in [(1280, 2560), (640, 1280), (2200, 3600)]:
        t = X[yy:yy + 768, xx:xx + 768].copy(); base = F.softmax(net(norm(t[None]))[:, :2], 1)[0, 1].numpy()[256:512, 256:512]
        paper = np.median(t[:, :, :3].reshape(-1, 3), 0)
        t2 = t.copy(); mask = np.ones((768, 768), bool); mask[120:648, 120:648] = False; t2[mask, :3] = paper      # outer 120 px ring -> plain paper (>=136 px from the centre block)
        p2 = F.softmax(net(norm(t2[None]))[:, :2], 1)[0, 1].numpy()[256:512, 256:512]
        t3 = X[yy:yy + 768, xx:xx + 768].copy(); t3[:, :, 3:] = 0; t3[600:760, 600:760, 3:] = 255          # a 160 px guide rectangle of 255 (as train() line 124 does), in a corner >=88 px from the centre block
        p3 = F.softmax(net(norm(t3[None]))[:, :2], 1)[0, 1].numpy()[256:512, 256:512]
        t4 = t.copy(); t4[300:460, 300:460, 3:] = 255                                                       # the same rectangle over the centre
        p4 = F.softmax(net(norm(t4[None]))[:, :2], 1)[0, 1].numpy()[256:512, 256:512]
        print(f'tile {yy},{xx}: outer ring -> paper: centre mean|dP| {np.abs(p2 - base).mean():.4f}, flips {((p2 > .5) != (base > .5)).mean():.4f} | 255 guide box in corner: mean|dP| {np.abs(p3 - base).mean():.4f}, flips {((p3 > .5) != (base > .5)).mean():.4f} | 255 box over centre: mean|dP| {np.abs(p4 - base).mean():.4f} flips {((p4 > .5) != (base > .5)).mean():.4f}')
