"""No-harm check (fix_block_a): on truth v2 T1-T7, the px a new mask calls text that finder3 did not, split by the truth
(1 not text, 2 text, 3 don't care), and the px of text it took away; with --pic OUT.png a sheet of every changed spot with
new false text (scan | finder3 | new, false text in red | truth).
    cd data/sanborn; python -B .../code/t17diff.py NEW_PATTERN [--pic OUT.png] [--min 15]"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from viz import paint, COL, TCOL
TD = 'bench_2026-11-25/text_v1/truth'; BASE = os.path.join(HERE, '..', 'base', '{plate}_text.png')
a = sys.argv; newp = a[1]; pic = a[a.index('--pic') + 1] if '--pic' in a else None; mn = int(a[a.index('--min') + 1]) if '--min' in a else 15
crops = json.load(open(TD + '/crops.json')); tiles = []; out = {}
for cid, c in sorted(crops.items()):
    x0, y0, x1, y1 = c['win']
    b = cv2.imread(BASE.replace('{plate}', c['plate']), 0)[y0:y1, x0:x1]; n = cv2.imread(newp.replace('{plate}', c['plate']), 0)[y0:y1, x0:x1]
    tr = cv2.imread(f'{TD}/{cid}_mask.png', 0); nt = np.isin(n, (2, 3)); bt = np.isin(b, (2, 3)); add = nt & ~bt
    out[cid] = dict(new_on_nottext=int((add & (tr == 1)).sum()), new_on_text=int((add & (tr == 2)).sum()), new_on_dontcare=int((add & (tr == 3)).sum()), text_lost=int((bt & ~nt).sum()))
    if pic:
        im = cv2.imread(f"cufp/22-{c['plate']}.jpg")[y0:y1, x0:x1]; fp = add & (tr == 1)
        k, lb, st, _ = cv2.connectedComponentsWithStats(cv2.dilate((n != b).astype(np.uint8), np.ones((15, 15), np.uint8)))
        for i in range(1, k):
            X, Y, W, H = st[i, :4]; f_ = int(fp[Y:Y + H, X:X + W].sum())
            if f_ < mn: continue
            s = (slice(max(0, Y - 10), Y + H + 10), slice(max(0, X - 10), X + W + 10)); o = paint(im[s], n[s], COL); o[fp[s]] = (0, 0, 255)
            r = cv2.resize(np.concatenate([im[s], paint(im[s], b[s], COL), o, paint(im[s], tr[s], TCOL)], 1), None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
            r = np.pad(r, ((14, 4), (0, 0), (0, 0)), constant_values=255); cv2.putText(r, f'{cid} {x0 + X},{y0 + Y} new false text {f_}', (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1); tiles.append(r)
print(json.dumps(out))
if pic and tiles:
    W_ = max(t.shape[1] for t in tiles); cv2.imwrite(pic, np.concatenate([np.pad(t, ((0, 0), (0, W_ - t.shape[1]), (0, 0)), constant_values=255) for t in tiles], 0))
