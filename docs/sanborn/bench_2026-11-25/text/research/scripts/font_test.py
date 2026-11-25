"""Which fonts already on this machine look like Sanborn's hand-lettered digits?
For each candidate font: render 0-9 (2,000 synthetic samples: slant, stroke weight, size, small rotation,
blur and noise drawn at random), fit a classifier on those synthetic samples ONLY, and test it on the real
upright digits hand-labelled in out/label_sample_44.json (a random sample of plate 44's single-glyph text
pieces, read by eye). Two classifiers per font:
  - template: the mean synthetic image of each digit, nearest by correlation (template matching);
  - svm: HOG features + RBF SVM (cv2.ml), fitted on the synthetic samples.
Also: 'real LOO' = 1-nearest-neighbour on the real digits themselves, leave-one-out (fitted on real glyphs).
And 'mix top-5': svm fitted on the five best fonts together.
Writes out/font_test.json and pics/font_samples.png (each font's digits beside real ones).
CPU only, no download. Usage: python -B font_test.py"""
import os, json, cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont


def skel_len(m):
    """stroke length ~ half the outline length (outer and inner contours)"""
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    return sum(cv2.arcLength(c, True) for c in cs) / 2.0

R = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D'
B = os.path.join(R, 'data/sanborn/bench_2026-11-25/text/research')
F = 'C:/Windows/Fonts/'
S = 32
rng = np.random.default_rng(0)


def norm(mask):
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        return np.zeros((S, S), np.float32)
    mask = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = mask.shape
    s = 26.0 / max(h, w)
    m = cv2.resize(mask.astype(np.float32), (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA)
    out = np.zeros((S, S), np.float32)
    y, x = (S - m.shape[0]) // 2, (S - m.shape[1]) // 2
    out[y:y + m.shape[0], x:x + m.shape[1]] = m
    return cv2.GaussianBlur(out, (3, 3), 0.8)


# ---- real digits (plate 44, hand-labelled) ----
code = cv2.imread(os.path.join(R, 'data/sanborn/unet_data/44_bins.png'), cv2.IMREAD_UNCHANGED)
t = (code == 8).astype(np.uint8)
lab_d = json.load(open(os.path.join(B, 'out/label_sample_44.json')))
realX, realY, realM = [], [], []
for (x, y, w, h), L in zip(lab_d['boxes'], lab_d['labels']):
    if len(L) == 1 and L.isdigit():
        sub = t[y:y + h, x:x + w]
        n, lab, st, _ = cv2.connectedComponentsWithStats(sub, connectivity=8)
        k = 1 + np.argmax(st[1:, 4])          # the piece that fills the box
        m = (lab == k)
        realM.append(m); realX.append(norm(m)); realY.append(int(L))
realX, realY = np.array(realX), np.array(realY)
print('real upright digits', len(realY), np.bincount(realY, minlength=10).tolist())
# stroke-to-height ratio of the real digits, to set the synthetic stroke weight
ratios = []
for m in realM:   # stroke width = ink area / skeleton length, over glyph height
    ratios.append(m.sum() / max(1, skel_len(m)) / m.shape[0])
REAL_RATIO = float(np.median(ratios))
print('real stroke / height', round(REAL_RATIO, 3))

# ---- candidate fonts ----
TTF = ['ariali.ttf', 'arial.ttf', 'ARIALNI.TTF', 'LiberationSans-Italic.ttf', 'LiberationSansNarrow-Italic.ttf',
       'DejaVuSans-Oblique.ttf', 'DejaVuSansCondensed-Oblique.ttf', 'GOTHICI.TTF', 'GOTHIC.TTF', 'framdit.ttf',
       'FRADMIT.TTF', 'FRAMDCN.TTF', 'TCMI____.TTF', 'TCCM____.TTF', 'segoeuii.ttf', 'calibrii.ttf', 'verdanai.ttf',
       'trebucit.ttf', 'comici.ttf', 'segoepr.ttf', 'Inkfree.ttf', 'LHANDW.TTF', 'consolai.ttf', 'couri.ttf',
       'timesi.ttf', 'bahnschrift.ttf', 'tahoma.ttf', 'AGENCYR.TTF', 'COPRGTL.TTF', 'GILC____.TTF', 'Candarai.ttf',
       'corbeli.ttf', 'NotoSans-Italic.ttf', 'Rubik-Italic.ttf', 'mvboli.ttf', 'segoesc.ttf']
HERSHEY = {'hershey_simplex_italic': cv2.FONT_HERSHEY_SIMPLEX | cv2.FONT_ITALIC,
           'hershey_plain_italic': cv2.FONT_HERSHEY_PLAIN | cv2.FONT_ITALIC,
           'hershey_duplex_italic': cv2.FONT_HERSHEY_DUPLEX | cv2.FONT_ITALIC,
           'hershey_complex_italic': cv2.FONT_HERSHEY_COMPLEX | cv2.FONT_ITALIC,
           'hershey_simplex': cv2.FONT_HERSHEY_SIMPLEX,
           'hershey_script_simplex': cv2.FONT_HERSHEY_SCRIPT_SIMPLEX}
ITALIC_NAMES = ('i.ttf', 'I.TTF', 'Oblique', 'Italic', 'MI____', 'dit.', 'DMIT', 'italic', 'NI.TTF', 'it.ttf', 'LHANDW', 'segoepr', 'Inkfree', 'segoesc', 'comici')


def render_ttf(path, ch, size=64):
    f = ImageFont.truetype(path, size)
    im = Image.new('L', (size * 2, size * 2), 0)
    ImageDraw.Draw(im).text((size // 2, size // 3), ch, fill=255, font=f)
    return np.array(im) > 127


def render_hershey(face, ch):
    im = np.zeros((160, 160), np.uint8)
    cv2.putText(im, ch, (30, 110), face, 2.5, 255, 3, cv2.LINE_AA)
    return im > 127


def synth(glyph, slant_extra):
    """one augmented sample from a big clean glyph mask"""
    m = glyph.astype(np.uint8) * 255
    ys, xs = np.nonzero(m); m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    m = cv2.copyMakeBorder(m, 20, 20, 30, 30, cv2.BORDER_CONSTANT, 0)
    h, w = m.shape
    sh = -slant_extra + rng.normal(0, 0.06)                      # shear; negative = top leans right (image y runs down)
    rot = np.deg2rad(rng.normal(0, 3))
    A = np.array([[np.cos(rot), -np.sin(rot) + sh, 0], [np.sin(rot), np.cos(rot), 0]], np.float32)
    A[:, 2] = np.array([w / 2, h / 2]) - A[:, :2] @ np.array([w / 2, h / 2])
    m = cv2.warpAffine(m, A, (w, h))
    ys, xs = np.nonzero(m > 127); m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    th = rng.uniform(18, 34)                                    # glyph height on the scan, px
    sc = th / m.shape[0]
    m = cv2.resize(m, (max(2, int(m.shape[1] * sc * rng.uniform(0.85, 1.15))), max(2, int(th))), interpolation=cv2.INTER_AREA)
    m = cv2.copyMakeBorder(m, 6, 6, 6, 6, cv2.BORDER_CONSTANT, 0) > 110
    # match the stroke weight of the real digits (+/- jitter) by dilating/eroding
    # stroke width = ink area / skeleton length (same measure as for the real digits below)
    cur = m.sum() / max(1, skel_len(m))
    want = REAL_RATIO * th * rng.uniform(0.8, 1.2)
    d = int(np.clip(round((want - cur) / 2), -1, 3))
    k = np.ones((3, 3), np.uint8)
    mm = m.astype(np.uint8)
    if d > 0: mm = cv2.dilate(mm, k, iterations=d)
    elif d < 0:
        e = cv2.erode(mm, k, iterations=1)
        if e.sum() >= 0.45 * mm.sum(): mm = e
    # ragged ink edge; keep the clean glyph if the noise would eat it
    g = (cv2.GaussianBlur(mm.astype(np.float32), (3, 3), 0.6) + rng.normal(0, 0.1, mm.shape)) > 0.5
    return g if g.sum() >= 0.7 * mm.sum() else mm.astype(bool)


hog = cv2.HOGDescriptor((32, 32), (16, 16), (8, 8), (8, 8), 9)


def hogf(X):
    return np.array([hog.compute((x * 255).clip(0, 255).astype(np.uint8)).ravel() for x in X], np.float32)


def fit_eval(Xs, Ys, label):
    # template matching: class means, nearest by correlation
    T = np.array([Xs[Ys == c].mean(0).ravel() for c in range(10)])
    T = (T - T.mean(1, keepdims=True)) / (T.std(1, keepdims=True) + 1e-6)
    Q = realX.reshape(len(realX), -1); Q = (Q - Q.mean(1, keepdims=True)) / (Q.std(1, keepdims=True) + 1e-6)
    acc_t = float(((Q @ T.T).argmax(1) == realY).mean())
    svm = cv2.ml.SVM_create(); svm.setType(cv2.ml.SVM_C_SVC); svm.setKernel(cv2.ml.SVM_RBF)
    svm.setC(10); svm.setGamma(0.5)
    Hs = hogf(Xs); Hr = hogf(realX)
    svm.train(Hs, cv2.ml.ROW_SAMPLE, Ys.astype(np.int32))
    pred = svm.predict(Hr)[1].ravel().astype(int)
    acc_s = float((pred == realY).mean())
    conf = np.zeros((10, 10), int)
    for a, b in zip(realY, pred): conf[a, b] += 1
    return {'font': label, 'template_acc': round(acc_t, 3), 'svm_acc': round(acc_s, 3), 'svm_confusion_true_by_pred': conf.tolist()}


results, synth_sets, samples = [], {}, {}
fonts = [(n, 'ttf') for n in TTF if os.path.exists(F + n)] + [(n, 'hershey') for n in HERSHEY]
for name, kind in fonts:
    try:
        glyphs = [render_ttf(F + name, str(c)) if kind == 'ttf' else render_hershey(HERSHEY[name], str(c)) for c in range(10)]
    except Exception as e:
        print(name, 'failed', e); continue
    is_it = kind == 'hershey' and 'italic' in name or any(s in name for s in ITALIC_NAMES)
    slant = 0.0 if is_it else 0.25                              # upright fonts get a Sanborn-like slant
    Xs, Ys = [], []
    for c in range(10):
        for _ in range(200):
            g = synth(glyphs[c], slant); Xs.append(norm(g)); Ys.append(c)
    Xs, Ys = np.array(Xs), np.array(Ys)
    r = fit_eval(Xs, Ys, name + ('' if is_it else ' (+slant 0.25)'))
    results.append(r); synth_sets[name] = (Xs, Ys); samples[name] = [synth(glyphs[c], slant) for c in range(10)]
    print(f"{r['font']:45s} template {r['template_acc']:.3f}  svm {r['svm_acc']:.3f}")
results.sort(key=lambda r: -r['svm_acc'])
top = [r['font'].split(' ')[0] for r in results[:5]]
Xm = np.concatenate([synth_sets[n][0] for n in top]); Ym = np.concatenate([synth_sets[n][1] for n in top])
mix = fit_eval(Xm, Ym, 'mix of top-5: ' + ', '.join(top))
print('MIX', mix['template_acc'], mix['svm_acc'])
# real-glyph leave-one-out 1-NN (HOG, L2) and LOO SVM
Hr = hogf(realX)
D = ((Hr[:, None] - Hr[None]) ** 2).sum(-1); np.fill_diagonal(D, 1e9)
loo_nn = float((realY[D.argmin(1)] == realY).mean())
ok = 0
for i in range(len(realY)):
    msk = np.arange(len(realY)) != i
    svm = cv2.ml.SVM_create(); svm.setType(cv2.ml.SVM_C_SVC); svm.setKernel(cv2.ml.SVM_RBF); svm.setC(10); svm.setGamma(0.5)
    svm.train(Hr[msk], cv2.ml.ROW_SAMPLE, realY[msk].astype(np.int32))
    ok += int(svm.predict(Hr[i:i + 1])[1].ravel()[0] == realY[i])
loo_svm = ok / len(realY)
print('real LOO 1-NN', round(loo_nn, 3), 'real LOO svm', round(loo_svm, 3))
# synthetic top-5 mix PLUS the other real digits (each real glyph repeated 10 times), leave-one-out
Hm = hogf(Xm); ok = 0; conf_mr = np.zeros((10, 10), int)
for i in range(len(realY)):
    msk = np.arange(len(realY)) != i
    Xtr = np.vstack([Hm] + [Hr[msk]] * 10); Ytr = np.concatenate([Ym] + [realY[msk]] * 10)
    svm = cv2.ml.SVM_create(); svm.setType(cv2.ml.SVM_C_SVC); svm.setKernel(cv2.ml.SVM_RBF); svm.setC(10); svm.setGamma(0.5)
    svm.train(Xtr, cv2.ml.ROW_SAMPLE, Ytr.astype(np.int32))
    pr = int(svm.predict(Hr[i:i + 1])[1].ravel()[0]); ok += int(pr == realY[i]); conf_mr[realY[i], pr] += 1
mix_real = ok / len(realY)
print('mix top-5 + real LOO svm', round(mix_real, 3))
json.dump({'n_real_digits': int(len(realY)), 'real_per_digit': np.bincount(realY, minlength=10).tolist(),
           'real_stroke_to_height': round(REAL_RATIO, 3), 'synthetic_per_font': 2000,
           'fonts_ranked_by_svm': results, 'mix_top5': mix,
           'real_leave_one_out_1nn_hog': round(loo_nn, 3), 'real_leave_one_out_svm_hog': round(loo_svm, 3), 'mix_top5_plus_real_leave_one_out_svm': round(mix_real, 3), 'mix_top5_plus_real_confusion': conf_mr.tolist(),
           'note': 'Synthetic fits see no real glyph. Real LOO fits see the other 112 real digits. One plate, one labeller (Claude by eye); small test set (113), so +/-0.04 is noise (binomial sd at 0.8).'},
          open(os.path.join(B, 'out/font_test.json'), 'w'), indent=1)
# picture: top 8 fonts and the real digits
show = [r['font'].split(' ')[0] for r in results[:8]] + [r['font'].split(' ')[0] for r in results[-3:]]
rows = []
for n in show:
    row = np.full((40, 120 + 10 * 36), 255, np.uint8)
    cv2.putText(row, n[:16], (2, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.38, 0, 1)
    for c in range(10):
        g = (norm(samples[n][c]) * 255).clip(0, 255).astype(np.uint8)
        row[4:36, 120 + c * 36:120 + c * 36 + 32] = 255 - g
    rows.append(row)
row = np.full((40, 120 + 10 * 36), 255, np.uint8); cv2.putText(row, 'REAL plate 44', (2, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.38, 0, 1)
for c in range(10):
    i = np.where(realY == c)[0]
    if len(i):
        row[4:36, 120 + c * 36:120 + c * 36 + 32] = 255 - (realX[i[0]] * 255).clip(0, 255).astype(np.uint8)
rows.insert(0, row)
cv2.imwrite(os.path.join(B, 'pics/font_samples.png'), cv2.resize(np.vstack(rows), None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST))
