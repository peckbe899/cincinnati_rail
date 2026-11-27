"""Block-number recall by method and scale on the targeted dev truth (dev_block, 26 Nov 2026).

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/dev_block/scripts/analyze.py NAME=MASK_PATTERN:CODES [...] [--pics]

e.g. bin8=unet_data/{plate}_bins.png:8  finder3=some/{plate}_text.png:2,3. A pattern may list several folders separated
by '|' (the first that has the plate is used). For every target block word: its truth text px (truth 2 inside its box),
how many the mask calls text, found (half or more), and where the missed px are:
  - 'at a line': within 3 px of ink the truth calls not text or don't care (a crossing or touching line),
  - 'rim': otherwise within 2 px of px of the word that are found (a 1-2 px edge of a found stroke),
  - 'stroke': the rest (a whole stroke or figure missed away from any line).
Pools by scale and in all. Non-text ink called text inside the scopes (truth 1 called text / truth 1).
Writes dev_block/scores/block_by_method.json and .md; with --pics, loss pictures pics/loss/NAME_DB##.png (scan | truth |
mask: text red/green) for every word whose recall is under 0.9."""
import os, sys, json
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from common import plate_img  # noqa: E402

TR = os.path.join(DB, 'truth'); C = json.load(open(os.path.join(TR, 'crops.json'), encoding='utf8'))


def load_mask(pat, plate, win, cache):
    for p in pat.split('|'):
        f = p.replace('{plate}', plate)
        if os.path.exists(f):
            if f not in cache: cache[f] = cv2.imread(f, cv2.IMREAD_UNCHANGED)
            m = cache[f]; m = m[..., 0] if m.ndim == 3 else m
            x0, y0, x1, y1 = win; return m[y0:y1, x0:x1], f
    return None, None


def word_mask(shape, poly, org):
    m = np.zeros(shape, np.uint8); cv2.fillPoly(m, [np.round(np.array(poly) - org).astype(np.int32)], 1); return m > 0


def main():
    specs = [a for a in sys.argv[1:] if '=' in a]; pics = '--pics' in sys.argv
    res = {}
    for s in specs:
        name, rest = s.split('=', 1); pat, codes = rest.rsplit(':', 1); codes = [int(v) for v in codes.split(',')]
        cache = {}; rows = []
        for t in sorted(C):
            c = C[t]; win = c['win']; M = cv2.imread(os.path.join(TR, f'{t}_mask.png'), 0)
            m, f = load_mask(pat, c['plate'], win, cache)
            if m is None: rows.append(dict(crop=t, plate=c['plate'], scale=c['scale_ft_per_inch'], missing=True)); continue
            pred = np.isin(m, codes)
            W = json.load(open(os.path.join(TR, f'{t}_words.json'), encoding='utf8'))['words']
            other = ((M == 1) | (M == 3)).astype(np.uint8)
            near_other = cv2.dilate(other, np.ones((7, 7), np.uint8)) > 0
            t1 = M == 1
            for w in W:
                if not w.get('target'): continue
                pm = word_mask(M.shape, w['poly'], np.array(win[:2])) & (M == 2)
                n = int(pm.sum()); fnd = int((pm & pred).sum()); miss = pm & ~pred
                near_found = cv2.dilate((pm & pred).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
                at_line = miss & near_other; rim = miss & ~near_other & near_found; stroke = miss & ~near_other & ~near_found
                rows.append(dict(crop=t, plate=c['plate'], scale=c['scale_ft_per_inch'], reading=w['reading'], flags=w['flags'], text_px=n, found_px=fnd,
                                 recall=round(fnd / max(1, n), 4), found=bool(fnd >= 0.5 * n), miss_at_line=int(at_line.sum()), miss_rim=int(rim.sum()), miss_stroke=int(stroke.sum()),
                                 nontext_px=int(t1.sum()), nontext_called=int((t1 & pred).sum()), mask=f))
                if pics and fnd < 0.9 * n: loss_pic(name, t, c, M, pred, w)
        res[name] = rows
    out = {}
    for name, rows in res.items():
        R = [r for r in rows if not r.get('missing')]; pools = {}
        for sc in (100, 200, 400, 'all'):
            q = [r for r in R if sc == 'all' or r['scale'] == sc]
            if not q: continue
            tp = sum(r['text_px'] for r in q); fp = sum(r['found_px'] for r in q)
            pools[str(sc)] = dict(words=len(q), words_found=sum(r['found'] for r in q), text_px=tp, found_px=fp, recall=round(fp / max(1, tp), 4),
                                  miss_at_line=sum(r['miss_at_line'] for r in q), miss_rim=sum(r['miss_rim'] for r in q), miss_stroke=sum(r['miss_stroke'] for r in q),
                                  nontext_called_share=round(sum(r['nontext_called'] for r in q) / max(1, sum(r['nontext_px'] for r in q)), 4),
                                  words_under_09=sum(r['recall'] < 0.9 for r in q))
        out[name] = dict(pools=pools, words=rows, missing=[r['crop'] for r in rows if r.get('missing')])
    json.dump(out, open(os.path.join(DB, 'scores', 'block_by_method.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
    L = ['| method | scale | words found | pixel recall | missed px at a line | missed px rim | missed px whole stroke | words under 0.9 | non-text ink called text (in scope) |', '|---|---|---|---|---|---|---|---|---|']
    for name, o in out.items():
        for sc, p in o['pools'].items():
            L.append(f"| {name} | {sc} | {p['words_found']}/{p['words']} | {p['recall']:.3f} | {p['miss_at_line']} | {p['miss_rim']} | {p['miss_stroke']} | {p['words_under_09']} | {p['nontext_called_share']:.3f} |")
    L += ['', '| crop | plate | scale | block | ' + ' | '.join(out) + ' |', '|---|---|---|---|' + '---|' * len(out)]
    names = list(out); base = out[names[0]]['words']
    for i, r in enumerate(base):
        cells = []
        for nm in names:
            q = out[nm]['words'][i]; cells.append('n/a' if q.get('missing') else f"{q['recall']:.2f}")
        L.append(f"| {r['crop']} | {r['plate']} | {r['scale']} | {r.get('reading', '')} | " + ' | '.join(cells) + ' |')
    open(os.path.join(DB, 'scores', 'block_by_method.md'), 'w', encoding='utf8').write('\n'.join(L) + '\n'); print('\n'.join(L[:2 + 4 * len(out)]))


def loss_pic(name, t, c, M, pred, w, sc=4):
    X0, Y0, X1, Y1 = c['win']; im = plate_img(c['plate'])[Y0:Y1, X0:X1]
    a = w['aabb']; x0, y0, x1, y1 = max(0, a[0] - X0 - 15), max(0, a[1] - Y0 - 15), min(M.shape[1], a[2] - X0 + 15), min(M.shape[0], a[3] - Y0 + 15)
    A = im[y0:y1, x0:x1]; T = M[y0:y1, x0:x1]; P = pred[y0:y1, x0:x1]
    o = (A.astype(np.float32) * 0.35 + 255 * 0.65).astype(np.uint8); o2 = o.copy()
    for v, col in {1: (200, 90, 0), 2: (0, 0, 230), 3: (0, 160, 255)}.items(): o[T == v] = col
    ink = cv2.cvtColor(A, cv2.COLOR_BGR2LAB)[..., 0] < 140
    o2[ink] = (150, 150, 150); o2[P & (T == 2)] = (0, 170, 0); o2[~P & (T == 2)] = (0, 0, 230); o2[P & (T == 1)] = (200, 0, 200)
    k = lambda z: cv2.resize(z, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)
    G = np.hstack([k(A), np.full((A.shape[0] * sc, 4, 3), 255, np.uint8), k(o), np.full((A.shape[0] * sc, 4, 3), 255, np.uint8), k(o2)])
    G = cv2.copyMakeBorder(G, 16, 2, 2, 2, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    cv2.putText(G, f"{t} plate {c['plate']} ({c['scale_ft_per_inch']} ft) block {w['reading']} | {name}: green found, red missed, magenta non-text called text", (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1)
    os.makedirs(os.path.join(DB, 'pics', 'loss'), exist_ok=True); cv2.imwrite(os.path.join(DB, 'pics', 'loss', f'{name}_{t}.png'), G)


if __name__ == '__main__':
    main()
