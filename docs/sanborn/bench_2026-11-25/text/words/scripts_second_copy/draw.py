"""Draw a window of a plate with its words (from out/N_words.json): each word's glyphs and marks coloured by its kind,
the phrase's centre line in black with a dot at its reading start and an arrow head at its end, the kind's short name
at each word's start. Lone pieces not in any word: grey.

    python -B .../draw.py N X0 Y0 X1 Y1 OUT.jpg [--scale S] [--mode kind|string]"""
import json, os, sys
import numpy as np
import cv2
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'out')
KCOL = dict(street_name=(0, 0, 230), house_number=(220, 0, 0), lot_dimension=(0, 150, 0), block_number=(200, 0, 200),
            pipe_label=(0, 140, 230), lot_number=(150, 100, 0), owner_or_note=(0, 90, 160), story_or_single=(130, 130, 130),
            other=(40, 40, 40), junk=(185, 185, 185))
ABBR = dict(street_name='ST', house_number='HN', lot_dimension='LD', block_number='BN', pipe_label='PL', lot_number='LN',
            owner_or_note='ON', story_or_single='1', other='?', junk='')


def main():
    N = sys.argv[1]; x0, y0, x1, y1 = map(int, sys.argv[2:6]); out = sys.argv[6]
    sc = float(sys.argv[sys.argv.index('--scale') + 1]) if '--scale' in sys.argv else 1.0
    mode = sys.argv[sys.argv.index('--mode') + 1] if '--mode' in sys.argv else 'kind'
    T = sys.argv[sys.argv.index('--tag') + 1] if '--tag' in sys.argv else N
    im = cv2.imread(f'cufp/22-{N}.jpg')[y0:y1, x0:x1]
    J = json.load(open(os.path.join(OUT, f'{T}_words.json'), encoding='utf8'))
    L = cv2.imread(os.path.join(OUT, f'{T}_glyphlab.png'))
    lab = (L[..., 0].astype(np.int32) | (L[..., 1].astype(np.int32) << 8) | (L[..., 2].astype(np.int32) << 16))[y0:y1, x0:x1]
    c = (im * 0.4 + 255 * 0.6).astype(np.uint8)
    nl = int(J['meta']['glyphs']) + 2
    col = np.zeros((nl, 3), np.uint8); has = np.zeros(nl, bool); rng = np.random.default_rng(3)
    pal = [(220, 0, 0), (0, 150, 0), (0, 0, 220), (180, 0, 180), (0, 140, 180), (200, 120, 0)]
    for r in J['strings']:
        cs = pal[rng.integers(0, 6)]
        for w in r['words']:
            cc = KCOL[w['kind']] if mode == 'kind' else cs
            for g in w['glyphs'] + [m['g'] for m in w['marks']]: col[g + 1] = cc; has[g + 1] = True
    m = has[lab]; c[m] = col[lab[m]]
    c[(lab > 0) & ~m] = (150, 150, 150)
    if sc != 1: c = cv2.resize(c, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    o = np.array([x0, y0])
    for r in J['strings']:
        P = (np.array(r['centre_line']) - o) * sc
        if not ((P[:, 0] > -50).any() and (P[:, 0] < c.shape[1] + 50).any() and (P[:, 1] > -50).any() and (P[:, 1] < c.shape[0] + 50).any()): continue
        if all(w['kind'] == 'junk' for w in r['words']): continue
        if r['n'] >= 2:
            cv2.polylines(c, [np.round(P).astype(np.int32)], False, (0, 0, 0), 1, cv2.LINE_AA)
            cv2.circle(c, tuple(np.round(P[0]).astype(int)), 3, (0, 0, 0), -1)
            if len(P) >= 2: cv2.arrowedLine(c, tuple(np.round(P[-2]).astype(int)), tuple(np.round(P[-1]).astype(int)), (0, 0, 0), 1, cv2.LINE_AA, tipLength=0.9 if np.hypot(*(P[-1] - P[-2])) < 12 else 0.3)
        for w in r['words']:
            if w['kind'] == 'junk': continue
            p = (np.array([w['cx'], w['cy']]) - o) * sc
            cv2.putText(c, ABBR[w['kind']], tuple(np.round(p + [-8, -0.6 * w['h'] * sc - 3]).astype(int)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.imwrite(out, c, [cv2.IMWRITE_JPEG_QUALITY, 90])


if __name__ == '__main__':
    main()
