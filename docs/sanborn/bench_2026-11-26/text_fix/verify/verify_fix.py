"""My own re-score of the text_fix gate (block, ditto, full crops) on sealed_final.
Independent of score_text.py / gscore.py / sk_score.py. Run from data/sanborn.
Text = codes 2,3 in N_text.png. Truth: 0 paper, 1 non-text ink, 2 text, 3 don't care.
"""
import json, sys
from pathlib import Path
import numpy as np, cv2

TF = Path('bench_2026-11-26/text_fix')
TRUTH = TF / 'sealed_final'
crops = json.load(open(TRUTH / 'crops.json'))
plates = {}

def plate_mask(method, N):
    k = (method, N)
    if k not in plates:
        m = cv2.imread(str(TF / 'gate/out' / method / f'{N}_text.png'), cv2.IMREAD_UNCHANGED)
        if m.ndim == 3: m = m[..., 0]
        plates[k] = (m == 2) | (m == 3)
    return plates[k]

res = {}
for method in ('finder3', 'finder4'):
    words = {'block': [], 'ditto': [], 'street': []}
    fullpix = dict(tp=0, fp=0, fn=0, t1=0)
    fill_mismatch = 0; nwords = 0
    for cid, c in crops.items():
        x0, y0, x1, y1 = c['win']
        t = cv2.imread(str(TRUTH / f'{cid}_mask.png'), cv2.IMREAD_UNCHANGED)
        if t.ndim == 3: t = t[..., 0]
        p = plate_mask(method, c['plate'])[y0:y1, x0:x1]
        assert p.shape == t.shape, (cid, p.shape, t.shape)
        w = json.load(open(TRUTH / f'{cid}_words.json'))
        for wd in w['words']:
            poly = np.round(np.array(wd['poly']) - [x0, y0]).astype(np.int32)
            wm = np.zeros(t.shape, np.uint8); cv2.fillPoly(wm, [poly], 1)
            tw = (wm > 0) & (t == 2)
            n = int(tw.sum())
            if 'text_px_final' in wd:
                nwords += 1
                if n != wd['text_px_final']: fill_mismatch += 1
            kind = wd['kind']
            take = (c['kind'] == 'targeted' and wd.get('target')) or (c['kind'] == 'full' and kind == 'street')
            if take and kind in words and n > 0:
                found = int((tw & p).sum())
                words[kind].append((cid, wd['id'], c['plate'], c['scale_ft_per_inch'], n, found))
        if c['kind'] == 'full':
            fullpix['tp'] += int((p & (t == 2)).sum()); fullpix['fp'] += int((p & (t == 1)).sum())
            fullpix['fn'] += int((~p & (t == 2)).sum()); fullpix['t1'] += int((t == 1).sum())
    out = {'fill_mismatch': f'{fill_mismatch}/{nwords}'}
    for kind, L in words.items():
        n = sum(a[4] for a in L); f = sum(a[5] for a in L)
        wf = sum(1 for a in L if a[5] >= 0.5 * a[4])
        out[kind] = dict(pixel_recall=round(f / max(1, n), 4), words=f'{wf}/{len(L)}', share=round(wf / max(1, len(L)), 4))
        for s in (100, 200, 400):
            Ls = [a for a in L if a[3] == s]
            if Ls:
                out[kind][f'{s}ft'] = (round(sum(a[5] for a in Ls) / sum(a[4] for a in Ls), 3),
                                        f'{sum(1 for a in Ls if a[5] >= 0.5 * a[4])}/{len(Ls)}')
    P = fullpix['tp'] / max(1, fullpix['tp'] + fullpix['fp']); R = fullpix['tp'] / max(1, fullpix['tp'] + fullpix['fn'])
    out['full'] = dict(P=round(P, 4), R=round(R, 4), F1=round(2 * P * R / (P + R), 4),
                       nontext_pct=round(100 * fullpix['fp'] / fullpix['t1'], 3))
    res[method] = out

print(json.dumps(res, indent=1))
