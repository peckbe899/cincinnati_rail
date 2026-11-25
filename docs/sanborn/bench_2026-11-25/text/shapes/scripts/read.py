"""Read the words in a window of a plate with the k-NN glyph reader (shapes prototype, 25 Nov 2026).

    python -B bench_2026-11-25/text/shapes/scripts/read.py N X0 Y0 X1 Y1 OUT.jpg [--model model.npz] [--rej D] [--nosplit]
    (from data/sanborn)

For every word (extract_glyphs.py) with its centre in the window, each glyph of 12 px or more is read by the k-NN
reader of classify.py (model.npz):
  - touching figures: a glyph at least 0.8 as wide as tall (14-70 px tall) is also tried cut in two, along slanted
    cuts (slant 0-0.45) where the column count of ink is lowest (up to 3 cuts tried); the cut is kept when both
    parts are read as characters, each nearer to its nearest training glyph than the whole was, and each part is at
    least 0.6 of the height. Parts can be cut again once (three touching figures). --nosplit turns this off;
  - the word is read both ways round (as found, and turned 180 deg); the way with the smaller mean distance wins;
  - output: a glyph read as 'junk' is '_', a small flat dash (4-6 px tall, 6-22 px long) is '-', other glyphs under
    12 px are '.', a glyph further than --rej (default 0.5) from every training glyph is '?'.
Words are printed top to bottom with their reading; OUT.jpg shows each glyph's reading (blue; red '?').
Also importable: read_window(N, box, model) -> list of words with 'text'.
"""
import os, sys
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster import features  # noqa: E402
from extract_glyphs import norm_glyph  # noqa: E402
from classify import knn  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REJ = 0.5


class Reader:
    def __init__(self, path):
        M = np.load(path, allow_pickle=True)
        self.mu, self.V, self.Ztr, self.ytr, self.classes = M['mu'], M['V'], M['Ztr'], M['ytr'], M['classes']

    def read(self, bitmaps):
        """bitmaps: list of 0/1 arrays (turned, tight) -> list of (char, dist)"""
        if not bitmaps: return []
        imgs = np.stack([norm_glyph(t) for t in bitmaps]); hw = np.array([t.shape for t in bitmaps], np.float32)
        Z = ((features(imgs, hw) - self.mu) @ self.V).astype(np.float32)
        b, s, d = knn(self.Ztr, self.ytr, Z, k=getattr(self, 'k', 5))
        return [(str(self.classes[i]), float(x)) for i, x in zip(b, d)]


def tight(m):
    ys, xs = np.nonzero(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1] if len(xs) else None


def cuts(t, ntry=3):
    """up to ntry (left, right) splits of bitmap t along slanted lines of least ink"""
    h, w = t.shape; ys, xs = np.nonzero(t); cand = []
    for s in (0.0, 0.15, 0.25, 0.35, 0.45):
        xp = xs - s * (h - 1 - ys); xp = xp - xp.min(); xi = np.round(xp).astype(int); Wp = xi.max() + 1
        proj = np.bincount(xi, minlength=Wp)
        for c in range(max(1, int(0.25 * Wp)), min(Wp - 1, int(0.75 * Wp) + 1)):
            cand.append((proj[c], abs(c - Wp / 2), s, c))
    cand.sort(); out = []; seen = set()
    for v, _, s, c in cand:
        if v > max(2, 0.12 * h) or len(out) >= ntry: break
        if (round(s, 2), c // 3) in seen: continue
        seen.add((round(s, 2), c // 3))
        xp = xs - s * (h - 1 - ys); xp = xp - xp.min()
        L = np.zeros_like(t); R = np.zeros_like(t); left = xp < c
        L[ys[left], xs[left]] = 1; R[ys[~left], xs[~left]] = 1
        L, R = tight(L), tight(R)
        if L is None or R is None or min(L.shape[0], R.shape[0]) < 0.6 * h or min(L.shape[1], R.shape[1]) < 0.2 * h: continue
        out.append((L, R))
    return out


def read_bitmap(R, t, split=True, depth=0):
    """list of (char, dist) for bitmap t, cut into touching figures when that reads better"""
    (c0, d0), = R.read([t])
    h, w = t.shape
    if split and depth < 2 and w >= 0.8 * h and 14 <= h <= 70:
        best = None
        for L_, R_ in cuts(t):
            (cl, dl), (cr, dr) = R.read([L_, R_])
            if cl == 'junk' or cr == 'junk' or max(dl, dr) >= d0: continue
            if best is None or max(dl, dr) < best[0]: best = (max(dl, dr), L_, R_)
        if best:
            return read_bitmap(R, best[1], split, depth + 1) + read_bitmap(R, best[2], split, depth + 1)
    return [(c0, d0)]


def raw_glyph(D, k):
    o0, o1 = D['raw_off'][k], D['raw_off'][k + 1]
    hh, ww = D['hw'][k].astype(int)
    return D['raw'][o0:o1].reshape(hh, ww) if o1 > o0 else None


def read_window(N, box, R, split=True, rej=REJ, D=None, gdir='glyphs'):
    x0, y0, x1, y1 = box
    D = D if D is not None else np.load(os.path.join(HERE, gdir, f'{N}.npz'))
    cen = D['cen']; inside = (cen[:, 0] >= x0) & (cen[:, 0] < x1) & (cen[:, 1] >= y0) & (cen[:, 1] < y1)
    out = []
    for w in np.unique(D['word'][inside]):
        mem = np.nonzero(D['word'] == w)[0]; mem = mem[np.argsort(D['order'][mem])]
        ways = []
        for flip in (False, True):
            seq = mem[::-1] if flip else mem; toks = []; ds = []
            for k in seq:
                t = raw_glyph(D, k); hh, ww = D['hw'][k]
                if t is None:
                    toks.append([('-' if 4 <= min(hh, ww) <= 6 and 6 <= max(hh, ww) <= 22 and (ww > hh) != flip or (4 <= hh <= 6 and 6 <= ww <= 22) else '.', 0.0, k)]); continue
                r = read_bitmap(R, t[::-1, ::-1] if flip else t, split)
                toks.append([(c, d, k) for c, d in r]); ds += [d for _, d in r]
            ways.append((np.mean(ds) if ds else 0.0, flip, toks))
        if len(mem) == 1: ways = ways[:1]
        dmean, flip, toks = min(ways, key=lambda x: x[0])
        text = ''; glyphs = []
        for tk in toks:
            for c, d, k in tk:
                ch = c if c in '.-' else ('?' if d > rej else ('_' if c == 'junk' else c))
                text += ch; glyphs.append((int(k), ch, d))
        out.append(dict(word=int(w), text=text, glyphs=glyphs, flip=flip, x=float(cen[mem, 0].mean()), y=float(cen[mem, 1].mean()),
                        angle=float(np.rad2deg(D['angle'][mem].mean())), dist=float(dmean)))
    return D, out


def main():
    N = sys.argv[1]; x0, y0, x1, y1 = (int(v) for v in sys.argv[2:6]); outp = sys.argv[6]
    mf = sys.argv[sys.argv.index('--model') + 1] if '--model' in sys.argv else os.path.join(HERE, 'model.npz')
    rej = float(sys.argv[sys.argv.index('--rej') + 1]) if '--rej' in sys.argv else REJ
    R = Reader(mf)
    D, W = read_window(N, (x0, y0, x1, y1), R, split='--nosplit' not in sys.argv, rej=rej)
    im = cv2.imread(f'cufp/22-{N}.jpg')[y0:y1, x0:x1]; c = (im * 0.55 + 255 * 0.45).astype(np.uint8)
    for w in sorted(W, key=lambda w: (round(w['y'] / 40), w['x'])):
        if all(ch in '._-' for ch in w['text']): continue
        # write the word's reading beside its first glyph
        k0 = w['glyphs'][0][0]; bx, by, bw, bh = D['bbox'][k0]
        txt = w['text'].replace('_', '').replace('.', '')
        cv2.putText(c, txt, (int(bx - x0), int(by - y0 - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255) if '?' in txt else (200, 0, 0), 2)
        print(f"  ({w['x']:.0f},{w['y']:.0f}) {w['angle']:+.0f} deg{' turned' if w['flip'] else ''}: {w['text']}")
    cv2.imwrite(outp, c, [cv2.IMWRITE_JPEG_QUALITY, 92])


if __name__ == '__main__':
    main()
