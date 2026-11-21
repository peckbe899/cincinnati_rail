exec(open('c2_common.py').read())
stored = cv2.imread(U + '44_pred_area_ng1.png', 0).astype(np.float32) / 255
y0, y1, x0, x1 = 640, 2560, 1280, 3840
A = stored[y0:y1, x0:x1]; L = lab[y0:y1, x0:x1]; m = L != 255
t0 = time.time(); B = tiled(X, 768, 192, y0, y1, x0, x1); tb = time.time() - t0
t0 = time.time(); C = tiled(X, 1536, 128, y0, y1, x0, x1); tc = time.time() - t0
def acc(P): return round(float(((P[m] > 0.5) == (L[m] == 1)).mean()), 4)
def flips(P, step, off_y, off_x):
    # 0.5-decision changes across rows at this scheme's seams vs elsewhere
    d = (P[1:] > 0.5) != (P[:-1] > 0.5)
    rows = [y - off_y - 1 for y in range(0, 10000, step) if 0 <= y - off_y - 1 < P.shape[0] - 1]
    other = [r for r in range(P.shape[0] - 1) if all(abs(r - s) > 3 for s in rows)]
    return round(float(d[rows].mean()), 4), round(float(d[other].mean()), 4)
print('time B', round(tb), 's; C', round(tc), 's')
print('accuracy vs label  A(768/64, as run)', acc(A), ' B(768/192)', acc(B), ' C(1536/128)', acc(C))
print('decision differs A vs B', round(float(((A > 0.5) != (B > 0.5)).mean()), 4), ' A vs C', round(float(((A > 0.5) != (C > 0.5)).mean()), 4), ' B vs C', round(float(((B > 0.5) != (C > 0.5)).mean()), 4))
print('row-seam flips (seam, other): A', flips(A, 640, y0, x0), ' B', flips(B, 384, y0, x0), ' C', flips(C, 1280, y0, x0))
np.save('c2_B.npy', B); np.save('c2_C.npy', C)
