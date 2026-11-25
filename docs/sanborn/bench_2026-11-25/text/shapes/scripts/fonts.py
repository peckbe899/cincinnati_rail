"""Template matching of glyphs against fonts installed on this machine (C:/Windows/Fonts), shapes prototype 25 Nov 2026.

    python -B bench_2026-11-25/text/shapes/scripts/fonts.py            (from data/sanborn)

Nothing is downloaded: only .ttf files already in C:/Windows/Fonts are read (PIL ImageFont).
Templates: 0-9 and A-Z rendered at 96 px in each font of FONTS, binarised, cropped tight, then normalised as the
plate glyphs are (extract_glyphs.norm_glyph: longest side 28 px in 32 x 32). An upright font is also sheared to a
slant of 0.25 (the house numbers lean about that much), an italic font is used as it is.
Match: features of cluster.py without the size part (blurred 16 x 16 pixels + HOG, each scaled to unit length), plus
0.6 x the difference of log(width/height); the nearest template wins (1-NN).
Test glyphs: the glyphs that carry a cluster label (claude_round1/2.json, the training set of classify.py, strays
left out as there), up to 200 per class drawn at random (seed 0). These labels are Claude's, by cluster, not
checked one by one; they are right for roughly 9 in 10 to 19 in 20 glyphs (by eye on the montages).
Writes fonts_result.json and look/font_templates.png (the templates of the best fonts).
"""
import json, os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster import features, load, HERE  # noqa: E402
from extract_glyphs import norm_glyph  # noqa: E402

FD = 'C:/Windows/Fonts/'
FONTS = {   # file: italic?
    'ariali.ttf': 1, 'ARIALNI.TTF': 1, 'GOTHICI.TTF': 1, 'framdit.ttf': 1, 'FRABKIT.TTF': 1, 'TCMI____.TTF': 1, 'GILI____.TTF': 1,
    'DejaVuSansCondensed-Oblique.ttf': 1, 'LiberationSansNarrow-Italic.ttf': 1, 'calibrii.ttf': 1, 'Candarai.ttf': 1, 'trebucit.ttf': 1,
    'LSANSI.TTF': 1, 'SCHLBKI.TTF': 1, 'BOOKOSI.TTF': 1, 'segoeuii.ttf': 1, 'verdanai.ttf': 1,
    'arial.ttf': 0, 'ARIALN.TTF': 0, 'GOTHIC.TTF': 0, 'framd.ttf': 0, 'FRABK.TTF': 0, 'TCM_____.TTF': 0, 'GIL_____.TTF': 0, 'bahnschrift.ttf': 0,
    'DejaVuSansCondensed.ttf': 0, 'LiberationSansNarrow-Regular.ttf': 0, 'segoeui.ttf': 0,
    'arialbd.ttf': 0, 'ARIALNB.TTF': 0, 'GOTHICB.TTF': 0, 'FRADM.TTF': 0, 'FRADMCN.TTF': 0, 'FRAHV.TTF': 0, 'TCB_____.TTF': 0, 'TCCB____.TTF': 0,
    'GILB____.TTF': 0, 'DejaVuSans-Bold.ttf': 0, 'DejaVuSansCondensed-Bold.ttf': 0, 'LiberationSansNarrow-Bold.ttf': 0, 'COPRGTB.TTF': 0,
    'ERASDEMI.TTF': 0, 'BRLNSDB.TTF': 0, 'segoeuib.ttf': 0, 'verdanab.ttf': 0, 'trebucbd.ttf': 0, 'ENGR.TTF': 0,
}
CHARS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
SLANT = 0.25; W_ASP = 0.6


def render(path, ch, slant=0.0, size=96):
    f = ImageFont.truetype(path, size)
    im = Image.new('L', (size * 3, size * 3), 0); ImageDraw.Draw(im).text((size, size // 2), ch, font=f, fill=255)
    a = (np.array(im) > 127).astype(np.uint8)
    if slant:
        h, w = a.shape; M = np.float32([[1, -slant, slant * h], [0, 1, 0]])   # top leans right
        a = (cv2.warpAffine(a.astype(np.float32), M, (w + int(slant * h) + 2, h)) > 0.5).astype(np.uint8)
    ys, xs = np.nonzero(a)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1] if len(xs) else None


def shape_feats(imgs):
    F = features(imgs, np.ones((len(imgs), 2), np.float32))
    return F[:, :-2]


def templates(fonts):
    T = []; lab = []; asp = []; src = []
    for fn, ital in fonts.items():
        for sl in ([0.0] if ital else [0.0, SLANT]):
            for ch in CHARS:
                t = render(FD + fn, ch, sl)
                if t is None: continue
                T.append(norm_glyph(t)); lab.append(ch); asp.append(np.log(t.shape[1] / t.shape[0])); src.append(f'{fn}{"/" + str(sl) if sl else ""}')
    return np.stack(T), np.array(lab), np.array(asp), np.array(src)


def match(Fq, aq, Ft, at):
    d = (Fq ** 2).sum(1)[:, None] + (Ft ** 2).sum(1)[None] - 2 * Fq @ Ft.T + (W_ASP * (aq[:, None] - at[None])) ** 2
    return d.argmin(1), np.sqrt(np.maximum(d.min(1), 0))


def main():
    G = load()
    M = np.load(os.path.join(HERE, 'model.npz'), allow_pickle=True)
    P = np.load(os.path.join(HERE, 'pred.npz'), allow_pickle=True)
    key = {(p, int(i)): j for j, (p, i) in enumerate(zip(G['plate'], G['idx']))}
    tj = np.array([key[(p, int(i))] for p, i in zip(P['train_plate'], P['train_idx'])]); ty = P['train_y']
    rng = np.random.default_rng(0); sel = []
    for c in sorted(set(ty) - {'junk'}):
        w = np.nonzero(ty == c)[0]; sel.append(rng.choice(w, min(200, len(w)), replace=False))
    sel = np.concatenate(sel); qj = tj[sel]; qy = ty[sel]
    Fq = shape_feats(G['imgs'][qj]); aq = np.log(G['hw'][qj, 1] / G['hw'][qj, 0])
    T, tl, ta, ts = templates(FONTS); Ft = shape_feats(T)
    digit = np.array([c.isdigit() for c in qy]); cap = ~digit
    res = {}; isd = np.array([c.isdigit() for c in tl])
    def score(m):
        b, _ = match(Fq, aq, Ft[m], ta[m]); pr = tl[m][b]
        bd, _ = match(Fq[digit], aq[digit], Ft[m & isd], ta[m & isd]); bc, _ = match(Fq[cap], aq[cap], Ft[m & ~isd], ta[m & ~isd])
        return dict(digits=float((pr[digit] == qy[digit]).mean()), capitals=float((pr[cap] == qy[cap]).mean()),
                    digits_among_digits=float((tl[m & isd][bd] == qy[digit]).mean()), capitals_among_letters=float((tl[m & ~isd][bc] == qy[cap]).mean())), pr
    for fn in FONTS:
        res[fn], _ = score(np.array([s.split('/')[0] == fn for s in ts]))
    res['ALL FONTS POOLED'], pr = score(np.ones(len(ts), bool))
    bd, _ = match(Fq[digit], aq[digit], Ft[isd], ta[isd]); prd = tl[isd][bd]
    per = {c: float((pr[qy == c] == c).mean()) for c in sorted(set(qy))}
    order = sorted(res, key=lambda f: -res[f]['digits_among_digits'])
    print(f'test glyphs: {int(digit.sum())} digits, {int(cap.sum())} capitals (classes {sorted(set(qy[cap]))})')
    print('  font                                 digits (all templates / digit templates only)   capitals (all / letter templates only)')
    for f in order: print(f"  {f:36s} {res[f]['digits']:.3f} / {res[f]['digits_among_digits']:.3f}      {res[f]['capitals']:.3f} / {res[f]['capitals_among_letters']:.3f}")
    print('pooled, per class:', ', '.join(f'{c} {v:.2f}' for c, v in per.items()))
    print('pooled, digits among digit templates only, per class:', ', '.join(f'{c} {float((prd[qy[digit] == c] == c).mean()):.2f}' for c in '0123456789'))
    conf = {}
    for t, p in zip(qy[digit], prd):
        if t != p: conf[f'{t}->{p}'] = conf.get(f'{t}->{p}', 0) + 1
    print('pooled digit confusions among digit templates (most common):', sorted(conf.items(), key=lambda x: -x[1])[:12])
    json.dump(dict(note='fonts.py: 1-NN against font templates; reference = cluster labels (Claude, by cluster), up to 200 per class', n_digits=int(digit.sum()),
                   n_capitals=int(cap.sum()), per_font=res, pooled_per_class=per, pooled_digit_confusions=conf),
              open(os.path.join(HERE, 'fonts_result.json'), 'w'), indent=1)
    # picture of the templates of the 4 best fonts for digits and 4 best for capitals
    best = [f for f in order if f != 'ALL FONTS POOLED'][:4]
    bestc = [f for f in sorted(res, key=lambda f: -res[f]['capitals_among_letters']) if f != 'ALL FONTS POOLED'][:4]
    rows = []
    for fn in best + bestc:
        m = np.array([s == fn for s in ts]); r = np.hstack([255 - np.pad(t, 2, constant_values=0) for t in T[m]])
        lab = np.full((36, 260), 255, np.uint8); cv2.putText(lab, fn, (2, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 0, 1)
        rows.append(np.hstack([lab, r]))
    cv2.imwrite(os.path.join(HERE, 'look', 'font_templates.png'), np.vstack(rows))
    np.savez_compressed(os.path.join(HERE, 'font_templates.npz'), T=T, label=tl, asp=ta, src=ts)


if __name__ == '__main__':
    main()
