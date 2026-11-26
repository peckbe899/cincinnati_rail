"""Synthetic Sanborn-like characters drawn from fonts already on this machine (classifier step, 26 Nov 2026).

    cd data/sanborn; python -B bench_2026-11-25/text_v1/classifier/scripts/synth.py [--per 300] [--seed 0]

Fonts (C:/Windows/Fonts and OpenCV's Hershey faces). The five that read Sanborn digits best in research font_test.py:
  ARIALNI.TTF (Arial Narrow Italic), TCCM____.TTF slanted 0.25 (Tw Cen MT Condensed), Hershey complex italic,
  FRAMDCN.TTF slanted 0.25 (Franklin Gothic Medium Condensed), trebucit.ttf (Trebuchet Italic).
Added for the upright street-name capitals (research font_caps.py: 'closest to Hershey Simplex, Arial and Bahnschrift'):
  arial.ttf, bahnschrift.ttf and Hershey simplex, upright, capitals only.
Each sample is jittered: slant (shear, plus the font's own), how it lies on the plate (70% level within 6 deg, 10% turned
+90, 10% -90, 10% any angle), height on the scan by class (figures 12-40 px, capitals 16-75 px, small letters 9-24 px
x-height, marks by kind), stroke width (0.12 x height, x 0.75-1.3, 2-9 px; capitals over 45 px 4-9 px) by dilating or
eroding, ragged edges (blur + noise), and sometimes a 1 px break. Classes: 0-9, A-Z, a-z, the marks ' " . - & , ,
'pair' (two figures drawn touching, e.g. 25, 14), 'run' (3-5 figures, sometimes with ' " . or -, each touching the next,
as 165 or 540-5: finder2 calls such runs one glyph, and the first fit, without this class, called them junk), and 'frag'
(a figure or capital cut by a straight band 2-6 px wide, the biggest piece kept when it holds 35-85% of the ink: the
pieces finder2 leaves when line ink crosses a glyph). Writes data/synth.npz: masks (bit-packed, tight), label, font.
No real glyph is used here."""
import os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import tight  # noqa
FD = 'C:/Windows/Fonts/'
FONTS = [('ARIALNI.TTF', 0.0, 'dcl'), ('TCCM____.TTF', 0.25, 'dc'), ('hershey_complex_italic', 0.0, 'dcl'),
         ('FRAMDCN.TTF', 0.25, 'dc'), ('trebucit.ttf', 0.0, 'dcl'),
         ('arial.ttf', 0.0, 'C'), ('bahnschrift.ttf', 0.0, 'C'), ('hershey_simplex', 0.0, 'C')]
HER = {'hershey_complex_italic': cv2.FONT_HERSHEY_COMPLEX | cv2.FONT_ITALIC, 'hershey_simplex': cv2.FONT_HERSHEY_SIMPLEX}
DIG = '0123456789'; CAP = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'; LOW = 'abcdefghijklmnopqrstuvwxyz'; MARK = ['\'', '"', '.', '-', '&', ',']


def render(font, text, size=96):
    if font in HER:
        im = np.zeros((4 * size, 2 * size + 60 * len(text)), np.uint8)
        cv2.putText(im, text, (20, 2 * size), HER[font], size / 30.0, 255, max(2, size // 16), cv2.LINE_AA)
        return im > 127
    f = ImageFont.truetype(FD + font, size)
    im = Image.new('L', (size * (2 + len(text)), size * 3), 0)
    ImageDraw.Draw(im).text((size // 2, size // 2), text, fill=255, font=f)
    return np.array(im) > 127


def render_pair(font, a, b, rng, size=96):
    """two figures drawn so they touch: each drawn alone, the second slid left until it meets the first, then 1-4 px more"""
    ga, gb = tight(render(font, a, size)), tight(render(font, b, size))
    if ga is None or gb is None: return None
    h = max(ga.shape[0], gb.shape[0]); W = ga.shape[1] + gb.shape[1] + 10
    best = None
    for ov in range(0, gb.shape[1] // 2):
        c = np.zeros((h, W), np.uint8); c[h - ga.shape[0]:, :ga.shape[1]] |= ga; x = ga.shape[1] - ov
        c[h - gb.shape[0]:, x:x + gb.shape[1]] |= gb
        if cv2.connectedComponents(c, connectivity=8)[0] == 2:
            best = c; extra = int(rng.integers(0, 5)); x2 = max(0, x - extra)
            c2 = np.zeros((h, W), np.uint8); c2[h - ga.shape[0]:, :ga.shape[1]] |= ga; c2[h - gb.shape[0]:, x2:x2 + gb.shape[1]] |= gb
            best = c2; break
    return best


def render_run(font, chars, rng, size=96):
    """3-6 characters drawn so each touches the next (Sanborn's italic figures often run together: 165, 540-5, 99')"""
    gs = [tight(render(font, c, size)) for c in chars]
    if any(g is None for g in gs): return None
    h = max(g.shape[0] for g in gs) + 4; W = sum(g.shape[1] for g in gs) + 20
    c = np.zeros((h, W), np.uint8); base = h - 2
    def put(canvas, g, x, ch):
        y = base - g.shape[0] if ch not in ('\'', '"', '-') else (2 if ch != '-' else base - int(0.45 * size))
        y = max(0, min(h - g.shape[0], y)); canvas[y:y + g.shape[0], x:x + g.shape[1]] |= g
    put(c, gs[0], 0, chars[0]); right = gs[0].shape[1]
    for g, ch in zip(gs[1:], chars[1:]):
        done = False
        for ov in range(0, min(g.shape[1], right)):
            t = c.copy(); put(t, g, right - ov, ch)
            if cv2.connectedComponents(t, connectivity=8)[0] == 2:
                ov2 = min(g.shape[1] - 1, right, ov + int(rng.integers(0, 4))); t = c.copy(); put(t, g, right - ov2, ch); c = t; right = right - ov2 + g.shape[1]; done = True; break
        if not done: return None
    return c[:, :right + 2]


def cut_frag(m, rng):
    """a glyph cut by a line, as finder2 cuts glyphs where line ink crosses them: a straight band 2-6 px wide at any angle
    through the glyph is erased; the biggest piece left is kept when it holds 35-85% of the ink"""
    m = m.astype(np.uint8); h, w = m.shape; ys, xs = np.nonzero(m)
    if len(xs) < 30: return None
    j = rng.integers(len(xs)); a = rng.uniform(0, np.pi); d = np.array([np.cos(a), np.sin(a)]) * 2 * max(h, w)
    c = np.array([xs[j], ys[j]], float); band = np.zeros_like(m)
    cv2.line(band, tuple(np.round(c - d).astype(int).tolist()), tuple(np.round(c + d).astype(int).tolist()), 1, int(rng.integers(2, 7)))
    r = m & (1 - band); n, lb, st, _ = cv2.connectedComponentsWithStats(r, connectivity=8)
    if n < 2: return None
    b = 1 + np.argmax(st[1:, 4]); f = st[b, 4] / m.sum()
    return tight(lb == b) if 0.35 <= f <= 0.85 else None


def jitter(g, slant, cls, rng):
    m = (g.astype(np.uint8) * 255); t = tight(m > 0)
    if t is None: return None
    m = cv2.copyMakeBorder(t * 255, 40, 40, 40, 40, cv2.BORDER_CONSTANT, 0); h, w = m.shape
    sh = -(slant + rng.normal(0, 0.06))
    u = rng.random()
    if u < 0.7: rot = rng.normal(0, 3)
    elif u < 0.8: rot = 90 + rng.normal(0, 3)
    elif u < 0.9: rot = -90 + rng.normal(0, 3)
    else: rot = rng.uniform(-180, 180)
    r = np.deg2rad(rot)
    A = np.array([[1, sh, 0], [0, 1, 0]], np.float32)
    A[:, 2] = np.array([w / 2, h / 2]) - A[:, :2] @ np.array([w / 2, h / 2])
    m = cv2.warpAffine(m, A, (w, h))
    R = cv2.getRotationMatrix2D((w / 2, h / 2), rot, 1.0); m = cv2.warpAffine(m, R, (w, h))
    # height on the scan, measured upright (before turning): use the glyph's own upright height
    if cls in DIG or cls == 'pair': ht = rng.uniform(12, 40)
    elif cls in CAP: ht = rng.uniform(16, 75)
    elif cls in LOW: ht = rng.uniform(9, 24) * (1.45 if cls in 'bdfhklt' else (1.4 if cls in 'gjpqy' else 1.0))
    elif cls in ('\'', ','): ht = rng.uniform(6, 15)
    elif cls == '"': ht = rng.uniform(6, 15)
    elif cls == '.': ht = rng.uniform(3, 7)
    elif cls == '-': ht = rng.uniform(1.5, 4)
    else: ht = rng.uniform(15, 35)
    sc = ht / max(1, t.shape[0]); sc *= rng.uniform(0.9, 1.1)
    nh, nw = max(2, int(round(h * sc))), max(2, int(round(w * sc * rng.uniform(0.88, 1.12))))
    m = cv2.resize(m, (nw, nh), interpolation=cv2.INTER_AREA) > 110
    t2 = tight(m)
    if t2 is None: return None
    m = cv2.copyMakeBorder(t2, 6, 6, 6, 6, cv2.BORDER_CONSTANT, 0)
    # stroke width to target
    dt = cv2.distanceTransform(np.pad(m, 1), cv2.DIST_L2, 3); ridge = (dt > 0) & (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8)))
    cur = 2 * dt[ridge].mean() if ridge.any() else 2
    if cls in CAP and ht > 45: want = rng.uniform(4, 9)
    elif cls in ('.',): want = ht
    else: want = float(np.clip(0.12 * ht * rng.uniform(0.75, 1.3), 2, 9))
    d = int(np.clip(round((want - cur) / 2), -2, 3)); k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    if d > 0: m = cv2.dilate(m, k, iterations=d)
    elif d < 0:
        e = cv2.erode(m, k, iterations=-d)
        if e.sum() >= 0.4 * m.sum() and cv2.connectedComponents(e, connectivity=8)[0] <= cv2.connectedComponents(m, connectivity=8)[0]: m = e
    g = (cv2.GaussianBlur(m.astype(np.float32), (3, 3), 0.7) + rng.normal(0, 0.12, m.shape)) > 0.5
    m = g if g.sum() >= 0.7 * m.sum() else m.astype(bool)
    if rng.random() < 0.08 and m.sum() > 60:   # a 1 px break, as faint figures break at the ink threshold
        ys, xs = np.nonzero(m); j = rng.integers(len(xs)); m = m.copy(); m[max(0, ys[j] - 1):ys[j] + 1, max(0, xs[j] - 1):xs[j] + 1] = False
    # keep the biggest piece only when a mark is one stroke; a character is kept whole only if it is one 8-connected piece
    n, lb, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    if n > 2:
        big = 1 + np.argmax(st[1:, 4])
        if st[big, 4] < 0.85 * st[1:, 4].sum() and cls not in ('"',): return None   # broken into real pieces: not one piece
        m = lb == big
    return tight(m)


def main():
    a = sys.argv; per = int(a[a.index('--per') + 1]) if '--per' in a else 300; seed = int(a[a.index('--seed') + 1]) if '--seed' in a else 0
    rng = np.random.default_rng(seed); masks = []; labels = []; fonts = []
    cache = {}
    for font, slant, use in FONTS:
        classes = (list(DIG) if 'd' in use else []) + (list(CAP) if ('c' in use or 'C' in use) else []) + (list(LOW) if 'l' in use else []) + (MARK if 'd' in use else [])
        if 'd' in use: classes += ['pair', 'run']
        classes += ['frag']
        share = 1.0 if use != 'C' else 0.6
        for cls in classes:
            nper = int(per * share * (0.5 if cls in LOW else 1.0) * (2.0 if cls == 'pair' else 1.0) * (4.0 if cls == 'run' else 1.0) * (8.0 if cls == 'frag' else 1.0))
            got = 0; tries = 0
            while got < nper and tries < nper * 4:
                tries += 1
                if cls == 'pair':
                    g = render_pair(font, str(rng.integers(0, 10)), str(rng.integers(0, 10)), rng)
                    if g is None: continue
                elif cls == 'run':
                    chars = [str(c) for c in rng.integers(0, 10, int(rng.integers(3, 6)))]
                    if rng.random() < 0.3: chars.insert(int(rng.integers(1, len(chars) + 1)), str(rng.choice(['\'', '"', '.', '-'])))
                    g = render_run(font, chars, rng)
                    if g is None: continue
                elif cls == 'frag':
                    src = str(rng.choice(list(DIG + CAP) if 'd' in use else list(CAP)))
                    key = (font, src)
                    if key not in cache: cache[key] = render(font, src)
                    m = jitter(cache[key], slant, src, rng)
                    m = cut_frag(m, rng) if m is not None else None
                    if m is None or m.sum() < 6: continue
                    masks.append(m); labels.append(cls); fonts.append(font); got += 1; continue
                else:
                    key = (font, cls)
                    if key not in cache: cache[key] = render(font, cls)
                    g = cache[key]
                m = jitter(g, slant, 'pair' if cls == 'run' else cls, rng)
                if m is None or m.sum() < 6: continue
                masks.append(m); labels.append(cls); fonts.append(font); got += 1
        print(font, len(masks), flush=True)
    bits = [np.packbits(m.ravel()) for m in masks]; off = np.r_[0, np.cumsum([len(b) for b in bits])]
    hw = np.array([m.shape for m in masks], np.int32)
    out = os.path.join(HERE, '..', 'data', 'synth.npz')
    np.savez_compressed(out, bits=np.concatenate(bits), off=off, hw=hw, label=np.array(labels), font=np.array(fonts))
    # a picture of a few samples per font
    rows = []
    for font, _, _ in FONTS:
        idx = [i for i, f in enumerate(fonts) if f == font]; pick = rng.choice(idx, min(40, len(idx)), replace=False)
        row = np.full((44, 40 * 44), 255, np.uint8)
        for j, i in enumerate(pick):
            m = masks[i]; s = 40 / max(m.shape); r = cv2.resize(m.astype(np.uint8) * 255, (max(1, int(m.shape[1] * s)), max(1, int(m.shape[0] * s))), interpolation=cv2.INTER_AREA)
            row[2:2 + r.shape[0], j * 44 + 2:j * 44 + 2 + r.shape[1]] = 255 - r
        rows.append(row)
    cv2.imwrite(os.path.join(HERE, '..', 'pics', 'synth_samples.png'), np.vstack(rows))
    print(len(masks), 'synthetic glyphs ->', out)


if __name__ == '__main__':
    main()
