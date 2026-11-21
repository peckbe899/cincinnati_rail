exec(open('v5_cpu.py').read().split("t0 = time.time()\n# (a)")[0])
import time
# two sub-regions; compare stored 768/64, 768/192, Hann 768 step 384
def tiled(tile, pad, y0, y1, x0, x1):
    step = tile - 2*pad; h, w = X.shape[:2]; im = cv2.copyMakeBorder(X, pad, pad+tile, pad, pad+tile, cv2.BORDER_REFLECT); out = np.full((h, w), np.nan, np.float32)
    for y in range(0, h, step):
        if y+step <= y0 or y >= y1: continue
        for x in range(0, w, step):
            if x+step <= x0 or x >= x1: continue
            p = P(im[y:y+tile, x:x+tile])[pad:pad+step, pad:pad+step]; out[y:y+step, x:x+step] = p[:min(step, h-y), :min(step, w-x)]
    return out[y0:y1, x0:x1]
def hann(T, S, y0, y1, x0, x1):
    w1 = np.hanning(T+2)[1:-1].astype(np.float32); win = np.outer(w1, w1) + 1e-4
    ap = np.zeros((y1-y0, x1-x0), np.float32); aw = np.zeros_like(ap); im = cv2.copyMakeBorder(X, T, T, T, T, cv2.BORDER_REFLECT)
    for ty in range(y0 - T + S, y1, S):
        for tx in range(x0 - T + S, x1, S):
            p = P(im[ty+T:ty+2*T, tx+T:tx+2*T]); a0, b0 = max(ty, y0), min(ty+T, y1); c0, d0 = max(tx, x0), min(tx+T, x1)
            ap[a0-y0:b0-y0, c0-x0:d0-x0] += (p*win)[a0-ty:b0-ty, c0-tx:d0-tx]; aw[a0-y0:b0-y0, c0-x0:d0-x0] += win[a0-ty:b0-ty, c0-tx:d0-tx]
    return ap/aw
st = cv2.imread(U + '44_pred_area_ng1.png', 0).astype(np.float32)/255
for (y0, y1, x0, x1) in [(1920, 3200, 2560, 4480), (0, 1280, 3200, 5120)]:
    t0 = time.time(); L = lab[y0:y1, x0:x1]; m = L != 255
    acc = lambda Q: round(float(((Q[m] > .5) == (L[m] == 1)).mean()), 4)
    A = st[y0:y1, x0:x1]; B = tiled(768, 192, y0, y1, x0, x1); H = hann(768, 384, y0, y1, x0, x1)
    def seam(Q):
        d = (Q[:, 1:] > .5) != (Q[:, :-1] > .5); cols = [c - x0 - 1 for c in range(640, 6000, 640) if 0 <= c - x0 - 1 < Q.shape[1]-1]
        mid = [c - x0 - 1 for c in range(320, 6000, 640) if 0 <= c - x0 - 1 < Q.shape[1]-1]
        return round(float(d[:, cols].mean()), 4), round(float(d[:, mid].mean()), 4)
    print(f'region {y0}:{y1},{x0}:{x1} labelled {int(m.sum())}: acc 768/64 {acc(A)}  768/192 {acc(B)}  hann {acc(H)} | differ A-B {float(((A>.5)!=(B>.5)).mean()):.4f} A-H {float(((A>.5)!=(H>.5)).mean()):.4f} | flips at 640-seam cols vs mid: A {seam(A)} H {seam(H)} | {time.time()-t0:.0f}s')
