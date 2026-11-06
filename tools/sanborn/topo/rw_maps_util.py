import numpy as np, cv2
def pushpull(val, mask):
    v = np.where(mask, 0, val).astype(np.float64); w = (~mask).astype(np.float64); levels = []
    while min(v.shape) > 4 and (w == 0).any():
        levels.append((v, w))
        h2, w2 = (v.shape[0] + 1) // 2, (v.shape[1] + 1) // 2
        pv = np.zeros((h2 * 2, w2 * 2)); pw = np.zeros_like(pv); pv[:v.shape[0], :v.shape[1]] = v * w; pw[:w.shape[0], :w.shape[1]] = w
        sv = pv.reshape(h2, 2, w2, 2).sum((1, 3)); sw = pw.reshape(h2, 2, w2, 2).sum((1, 3))
        v = np.where(sw > 0, sv / np.maximum(sw, 1e-9), 0); w = np.minimum(sw, 1)
    for pv, pw in reversed(levels):
        up = cv2.resize(v.astype(np.float32), (pv.shape[1], pv.shape[0]), interpolation=cv2.INTER_LINEAR)
        v = pw * pv + (1 - pw) * up
    return np.where(mask, v, val).astype(np.float32)
