"""Character finder v3 (finder3, 26 Nov 2026): finder v2 plus a character-or-not classifier as a second opinion.

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/code/finder3.py N [--win X0 Y0 X1 Y1] [--out DIR] [--pic] [--tag NAME]
           [--model PATH] [--combiner PATH | --no-combiner] [--off] [--save-state DIR]

Output N_text.png (default DIR: text_v1/classifier/out/finder3), the hand-off codes of finder2 (text_first.md section 6):
0 paper, 1 line ink, 2 text sure, 3 text by context, 4 shared ink, 5 other ink. Text for scoring is codes 2 and 3.
No truth is read at run time: only the scan, its paper mask, scale_table.json and the classifier's weights.

How:
  A. finder2.py runs unchanged (imported). Its last step (shared_ink) is held back, and three of its inner results are
     kept: the pieces (8-connected ink less the line ink grown 1 px) with their kinds, which strokes are dashes of a
     dashed line or carry on a line (chains) or are rail-tick ends (tick_ends), and the big-letter mask (big_letters).
  B. Every piece 8-140 px across is shown to the classifier (classifier/scripts/model_np.py, numpy only; weights in
     classifier/out/model_cnn2.npz by default): a small CNN (3 convolutions, 0.17 M weights) on the piece's 32 x 32
     image and 10 shape numbers, fitted on the CPU on Claude's cluster labels, synthetic font glyphs and junk
     (classifier/scripts/train.py cnn). Its answer is put together with finder2's own call, the piece's kind, size and line
     contact, and the text and line ink round it, by a small COMBINER net (classifier/scripts/stack.py; weights in
     classifier/out/combiner_cnn2.npz, fitted on the truth v2 T1-T7 pieces), giving P(text). P(junk) = 1 - P(text).
     --model/--combiner pick others (e.g. the HOG pair *_mlp2.npz).
       TEXT -> OTHER (code 5): a piece finder2 calls text (codes 2/3 on most of its ink) whose P(junk) is tj or more
         (P(text) 0.4 or less).
         Never a piece half or more inside a big letter (big lettering is judged by finder2's own rules: street names
         and block numbers must not lose strokes to a classifier fitted on small glyphs), and never a free stroke
         (kind stroke touching no line ink): figure 1s, story heights and the I's of spaced railroad names look like
         dashes, and on T1-T7 taking free strokes out lost as much text as it removed junk (net -21 px), with 4 railroad
         letters lost on T2.
       OTHER -> TEXT (code 3): a piece finder2 left as other ink (code 5 on most of its ink) whose P(text) is tt (0.6) or more,
         that is ext_min px across or more and has other text within ctx px of its box. Never a rail tick end, a
         dash of a dashed line or a piece carrying on a line (finder2's chains), a streetcar dash (kind bar), a ring,
         box or building outline, nor a bit ctx_tip px across or less that touches line ink (it may be a tick's tip):
         Ben's rule, never a rail tick or streetcar dash, not even the tip.
     Line ink (code 1) is never changed.
  C. finder2's shared_ink then runs on the result, as in finder2.
Thresholds (P3 below) were set on truth v2 T1-T7 only (classifier/scripts/tune_stack.py); the held-out crops were never
seen. The combiner is fitted on the T1-T7 pieces, so a score of this mask on T1-T7 is in-sample (F1 0.9445); the honest
T1-T7 number is leave one crop out (F1 0.9415, classifier/out/scores/finder3_cnn2_loco_codes23.txt; finder2 0.9367).
To refit without some windows (e.g. held-out ones): classifier/scripts/train_overlap.py says the recipe.
"""
import json, os, sys, time
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import finder2  # noqa: E402
CLS = os.path.normpath(os.path.join(HERE, '..', 'classifier', 'scripts')); sys.path.insert(0, CLS)
from common import piece_features  # noqa: E402
from model_np import load_model, predict  # noqa: E402
# The shape classifier is the small CNN (model_cnn2.npz with combiner_cnn2.npz). On T1-T7 the net on HOG + blurred pixels +
# shape numbers (model_mlp2.npz, combiner_mlp2.npz) is about as good (dev AUC of P(junk) 0.9301 against 0.9311; combiner
# AUC leave one crop out 0.9685 against 0.9708; mask F1 leave one crop out 0.9411 against 0.9415). But on Ben's checked
# lines and rail (classifier/out/checks, 26 Nov) the HOG pair turned two stubs of a line on 1A (172 px of his line ink) and
# one 60 px piece lying along a railroad track on 44 into text; the CNN pair did neither. So the CNN pair is the default.
MODEL = os.path.normpath(os.path.join(HERE, '..', 'classifier', 'out', 'model_cnn2.npz'))
COMBINER = os.path.normpath(os.path.join(HERE, '..', 'classifier', 'out', 'combiner_cnn2.npz'))
# tj, tt: set on truth v2 T1-T7 from leave-one-crop-out combiner predictions (classifier/scripts/tune_stack.py, 26 Nov):
# best pooled F1 at P(text) <= 0.4 for text -> other and P(text) >= 0.6 for other -> text (CNN pair; the mlp pair is
# equal there, 0.9411, and best-by-0.00004 at tj 0.7, so the same values are kept). ext_min 8 gave the same F1 with more
# small flips, so 10 is kept (fewer small bits near lines).
P3 = dict(ext=(8, 140), tj=0.6, tt=0.6, ext_min=10, ctx=30, ctx_tip=12, letter=0.5, keep_free_strokes=True,
          tj_kinds=('glyph', 'cluster', 'stroke', 'dot', 'eq', 'jog', 'blob', 'long'), tt_kinds=('stroke', 'dot', 'blob', 'jog', 'long', 'glyph'))
FKEYS = ('A', 'long', 'thick', 'sw', 'holes', 'touch', 'ext')


def stage_a(N, win=None):
    """finder2 as it is, holding back shared_ink; returns the state finder3 needs (no full-size label image kept)"""
    cap = {}
    real = (finder2.shared_ink, finder2.chains, finder2.big_letters)
    def sh(code, ink): cap['pre'] = code.copy(); return code, 0
    def ch(F, idx, ori, line):
        r = real[1](F, idx, ori, line); cap['chain_idx'] = np.asarray(idx); cap['chain_bad'] = r[0]; return r
    def bl(*a, **k):
        r = real[2](*a, **k); cap['letter'] = r[0].copy(); return r
    finder2.shared_ink, finder2.chains, finder2.big_letters = sh, ch, bl
    try: _, rec, (n, lb, F, k) = finder2.run(N, win, None, False, None, verbose=False)
    finally: finder2.shared_ink, finder2.chains, finder2.big_letters = real
    pre = cap['pre']; m = lb > 0
    isdash = np.zeros(n, bool)
    if len(cap.get('chain_idx', [])): isdash[cap['chain_idx'][cap['chain_bad']]] = True
    isdash |= (k == 'tick')
    letter = cap.get('letter', np.zeros(pre.shape, np.uint8))
    inl = np.bincount(lb[m & (letter > 0)], minlength=n) / np.maximum(np.bincount(lb[m], minlength=n), 1)
    cc = np.zeros((n, 6), np.int64)
    for v in range(6): cc[:, v] = np.bincount(lb[m & (pre == v)], minlength=n)
    bits = []; off = np.zeros(n, np.int64)
    bx, by, bw, bh = F['bx'], F['by'], F['bw'], F['bh']
    for i in range(1, n):
        x, y, w, h = int(bx[i]), int(by[i]), int(bw[i]), int(bh[i])
        b = np.packbits((lb[y:y + h, x:x + w] == i).ravel()); bits.append(b); off[i] = off[i - 1] + len(b)
    S = dict(plate=N, win=win, rec=rec, pre=pre, letter=letter, bbox=np.c_[bx, by, bw, bh][1:].astype(np.int32), kind=np.array(k[1:], dtype='U8'),
             codes=cc[1:].astype(np.int32), isdash=isdash[1:], inletter=inl[1:].astype(np.float32),
             bits=np.concatenate(bits) if bits else np.zeros(0, np.uint8), off=np.r_[0, off[1:]])
    for q in FKEYS: S[f'f_{q}'] = np.asarray(F[q])[1:].astype(np.float32)
    return S


def piece_mask(S, i):
    x, y, w, h = S['bbox'][i]; return np.unpackbits(S['bits'][S['off'][i]:S['off'][i + 1]])[:w * h].reshape(h, w)


def text_near(pre, bbox, own, r):
    t = np.isin(pre, (2, 3)).astype(np.uint8); ii = cv2.integral(t); H, W = t.shape
    x0 = np.clip(bbox[:, 0] - r, 0, W); y0 = np.clip(bbox[:, 1] - r, 0, H); x1 = np.clip(bbox[:, 0] + bbox[:, 2] + r, 0, W); y1 = np.clip(bbox[:, 1] + bbox[:, 3] + r, 0, H)
    return (ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0]) - own


def classify(S, M, ext=None, combiner=None):
    """P(junk) for every piece in the size range (nan elsewhere), and the classes' probabilities. With a combiner (dict
    from stack.py), P(junk) = 1 - the combiner's P(text); otherwise the shape classifier's own P(junk)"""
    ext = ext or P3['ext']; e = np.maximum(S['bbox'][:, 2], S['bbox'][:, 3]); sel = np.nonzero((e >= ext[0]) & (e <= ext[1]))[0]
    img, sc = piece_features([piece_mask(S, i) for i in sel]); pr = predict(M, img, sc)
    pj = np.full(len(e), np.nan, np.float32)
    if combiner is None: pj[sel] = pr[:, M['classes'].index('junk')]
    else:
        import stack
        pj[sel] = 1 - stack.apply(combiner, stack.features(S, pr, sel, M['classes']))
    return pj, sel, pr


def stage_b(S, pj, p=None):
    """apply the second opinion to the pre-shared code; returns the new code and the flips"""
    p = dict(P3, **(p or {})); pre = S['pre']; code = pre.copy(); cc = S['codes']; tot = np.maximum(cc.sum(1), 1)
    istext = (cc[:, 2] + cc[:, 3]) >= 0.5 * tot; isother = cc[:, 5] >= 0.5 * tot
    e = np.maximum(S['bbox'][:, 2], S['bbox'][:, 3]); k = S['kind']; ok = ~np.isnan(pj)
    tj = ok & istext & (pj >= p['tj']) & np.isin(k, p['tj_kinds']) & (S['inletter'] < p['letter'])
    if p.get('keep_free_strokes'): tj &= ~((k == 'stroke') & (S['f_touch'] == 0))
    near = text_near(pre, S['bbox'], cc[:, 2] + cc[:, 3], p['ctx']) > 0
    tip = (S['f_touch'] > 0) & (e <= p['ctx_tip'])
    tt = ok & isother & ((1 - pj) >= p['tt']) & np.isin(k, p['tt_kinds']) & (e >= p['ext_min']) & near & ~S['isdash'] & ~tip
    for i in np.nonzero(tj | tt)[0]:
        x, y, w, h = S['bbox'][i]; m = piece_mask(S, i) > 0; sub = code[y:y + h, x:x + w]
        if tj[i]: sub[m & np.isin(sub, (2, 3))] = 5
        else: sub[m & (sub == 5)] = 3
    return code, dict(to_other=int(tj.sum()), to_text=int(tt.sum()), to_other_px=int(cc[tj][:, 2:4].sum()), to_text_px=int(cc[tt][:, 5].sum()))


def run(N, win=None, out=None, pic=False, tag=None, model=MODEL, off=False, save_state=None, verbose=True, combiner=COMBINER):
    t0 = time.time(); S = stage_a(N, win); ta = time.time() - t0
    if save_state:
        os.makedirs(save_state, exist_ok=True)
        np.savez_compressed(os.path.join(save_state, f'{N}.npz'), **{k: (v if k not in ('rec', 'win') else json.dumps(v)) for k, v in S.items() if k not in ('pre', 'letter')},
                            pre=np.frombuffer(cv2.imencode('.png', S['pre'])[1].tobytes(), np.uint8), letter=np.frombuffer(cv2.imencode('.png', S['letter'])[1].tobytes(), np.uint8))
    info = dict(off=off)
    if off: code = S['pre']
    else:
        M = load_model(model); C = dict(np.load(combiner)) if combiner else None
        pj, sel, _ = classify(S, M, combiner=C); code, info = stage_b(S, pj); info['classified'] = int(len(sel))
        info['model'] = os.path.relpath(model, os.getcwd()); info['combiner'] = os.path.relpath(combiner, os.getcwd()) if combiner else None
    ink = (code > 0).astype(np.uint8); code, nsh = finder2.shared_ink(code, ink)
    rec = S['rec']; rec.update(finder='finder3', classifier=info, P3={k: v for k, v in P3.items()}, px={nm: int((code == v).sum()) for nm, v in finder2.CODE.items()},
                               seconds=dict(rec['seconds'], finder2_total=round(ta, 1), finder3_total=round(time.time() - t0, 1)), made=time.strftime('%Y-%m-%d %H:%M'))
    if out:
        os.makedirs(out, exist_ok=True); stem = os.path.join(out, f'{N}_text' + (f'_{tag}' if tag else ''))
        cv2.imwrite(stem + '.png', code); json.dump(rec, open(stem + '.json', 'w', encoding='utf8', newline='\n'), indent=1, default=str)
        if pic:
            im = cv2.imread(f'cufp/22-{N}.jpg')
            if win: im = im[win[1]:win[3], win[0]:win[2]]
            c = finder2.overlay(im, code); cv2.imwrite(stem + '.jpg', c if win else cv2.resize(c, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])
    if verbose: print(f'finder3 plate {N}: {info} | finder2 part {ta:.0f} s, total {time.time() - t0:.0f} s', flush=True)
    return code, rec


if __name__ == '__main__':
    a = sys.argv; N = a[1]
    win = tuple(int(v) for v in a[a.index('--win') + 1:a.index('--win') + 5]) if '--win' in a else None
    out = a[a.index('--out') + 1] if '--out' in a else os.path.join(HERE, '..', 'classifier', 'out', 'finder3')
    tag = a[a.index('--tag') + 1] if '--tag' in a else None
    model = a[a.index('--model') + 1] if '--model' in a else MODEL
    ss = a[a.index('--save-state') + 1] if '--save-state' in a else None
    comb = None if '--no-combiner' in a else (a[a.index('--combiner') + 1] if '--combiner' in a else COMBINER)
    run(N, win, out, '--pic' in a, tag, model, '--off' in a, ss, combiner=comb)
