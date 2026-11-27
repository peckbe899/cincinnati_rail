"""Per-figure loss on the targeted block truth (dev_block, 26 Nov 2026).
The target's text ink (truth 2 in its box) is cut into 8-connected pieces of 60 px or more (mostly one figure each;
two touching figures make one piece). A piece is 'bar-like' (a figure 1) when its width is under 0.45 of its height.
'touches a line': within 2 px of ink the truth calls not text or don't care. Found = half or more of its px called text.
    python -B glyphs.py NAME=PATTERN:CODES [...]   (patterns as analyze.py)"""
import os, sys, json
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from analyze import C, TR, load_mask, word_mask
out = {}
for s in [a for a in sys.argv[1:] if '=' in a]:
    name, rest = s.split('=', 1); pat, codes = rest.rsplit(':', 1); codes = [int(v) for v in codes.split(',')]; cache = {}; G = []
    for t in sorted(C):
        c = C[t]; M = cv2.imread(os.path.join(TR, f'{t}_mask.png'), 0); m, f = load_mask(pat, c['plate'], c['win'], cache)
        pred = np.isin(m, codes)
        w = [w for w in json.load(open(os.path.join(TR, f'{t}_words.json'), encoding='utf8'))['words'] if w.get('target')][0]
        pm = (word_mask(M.shape, w['poly'], np.array(c['win'][:2])) & (M == 2)).astype(np.uint8)
        near = cv2.dilate(((M == 1) | (M == 3)).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        n, lb, st, _ = cv2.connectedComponentsWithStats(pm, connectivity=8)
        for i in range(1, n):
            x, y, ww, hh, a = st[i]
            if a < 60: continue
            g = lb == i
            G.append(dict(crop=t, scale=c['scale_ft_per_inch'], reading=w['reading'], box=[int(x), int(y), int(ww), int(hh)], px=int(a), bar=bool(ww < 0.45 * hh),
                          touches=bool((g & near).any()), found=bool((g & pred).sum() >= 0.5 * a), recall=round(float((g & pred).sum() / a), 3)))
    out[name] = G
    for lab, q in (('bar-like (1s), free', [g for g in G if g['bar'] and not g['touches']]), ('bar-like (1s), touching a line', [g for g in G if g['bar'] and g['touches']]),
                   ('other figures, free', [g for g in G if not g['bar'] and not g['touches']]), ('other figures, touching a line', [g for g in G if not g['bar'] and g['touches']])):
        print(f"{name:8s} {lab:32s} pieces {len(q):3d}  found {sum(g['found'] for g in q):3d}  px recall {sum(g['recall'] * g['px'] for g in q) / max(1, sum(g['px'] for g in q)):.3f}  missed: {[g['crop'] for g in q if not g['found']]}")
json.dump(out, open(os.path.join(HERE, '..', 'scores', 'glyph_pieces.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
