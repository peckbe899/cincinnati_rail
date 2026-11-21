exec(open('c2_common.py').read())
stored = cv2.imread(U + '44_pred_area_ng1.png', 0).astype(np.float32) / 255
y0, y1, x0, x1 = 640, 2560, 1280, 3840; T, S = 768, 384
win1 = np.hanning(T + 2)[1:-1].astype(np.float32); win = np.outer(win1, win1) + 1e-4
acc_p = np.zeros((y1 - y0, x1 - x0), np.float32); acc_w = np.zeros_like(acc_p)
h, w = X.shape[:2]; im = cv2.copyMakeBorder(X, T, T, T, T, cv2.BORDER_REFLECT)
t0 = time.time()
with torch.no_grad():
    for ty in range(y0 - T + S, y1, S):
        for tx in range(x0 - T + S, x1, S):
            p = F.softmax(net(norm(im[None, ty + T:ty + 2 * T, tx + T:tx + 2 * T]))[:, :2], 1)[0, 1].numpy()
            a0, b0 = max(ty, y0), min(ty + T, y1); c0, d0 = max(tx, x0), min(tx + T, x1)
            acc_p[a0 - y0:b0 - y0, c0 - x0:d0 - x0] += (p * win)[a0 - ty:b0 - ty, c0 - tx:d0 - tx]; acc_w[a0 - y0:b0 - y0, c0 - x0:d0 - x0] += win[a0 - ty:b0 - ty, c0 - tx:d0 - tx]
P = acc_p / acc_w; print('blend time', round(time.time() - t0), 's')
A = stored[y0:y1, x0:x1]; L = lab[y0:y1, x0:x1]; m = L != 255
B = np.load('c2_B.npy')
def acc(P): return round(float(((P[m] > 0.5) == (L[m] == 1)).mean()), 4)
def iou_s(P): pr = P[m] > 0.5; gt = L[m] == 1; return round(float(((~pr) & (~gt)).sum() / ((~pr) | (~gt)).sum()), 4)
def seamflips(P, step, off):
    d = (P[1:] > 0.5) != (P[:-1] > 0.5); rows = [y - off - 1 for y in range(0, 10000, step) if 0 <= y - off - 1 < P.shape[0] - 1]
    other = [r for r in range(P.shape[0] - 1) if all(abs(r - s) > 3 for s in rows)]; return round(float(d[rows].mean()), 4), round(float(d[other].mean()), 4)
print('acc / iou_street: A (as run)', acc(A), iou_s(A), '| B 768/192', acc(B), iou_s(B), '| Hann blend 768 step 384', acc(P), iou_s(P))
print('flips at A seam rows (A, blend):', seamflips(A, 640, y0), seamflips(P, 640, y0))
print('flips at B seam rows (B, blend):', seamflips(B, 384, y0), seamflips(P, 384, y0))
print('decision differs blend vs A', round(float(((P > .5) != (A > .5)).mean()), 4))
np.save('c5_blend.npy', P)
