"""Contact sheets of the pieces finder v2 gets wrong on T1-T7 (dev only): mostly-non-text pieces called text, and
mostly-text pieces left as other ink (code 5). Each tile: scan crop | the piece in red, other text magenta, line grey.

    cd data/sanborn; python -B bench_2026-11-25/text_v1/classifier/scripts/flip_sheet.py [CODEPATTERN]

CODEPATTERN (default finder2's pre-shared code from the dumps) may be a png pattern with {plate}, e.g. a finder3 output,
to sheet what is still wrong after the classifier."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from dump_pieces import load, mask  # noqa
TRUTH = os.path.join('bench_2026-11-25', 'text_v1', 'truth')
PICS = os.path.join(HERE, '..', 'pics')


def pieces_in(D, win):
    x0, y0, x1, y1 = win; bb = D['bbox']
    return np.nonzero((bb[:, 0] >= x0) & (bb[:, 1] >= y0) & (bb[:, 0] + bb[:, 2] <= x1) & (bb[:, 1] + bb[:, 3] <= y1))[0]


def piece_truth(D, i, tr, win):
    x, y, w, h = D['bbox'][i]; m = mask(D, i) > 0; t = tr[y - win[1]:y - win[1] + h, x - win[0]:x - win[0] + w][m]
    return int((t == 2).sum()), int((t == 1).sum()), int(m.sum())


def main():
    pat = sys.argv[1] if len(sys.argv) > 1 else None
    crops = json.load(open(os.path.join(TRUTH, 'crops.json'))); tiles = {'to_junk': [], 'to_text': []}; ims = {}
    for tid in ('T1', 'T2', 'T3', 'T4', 'T6', 'T7'):
        c = crops[tid]; win = c['win']; D = load(c['plate']); tr = cv2.imread(os.path.join(TRUTH, f'{tid}_mask.png'), 0)
        code = cv2.imread(pat.replace('{plate}', c['plate']), 0) if pat else D['final']
        if c['plate'] not in ims: ims[c['plate']] = cv2.imread(f"cufp/22-{c['plate']}.jpg")
        im = ims[c['plate']]; H, W = code.shape
        for i in pieces_in(D, win):
            t2, t1, a = piece_truth(D, i, tr, win)
            if t2 + t1 == 0: continue
            x, y, w, h = D['bbox'][i]; m = mask(D, i) > 0; cc = code[y:y + h, x:x + w][m]; istext = np.isin(cc, (2, 3)).mean() >= 0.5
            if t1 >= 0.6 * (t1 + t2) and istext: key = 'to_junk'
            elif t2 >= 0.6 * (t1 + t2) and not istext: key = 'to_text'
            else: continue
            s = max(40, w, h) // 2 + 25; cx, cy = x + w // 2, y + h // 2; X0, Y0, X1, Y1 = max(0, cx - s), max(0, cy - s), min(W, cx + s), min(H, cy + s)
            a_ = im[Y0:Y1, X0:X1]; o = (a_ * 0.3 + 255 * 0.7).astype(np.uint8); cw = code[Y0:Y1, X0:X1]
            o[cw == 1] = (160, 160, 160); o[np.isin(cw, (2, 3))] = (220, 0, 220); o[cw == 4] = (0, 200, 230)
            pm = np.zeros(cw.shape, bool); pm[y - Y0:y - Y0 + h, x - X0:x - X0 + w] = m; o[pm] = (0, 0, 255)
            t_ = cv2.resize(np.concatenate([a_, o], 1), (240, 120), interpolation=cv2.INTER_AREA)
            cv2.putText(t_, f"{tid} {D['kind'][i]} {max(w, h)}px {t2}/{t1}", (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 120, 0), 1)
            tiles[key].append((t1 + t2, t_))
    tag = 'finder2' if not pat else 'custom'
    for key, L in tiles.items():
        L.sort(key=lambda q: -q[0]); L = [t for _, t in L[:120]]
        cols = 6; rows = max(1, (len(L) + cols - 1) // cols); sheet = np.full((rows * 122, cols * 242, 3), 255, np.uint8)
        for j, t_ in enumerate(L): r, cc_ = divmod(j, cols); sheet[r * 122:r * 122 + 120, cc_ * 242:cc_ * 242 + 240] = t_
        os.makedirs(PICS, exist_ok=True); cv2.imwrite(os.path.join(PICS, f'dev_{tag}_{key}.jpg'), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
        print(key, len(tiles[key]), 'pieces')


if __name__ == '__main__':
    main()
