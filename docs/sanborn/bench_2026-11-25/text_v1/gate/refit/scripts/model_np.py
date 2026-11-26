"""numpy forward pass of the classifier, so finder3 runs on the system python with no torch (classifier step, 26 Nov 2026).

Two model kinds, both written by train.py into an .npz:
  'cnn'  32x32 image -> conv3x3(16) relu pool -> conv3x3(32) relu pool -> conv3x3(64) relu pool -> 1024, joined with the
         10 shape numbers (standardised) -> fc 128 relu -> fc classes. Batch norm is folded into the convolutions.
  'mlp'  HOG (324) + the image blurred and shrunk to 16x16 (256) + the 10 shape numbers, standardised -> fc 256 relu ->
         fc classes.
predict(model, img, scal) returns class probabilities (n, classes)."""
import numpy as np, cv2
from common import hog_batch


def load_model(path):
    M = dict(np.load(path, allow_pickle=True)); M['classes'] = [str(c) for c in M['classes']]; M['kind'] = str(M['kind']); return M


def _conv3(x, W, b):
    """x (n, c, h, w), W (o, c, 3, 3), padding 1 -> (n, o, h, w)"""
    n, c, h, w = x.shape; p = np.pad(x, ((0, 0), (0, 0), (1, 1), (1, 1)))
    cols = np.empty((n, c, 9, h, w), np.float32)
    for dy in range(3):
        for dx in range(3): cols[:, :, dy * 3 + dx] = p[:, :, dy:dy + h, dx:dx + w]
    cols = cols.reshape(n, c * 9, h * w)
    out = np.einsum('ok,nkp->nop', W.reshape(W.shape[0], -1), cols, optimize=True) + b[None, :, None]
    return out.reshape(n, W.shape[0], h, w)


def _pool(x):
    n, c, h, w = x.shape; return x.reshape(n, c, h // 2, 2, w // 2, 2).max(axis=(3, 5))


def mlp_input(img, scal):
    pix = np.stack([cv2.resize(cv2.GaussianBlur(g, (0, 0), 1.0), (16, 16), interpolation=cv2.INTER_AREA).ravel() for g in img]) if len(img) else np.zeros((0, 256), np.float32)
    return np.hstack([hog_batch(img), pix, scal]).astype(np.float32)


def predict(M, img, scal, batch=2048):
    img = img.astype(np.float32); scal = scal.astype(np.float32); out = []
    if img.max(initial=0) > 1.5: img = img / 255.0
    for s in range(0, len(img), batch):
        x = img[s:s + batch]; q = (scal[s:s + batch] - M['s_mu']) / M['s_sd']
        if M['kind'] == 'cnn':
            h = x[:, None]
            for j in range(3): h = _pool(np.maximum(_conv3(h, M[f'c{j}_w'], M[f'c{j}_b']), 0))
            z = np.hstack([h.reshape(len(x), -1), q])
        else:
            z = (mlp_input(x, scal[s:s + batch]) - M['x_mu']) / M['x_sd']
        z = np.maximum(z @ M['f0_w'].T + M['f0_b'], 0); z = z @ M['f1_w'].T + M['f1_b']
        z = z - z.max(1, keepdims=True); e = np.exp(z); out.append(e / e.sum(1, keepdims=True))
    return np.concatenate(out) if out else np.zeros((0, len(M['classes'])), np.float32)
