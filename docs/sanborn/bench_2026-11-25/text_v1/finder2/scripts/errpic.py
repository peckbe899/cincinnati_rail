"""Error pictures of a text code mask on the truth v2 crops T1-T7 (finder2, 25 Nov 2026).

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/finder2/scripts/errpic.py MASK_PATTERN CODES OUTDIR [T1 ...] [--tiles] [--kind street,block]

MASK_PATTERN holds {plate}; CODES e.g. 2,3 (the codes that count as text).
Colours: text found = magenta; text missed and called line (code 1) = red; missed and called other (5) = orange;
missed and called shared (4) = yellow; non-text ink called text = green; don't care = light yellow; other ink = grey.
Reads only truth v2 (text_v1/truth) and the mask; writes only into OUTDIR."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
TRUTH = os.path.normpath(os.path.join(HERE, '..', '..', 'truth'))


def pic(im, truth, code, codes):
    t = np.isin(code, codes); c = (im * 0.35 + 255 * 0.65).astype(np.uint8)
    c[truth == 1] = (150, 150, 150); c[truth == 3] = (150, 230, 230)
    c[(truth == 2) & t] = (220, 0, 220)
    c[(truth == 2) & ~t & (code == 1)] = (0, 0, 255)
    c[(truth == 2) & ~t & (code == 5)] = (0, 140, 255)
    c[(truth == 2) & ~t & (code == 4)] = (0, 220, 220)
    c[(truth == 2) & ~t & (code == 0)] = (80, 80, 80)
    c[(truth == 1) & t] = (0, 170, 0)
    return c


if __name__ == '__main__':
    a = [x for i, x in enumerate(sys.argv[1:], 1) if not x.startswith("--") and sys.argv[i - 1] != "--kind"]
    pat, codes, out = a[0], [int(v) for v in a[1].split(',')], a[2]; ids = a[3:] or ['T1', 'T2', 'T3', 'T4', 'T6', 'T7']
    os.makedirs(out, exist_ok=True); crops = json.load(open(os.path.join(TRUTH, 'crops.json'))); cache = {}
    kinds = None
    if '--kind' in sys.argv: kinds = sys.argv[sys.argv.index('--kind') + 1].split(',')
    for tid in ids:
        c = crops[tid]; x0, y0, x1, y1 = c['win']; p = pat.replace('{plate}', c['plate'])
        if p not in cache: cache[p] = cv2.imread(p, 0)
        code = cache[p][y0:y1, x0:x1]; truth = cv2.imread(os.path.join(TRUTH, f'{tid}_mask.png'), 0)
        im = cv2.imread(f'cufp/22-{c["plate"]}.jpg')[y0:y1, x0:x1]
        o = pic(im, truth, code, codes)
        if kinds:
            W = json.load(open(os.path.join(TRUTH, f'{tid}_words.json'), encoding='utf8'))['words']
            for w in W:
                if w['kind'] in kinds and w.get('poly'):
                    q = np.round(np.array(w['poly'], float) - [x0, y0]).astype(np.int32); cv2.polylines(o, [q], True, (255, 120, 0), 1)
        cv2.imwrite(os.path.join(out, f'{tid}_err.png'), o)
        if '--tiles' in sys.argv:
            for r in range(2):
                for cc in range(2):
                    cv2.imwrite(os.path.join(out, f'{tid}_err_{r}{cc}.png'), o[r * 500:(r + 1) * 500, cc * 750:(cc + 1) * 750])
        print(tid, 'done')
