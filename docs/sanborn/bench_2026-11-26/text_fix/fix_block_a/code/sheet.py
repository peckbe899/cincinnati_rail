"""Contact sheet of blockfix's changes on a plate (fix_block_a): scan | finder3 codes | blockfix codes, per changed word.
    cd data/sanborn; python -B .../code/sheet.py N BASE_DIR NEW_DIR OUT.png [--z 2] [--sample K --seed S] [--skip x0,y0,x1,y1;...]
Changed px are outlined in red in the third panel. Words are taken from NEW_DIR/N_text.json 'changes'. With --sample, K
words are drawn at random (random.Random(S)); --skip leaves out words whose box overlaps any listed window."""
import json, os, sys, random
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from viz import paint, COL


def main():
    a = sys.argv; N, bd, nd, outp = a[1:5]
    z = float(a[a.index('--z') + 1]) if '--z' in a else 2
    info = json.load(open(os.path.join(nd, f'{N}_text.json')))
    ch = info['changes']
    if '--skip' in a:
        sk = [[int(v) for v in w.split(',')] for w in a[a.index('--skip') + 1].split(';')]
        ch = [c for c in ch if not any(c['fbox'][0] < s[2] and c['fbox'][2] > s[0] and c['fbox'][1] < s[3] and c['fbox'][3] > s[1] for s in sk)]
    idx = list(range(len(ch)))
    if '--sample' in a:
        k = int(a[a.index('--sample') + 1]); seed = a[a.index('--seed') + 1]
        random.Random(seed).shuffle(idx); idx = sorted(idx[:k])
    base = cv2.imread(os.path.join(bd, f'{N}_text.png'), 0); new = cv2.imread(os.path.join(nd, f'{N}_text.png'), 0); im = cv2.imread(f'cufp/22-{N}.jpg')
    H, W = base.shape; tiles = []; listing = []
    for t, i in enumerate(idx):
        c = ch[i]; x0, y0, x1, y1 = c['fbox']; g = 25
        X0, Y0, X1, Y1 = max(0, x0 - g), max(0, y0 - g), min(W, x1 + g), min(H, y1 + g)
        s = im[Y0:Y1, X0:X1]; b = base[Y0:Y1, X0:X1]; n = new[Y0:Y1, X0:X1]
        pn = paint(s, n, COL); d = (b != n).astype(np.uint8)
        edge = (cv2.dilate(d, np.ones((3, 3), np.uint8)) > 0) & (d == 0)
        pn[edge] = (0, 0, 255)
        r = np.concatenate([s, np.full((s.shape[0], 3, 3), 255, np.uint8), paint(s, b, COL), np.full((s.shape[0], 3, 3), 255, np.uint8), pn], 1)
        r = cv2.resize(r, None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
        r = np.pad(r, ((16, 4), (0, 6), (0, 0)), constant_values=255)
        cv2.putText(r, f"#{i} {x0},{y0} +{c['to_text']} a{c['anchor']}", (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        tiles.append(r); listing.append(dict(i=i, fbox=c['fbox'], to_text=c['to_text'], anchor=c['anchor']))
    # pack rows of width <= 2400
    rows = []; cur = []; cw = 0
    for t in tiles:
        if cw + t.shape[1] > 2400 and cur: rows.append(cur); cur = []; cw = 0
        cur.append(t); cw += t.shape[1]
    if cur: rows.append(cur)
    R = []
    for r in rows:
        h = max(t.shape[0] for t in r); R.append(np.concatenate([np.pad(t, ((0, h - t.shape[0]), (0, 0), (0, 0)), constant_values=255) for t in r], 1))
    Wm = max(r.shape[1] for r in R)
    sheet = np.concatenate([np.pad(r, ((0, 0), (0, Wm - r.shape[1]), (0, 0)), constant_values=255) for r in R], 0)
    cv2.imwrite(outp, sheet)
    json.dump(listing, open(outp[:-4] + '.json', 'w'), indent=0)
    print(f'{len(tiles)} tiles -> {outp} {sheet.shape}')


if __name__ == '__main__':
    main()
