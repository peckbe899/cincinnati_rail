"""Skeptic re-score (26 Nov 2026): my own pixel scorer for the held-out crops, written apart from score_text.py and the
gate's my_score.py (word boxes by matplotlib Path.contains_points on pixel centres, not cv2/PIL). Reads masks and truth only; writes only skeptic/out.

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/skeptic/scripts/sk_score.py [--truth heldfix|helddeliv] [--boot 2000]

What it adds to the gate's numbers:
  1. pooled P/R/F1 (should equal the gate's), and the plain mean of the 4 crop F1s (each crop counted once);
  2. F1 with one crop left out, each in turn;
  3. a tile bootstrap: each crop cut into 100 x 100 px tiles, tiles drawn with replacement (stratified by crop), pooled F1
     per method and the v3 - v2 and v2 - v1 differences; 2.5/50/97.5 percentiles and the share of draws with F1 >= 0.92;
  4. street-name and block-number recall by WORD (a word is found when >= 50% of its text px are found) and by pixel,
     word by word;
  5. a no-truth-used proxy for 'line ink called text' on the held-out plates: truth-1 ink (not text) in pieces that span
     >= 150 px (block lines, lot lines, building outlines), and the part of it on straight runs >= 61 px (opening with
     line kernels every 7.5 degrees). Ben's own lines exist only on 44, 5 and 1A, where the finders were tuned.
"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
from matplotlib.path import Path as MPath

B = 'bench_2026-11-25/text_v1'
TRUTHS = {'heldfix': f'{B}/truth-check/heldout_fixed', 'helddeliv': f'{B}/gate/truth_delivered',
          'v2': f'{B}/truth', 'v2fix': f'{B}/truth-check/truth_v2_fixed'}
METHODS = {
    'bin8': ('unet_data/{plate}_bins.png', (8,)),
    'v1': ('bench_2026-11-25/text/finder/out/{plate}_finder.png', (2, 3, 4)),
    'v2': (f'{B}/finder2/out/final/{{plate}}_text.png', (2, 3)),
    'v3': (f'{B}/classifier/out/finder3/{{plate}}_text.png', (2, 3)),
    'v3ex': (f'{B}/gate/out/v3ex/{{plate}}_text.png', (2, 3)),
}
a = sys.argv[1:]
tn = a[a.index('--truth') + 1] if '--truth' in a else 'heldfix'
NB = int(a[a.index('--boot') + 1]) if '--boot' in a else 2000
TD = TRUTHS[tn]
crops = json.load(open(os.path.join(TD, 'crops.json')))
ids = sorted(k for k in crops if os.path.exists(os.path.join(TD, f'{k}_mask.png')))
cache = {}


def pred(m, plate, win):
    pat, codes = METHODS[m]; p = pat.replace('{plate}', plate)
    if not os.path.exists(p): return None
    if p not in cache:
        x = cv2.imread(p, cv2.IMREAD_UNCHANGED); cache.clear(); cache[p] = x if x.ndim == 2 else x[..., 0]
    x0, y0, x1, y1 = win; return np.isin(cache[p][y0:y1, x0:x1], codes)


def lineish(t1):
    """t1: bool, truth-1 ink. Returns (big: pieces spanning >= 150 px, straight: on a straight run >= 61 px)"""
    n, lb, st, _ = cv2.connectedComponentsWithStats(t1.astype(np.uint8), connectivity=8)
    span = np.maximum(st[:, 2], st[:, 3]); keep = span >= 150; keep[0] = False; big = keep[lb]
    u = t1.astype(np.uint8); straight = np.zeros_like(t1)
    L = 61
    for ang in np.arange(0, 180, 7.5):
        k = np.zeros((L, L), np.uint8); c = L // 2; d = np.array([np.cos(np.radians(ang)), np.sin(np.radians(ang))])
        p0 = np.round(c - d * c).astype(int); p1 = np.round(c + d * c).astype(int); cv2.line(k, tuple(p0), tuple(p1), 1, 1)
        straight |= cv2.morphologyEx(u, cv2.MORPH_OPEN, k) > 0
    return big, straight


res = {}; T = {}
for tid in ids:
    c = crops[tid]; truth = cv2.imread(os.path.join(TD, f'{tid}_mask.png'), 0)
    words = json.load(open(os.path.join(TD, f'{tid}_words.json'), encoding='utf8'))['words']
    t1, t2 = truth == 1, truth == 2
    big, straight = lineish(t1)
    T[tid] = dict(truth=truth, words=words, big=big, straight=straight)
    for m in METHODS:
        p = pred(m, c['plate'], c['win'])
        if p is None: continue
        r = res.setdefault(m, {})
        tp, fp, fn = int((p & t2).sum()), int((p & t1).sum()), int((~p & t2).sum())
        # tiles for the bootstrap
        H, W = truth.shape; tiles = []
        for y in range(0, H, 100):
            for x in range(0, W, 100):
                s = (slice(y, y + 100), slice(x, x + 100)); tiles.append(((p[s] & t2[s]).sum(), (p[s] & t1[s]).sum(), (~p[s] & t2[s]).sum()))
        wk = []
        for w in words:
            if w['kind'] not in ('street', 'block') or not w.get('poly'): continue
            P = np.array(w['poly'], float) - [c['win'][0], c['win'][1]]
            xa, ya = np.clip(np.floor(P.min(0)).astype(int), 0, None); xb, yb = np.ceil(P.max(0)).astype(int) + 1
            xb, yb = min(xb, truth.shape[1]), min(yb, truth.shape[0]); wm = np.zeros(truth.shape, bool)
            if xb > xa and yb > ya:
                gx, gy = np.meshgrid(np.arange(xa, xb), np.arange(ya, yb)); inside = MPath(P).contains_points(np.c_[gx.ravel(), gy.ravel()], radius=0.5)
                wm[ya:yb, xa:xb] = inside.reshape(gy.shape)
            n = int((wm & t2).sum()); f = int((wm & t2 & p).sum())
            if n: wk.append(dict(reading=w["reading"], kind=w["kind"], flags=w.get("flags", []), text_px=n, found_px=f, found=bool(f >= 0.5 * n)))
        r[tid] = dict(tp=tp, fp=fp, fn=fn, t1=int(t1.sum()), tiles=np.array(tiles), words=wk,
                      big_px=int(big.sum()), big_called=int((big & p).sum()), str_px=int(straight.sum()), str_called=int((straight & p).sum()))


def prf(tp, fp, fn):
    P = tp / max(1, tp + fp); R = tp / max(1, tp + fn); return P, R, 2 * P * R / max(1e-12, P + R)


out = dict(truth=TD, methods={})
rng = np.random.default_rng(0)
idx = {tid: rng.integers(0, len(res['v2'][tid]['tiles']), size=(NB, len(res['v2'][tid]['tiles']))) for tid in ids}
boot = {}
for m, r in res.items():
    have = [t for t in ids if t in r]
    if not have: continue
    s = np.array([[r[t]['tp'], r[t]['fp'], r[t]['fn']] for t in have]).sum(0)
    P, R, F = prf(*s)
    per = {t: round(prf(r[t]['tp'], r[t]['fp'], r[t]['fn'])[2], 4) for t in have}
    loo = {}
    for t in have:
        s2 = np.array([[r[u]['tp'], r[u]['fp'], r[u]['fn']] for u in have if u != t]).sum(0); loo['without_' + t] = round(prf(*s2)[2], 4)
    if len(have) == len(ids):
        acc = np.zeros((NB, 3))
        for t in ids: acc += r[t]['tiles'][idx[t]].sum(1)
        Pb = acc[:, 0] / np.maximum(1, acc[:, 0] + acc[:, 1]); Rb = acc[:, 0] / np.maximum(1, acc[:, 0] + acc[:, 2]); Fb = 2 * Pb * Rb / np.maximum(1e-12, Pb + Rb)
        boot[m] = Fb
    words = [dict(crop=t, **w) for t in have for w in r[t]['words']]
    def kind(k):
        ws = [w for w in words if w['kind'] == k]
        return dict(words_found=f"{sum(w['found'] for w in ws)}/{len(ws)}", word_recall=round(sum(w['found'] for w in ws) / max(1, len(ws)), 4),
                    px_recall=round(sum(w['found_px'] for w in ws) / max(1, sum(w['text_px'] for w in ws)), 4),
                    mean_word_px_recall=round(float(np.mean([w['found_px'] / w['text_px'] for w in ws])) if ws else 0, 4),
                    weak=[(w['crop'], w['reading'], round(w['found_px'] / w['text_px'], 3)) for w in ws if w['found_px'] / w['text_px'] < 0.9])
    lp = dict(big_px=sum(r[t]['big_px'] for t in have), big_called=sum(r[t]['big_called'] for t in have),
              str_px=sum(r[t]['str_px'] for t in have), str_called=sum(r[t]['str_called'] for t in have))
    lp['big_share'] = round(lp['big_called'] / max(1, lp['big_px']), 5); lp['straight_share'] = round(lp['str_called'] / max(1, lp['str_px']), 5)
    lp['by_crop'] = {t: dict(big=round(r[t]['big_called'] / max(1, r[t]['big_px']), 5), straight=round(r[t]['str_called'] / max(1, r[t]['str_px']), 5)) for t in have}
    o = dict(crops=have, P=round(P, 4), R=round(R, 4), F1=round(F, 4), nontext_called=round(s[1] / max(1, sum(r[t]['t1'] for t in have)), 5),
             crop_F1=per, mean_crop_F1=round(float(np.mean(list(per.values()))), 4), leave_one_out_F1=loo,
             street=kind('street'), block=kind('block'), line_proxy=lp)
    if m in boot:
        o['boot_F1'] = dict(p2_5=round(float(np.percentile(boot[m], 2.5)), 4), p50=round(float(np.median(boot[m])), 4),
                            p97_5=round(float(np.percentile(boot[m], 97.5)), 4), share_ge_0_92=round(float((boot[m] >= 0.92).mean()), 4))
    o['street_words'] = [(w['crop'], w['reading'], w['text_px'], w['found_px']) for w in words if w['kind'] == 'street']
    o['block_words'] = [(w['crop'], w['reading'], w['text_px'], w['found_px']) for w in words if w['kind'] == 'block']
    out['methods'][m] = o
for a_, b_ in (('v3', 'v2'), ('v2', 'v1'), ('v3ex', 'v2')):
    if a_ in boot and b_ in boot:
        d = boot[a_] - boot[b_]
        out[f'boot_{a_}_minus_{b_}'] = dict(p2_5=round(float(np.percentile(d, 2.5)), 4), p50=round(float(np.median(d)), 4),
                                            p97_5=round(float(np.percentile(d, 97.5)), 4), share_gt_0=round(float((d > 0).mean()), 4))
os.makedirs(f'{B}/skeptic/out', exist_ok=True)
fn = f'{B}/skeptic/out/sk_score_{tn}.json'
json.dump(out, open(fn, 'w', encoding='utf8'), indent=1, default=lambda x: x.item() if hasattr(x, 'item') else str(x))
for m, o in out['methods'].items():
    print(f"{m:5s} P {o['P']:.4f} R {o['R']:.4f} F1 {o['F1']:.4f} | crop F1 {o['crop_F1']} mean {o['mean_crop_F1']:.4f} | boot {o.get('boot_F1')}")
    print(f"      LOO {o['leave_one_out_F1']}")
    print(f"      street {o['street']['words_found']} px {o['street']['px_recall']} meanword {o['street']['mean_word_px_recall']} weak {o['street']['weak']}")
    print(f"      block  {o['block']['words_found']} px {o['block']['px_recall']} meanword {o['block']['mean_word_px_recall']} weak {o['block']['weak']}")
    lp = o['line_proxy']; print(f"      line proxy: big {lp['big_share']*100:.3f}% of {lp['big_px']} | straight {lp['straight_share']*100:.3f}% of {lp['str_px']} | {lp['by_crop']}")
for k, v in out.items():
    if k.startswith('boot_'): print(k, v)
print('->', fn)
