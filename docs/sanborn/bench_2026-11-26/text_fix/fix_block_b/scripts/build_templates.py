"""Digit templates from the real figures (extract_digits.py) and, for comparison, from Windows fonts.
    python -B .../scripts/build_templates.py REAL.npy OUTDIR
Writes OUTDIR/tmpl_real_{A,B,all}.npz (per digit: mean of the figures scaled to height 52, as a 0-1 map on a 72 x 72
canvas, centred on the figure's box; n, median width/height) and tmpl_font_<name>.npz, plus montages.
Fold A templates use only fold-A plates' figures, fold B only fold-B's."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
import bfcommon as C

H0, CAN = 52, 72
real, od = sys.argv[1], sys.argv[2]
R = list(np.load(real, allow_pickle=True))


def norm(mask):
    """scale a figure mask (cropped to its box) to height H0, centre on the canvas"""
    ys, xs = np.nonzero(mask); m = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.float32)
    s = H0 / m.shape[0]; w = max(1, int(round(m.shape[1] * s)))
    m = cv2.resize(m, (w, H0), interpolation=cv2.INTER_AREA)
    c = np.zeros((CAN, CAN), np.float32); x0 = (CAN - w) // 2; y0 = (CAN - H0) // 2
    if w > CAN: m = m[:, (w - CAN) // 2:(w - CAN) // 2 + CAN]; x0 = 0; w = CAN
    c[y0:y0 + H0, x0:x0 + w] = m; return c, w / H0


def fig_mask(q):
    return (q['ink'] & cv2.dilate(q['comp'], np.ones((5, 5), np.uint8))).astype(np.uint8)


def build(sel, name):
    T = {}; asp = {}; n = {}
    for d in '0123456789':
        ims = []; ar = []
        for q in sel:
            if q['digit'] != d: continue
            c, a = norm(fig_mask(q)); ims.append(c); ar.append(a)
        if not ims: continue
        ar = np.array(ar); med = np.median(ar); keep = np.abs(ar - med) <= 0.2 * med + 0.03
        T[d] = np.mean(np.array(ims)[keep], 0); asp[d] = float(np.median(ar[keep])); n[d] = int(keep.sum())
    np.savez(os.path.join(od, f'tmpl_{name}.npz'), **{f't{d}': T[d] for d in T}, **{f'a{d}': asp[d] for d in asp}, **{f'n{d}': n[d] for d in n})
    row = np.concatenate([cv2.copyMakeBorder((255 - 255 * T[d]).astype(np.uint8), 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0) for d in sorted(T)], 1)
    print(name, n, {d: round(a, 2) for d, a in asp.items()}); return row


rows = [build(R, 'real_all'), build([q for q in R if q['fold'] == 'A'], 'real_A'), build([q for q in R if q['fold'] == 'B'], 'real_B')]
FD = 'C:/Windows/Fonts'
for fn in ('FRADM.TTF', 'FRAHV.TTF', 'GOTHICB.TTF', 'arialbd.ttf', 'GILB____.TTF', 'FRADMCN.TTF', 'ARIALNB.TTF', 'LTYPEB.TTF'):
    p = os.path.join(FD, fn)
    if not os.path.exists(p): continue
    f = ImageFont.truetype(p, 200); T = {}; asp = {}
    for d in '0123456789':
        im = Image.new('L', (300, 300), 0); ImageDraw.Draw(im).text((40, 20), d, fill=255, font=f)
        a = np.array(im) > 127; c, ar = norm(a.astype(np.uint8)); T[d] = c; asp[d] = ar
    nm = 'font_' + fn.split('.')[0].strip('_')
    np.savez(os.path.join(od, f'tmpl_{nm}.npz'), **{f't{d}': T[d] for d in T}, **{f'a{d}': asp[d] for d in asp}, **{f'n{d}': 0 for d in T})
    rows.append(np.concatenate([cv2.copyMakeBorder((255 - 255 * T[d]).astype(np.uint8), 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0) for d in sorted(T)], 1))
S = np.concatenate(rows, 0); cv2.imwrite(os.path.join(od, 'templates.png'), cv2.resize(S, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST))
