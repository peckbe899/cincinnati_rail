"""Gate scorer's own re-implementation of the main text numbers (26 Nov 2026). Independent of score_text.py:
PIL for reading, PIL ImageDraw.polygon for word boxes, plain numpy for counts.
    cd data/sanborn; python -B bench_2026-11-25/text_v1/gate/scripts/my_score.py OUT.json [--mask-out WINS.json]
Methods and truth sets are listed below. --mask-out: a JSON {plate: [[x0,y0,x1,y1],...]} of plate windows to leave out
of the score (set to don't care), e.g. the finder2 tuning windows that fall inside H3.
Scored: ink the truth calls 1 or 2; 3 (don't care) and 0 (paper) skipped. P, R, F1, non-text ink called text.
By kind: truth-2 pixels inside each word polygon (not grown); words found = half or more of a word's text px found.
Per-word lists are kept for street and block words."""
import json, os, sys
import numpy as np
from PIL import Image
from PIL import ImageDraw
Image.MAX_IMAGE_PIXELS = None
B = 'bench_2026-11-25'
METHODS = {
    'bin8': ('unet_data/{plate}_bins.png', (8,)),
    'v1': (f'{B}/text/finder/out/{{plate}}_finder.png', (2, 3, 4)),
    'v2': (f'{B}/text_v1/finder2/out/final/{{plate}}_text.png', (2, 3)),
    'v3': (f'{B}/text_v1/classifier/out/finder3/{{plate}}_text.png', (2, 3)),
}
TRUTH = {'heldfix': f'{B}/text_v1/truth-check/heldout_fixed', 'v2': f'{B}/text_v1/truth'}
a = sys.argv; OUT = a[1]
MO = json.load(open(a[a.index('--mask-out') + 1])) if '--mask-out' in a else {}
extra = [s for s in a[2:] if s.startswith('method=')]
for s in extra:   # method=name:pattern:codes
    n, p, c = s[7:].split('|'); METHODS[n] = (p, tuple(int(v) for v in c.split(',')))
cache = {}


def load(path):
    if path not in cache:
        cache.clear(); cache[path] = np.array(Image.open(path))
        if cache[path].ndim == 3: cache[path] = cache[path][..., 0]
    return cache[path]


res = {}
for tn, td in TRUTH.items():
    crops = json.load(open(os.path.join(td, 'crops.json')))
    ids = sorted(k for k in crops if os.path.exists(os.path.join(td, f'{k}_mask.png')))
    for m, (pat, codes) in METHODS.items():
        R = res.setdefault(m, {}).setdefault(tn, {'crops': {}})
        for cid in ids:
            c = crops[cid]; x0, y0, x1, y1 = c['win']; pl = c['plate']
            t = np.array(Image.open(os.path.join(td, f'{cid}_mask.png')))
            for w in MO.get(pl, []):   # leave windows out
                ax0, ay0, ax1, ay1 = max(w[0], x0), max(w[1], y0), min(w[2], x1), min(w[3], y1)
                if ax1 > ax0 and ay1 > ay0: t = t.copy(); t[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0] = np.where(t[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0] > 0, 3, 0)
            full = load(pat.replace('{plate}', pl))
            code = full[y0:y1, x0:x1] if full.shape != t.shape else full
            pred = np.isin(code, codes)
            tp = int((pred & (t == 2)).sum()); fp = int((pred & (t == 1)).sum()); fn = int((~pred & (t == 2)).sum()); n1 = int((t == 1).sum())
            kinds = {}; wl = []
            W = json.load(open(os.path.join(td, f'{cid}_words.json'), encoding='utf8'))['words']
            for w in W:
                if not w.get('poly'): continue
                P = np.array(w['poly'], float) - [x0, y0]
                im = Image.new('1', (t.shape[1], t.shape[0]), 0); ImageDraw.Draw(im).polygon([tuple(p) for p in P.tolist()], fill=1, outline=1)
                inside = np.array(im, bool)
                tt = inside & (t == 2); n = int(tt.sum())
                if not n: continue
                f = int((tt & pred).sum()); k = kinds.setdefault(w['kind'], [0, 0, 0, 0]); k[0] += 1; k[1] += n; k[2] += f; k[3] += int(f >= 0.5 * n)
                if w['kind'] in ('street', 'block', 'adjoin'):
                    wl.append(dict(kind=w['kind'], reading=w.get('reading'), text_px=n, found=f, recall=round(f / n, 3), aabb=w.get('aabb')))
            R['crops'][cid] = dict(tp=tp, fp=fp, fn=fn, n1=n1, kinds=kinds, words=wl)
        # pools
        for pn, sel in (('ALL', ids), ('noH3', [i for i in ids if i != 'H3']), ('H3', [i for i in ids if i == 'H3'])):
            if not sel: continue
            s = {q: sum(R['crops'][i][q] for i in sel) for q in ('tp', 'fp', 'fn', 'n1')}
            P_ = s['tp'] / max(1, s['tp'] + s['fp']); R_ = s['tp'] / max(1, s['tp'] + s['fn'])
            K = {}
            for i in sel:
                for k, v in R['crops'][i]['kinds'].items():
                    a_ = K.setdefault(k, [0, 0, 0, 0]); K[k] = [p + q for p, q in zip(a_, v)]
            R[pn] = dict(P=round(P_, 4), R=round(R_, 4), F1=round(2 * P_ * R_ / max(1e-9, P_ + R_), 4), nontext=round(s['fp'] / max(1, s['n1']), 4),
                         kinds={k: dict(words=v[0], text_px=v[1], recall=round(v[2] / max(1, v[1]), 4), words_found=v[3]) for k, v in sorted(K.items())}, **s)
            print(f"{tn:8s} {m:5s} {pn:5s} P {R[pn]['P']:.4f} R {R[pn]['R']:.4f} F1 {R[pn]['F1']:.4f} nontext {R[pn]['nontext']:.4f}  "
                  + '  '.join(f"{k} {R[pn]['kinds'][k]['recall']:.3f}({R[pn]['kinds'][k]['words_found']}/{R[pn]['kinds'][k]['words']})" for k in ('street', 'block', 'house', 'adjoin', 'ditto') if k in R[pn]['kinds']))
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
json.dump(dict(methods={k: [v[0], list(v[1])] for k, v in METHODS.items()}, mask_out=MO, res=res), open(OUT, 'w'), indent=1)
