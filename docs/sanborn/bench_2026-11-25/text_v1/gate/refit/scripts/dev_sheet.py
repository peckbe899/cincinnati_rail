"""Contact sheet of dev pieces (T1-T7) chosen by a rule on the classifier's P(junk), with the scan and finder2's codes.
DEV ONLY. cd data/sanborn; python -B .../dev_sheet.py MODEL.npz WHICH OUT.jpg
WHICH: wrongjunk (finder2 text, truth text, P(junk) >= 0.9), rightjunk (finder2 text, truth non-text, P(junk) >= 0.9),
       missedtext (finder2 other, truth text) sorted by P(text)."""
import os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from model_np import load_model, predict  # noqa
from dump_pieces import load, mask  # noqa


def main():
    mp, which, out = sys.argv[1:4]; V = np.load(os.path.join(HERE, '..', 'data', 'dev.npz')); M = load_model(mp)
    pr = predict(M, V['img'], V['scal']); J = M['classes'].index('junk'); pj = pr[:, J]; top = np.array(M['classes'])[pr.argmax(1)]
    cc = V['codes']; tot = np.maximum(cc.sum(1), 1); istext = (cc[:, 2] + cc[:, 3]) >= 0.5 * tot; e = np.maximum(V['bbox'][:, 2], V['bbox'][:, 3])
    t2, t1 = V['t2'], V['t1']
    if which == 'wrongjunk': s = np.nonzero(istext & (pj >= 0.9) & (t2 > t1) & (e >= 8))[0]; s = s[np.argsort(-t2[s])]
    elif which == 'rightjunk': s = np.nonzero(istext & (pj >= 0.9) & (t1 > t2) & (e >= 8))[0]; s = s[np.argsort(-t1[s])]
    else: s = np.nonzero(~istext & (t2 > t1) & (e >= 8))[0]; s = s[np.argsort(pj[s])]
    D = {}; ims = {}; tiles = []
    for i in s[:150]:
        N = str(V['plate'][i]); D.setdefault(N, load(N)); ims.setdefault(N, cv2.imread(f'cufp/22-{N}.jpg'))
        d = D[N]; j = int(V['idx'][i]); x, y, w, h = d['bbox'][j]; m = mask(d, j) > 0; code = d['pre']; H, W = code.shape
        sz = max(30, w, h) // 2 + 20; cx, cy = x + w // 2, y + h // 2; X0, Y0, X1, Y1 = max(0, cx - sz), max(0, cy - sz), min(W, cx + sz), min(H, cy + sz)
        a = ims[N][Y0:Y1, X0:X1]; o = (a * 0.3 + 255 * 0.7).astype(np.uint8); cw = code[Y0:Y1, X0:X1]
        o[cw == 1] = (160, 160, 160); o[np.isin(cw, (2, 3))] = (220, 0, 220)
        pm = np.zeros(cw.shape, bool); pm[y - Y0:y - Y0 + h, x - X0:x - X0 + w] = m; o[pm] = (0, 0, 255)
        t_ = cv2.resize(np.concatenate([a, o], 1), (240, 120), interpolation=cv2.INTER_AREA)
        cv2.putText(t_, f"{V['crop'][i]} {V['kind'][i]} {e[i]} pj{pj[i]:.2f} {top[i]} {t2[i]}/{t1[i]}", (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 120, 0), 1)
        tiles.append(t_)
    cols = 6; rows = max(1, (len(tiles) + cols - 1) // cols); sheet = np.full((rows * 122, cols * 242, 3), 255, np.uint8)
    for j, t_ in enumerate(tiles): r, c = divmod(j, cols); sheet[r * 122:r * 122 + 120, c * 242:c * 242 + 240] = t_
    cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 88]); print(which, len(s), 'pieces;', len(tiles), 'shown ->', out)


if __name__ == '__main__':
    main()
