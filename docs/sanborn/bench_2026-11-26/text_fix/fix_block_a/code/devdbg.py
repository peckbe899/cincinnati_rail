"""Dev (fix_block_a): show blockfix's words round one dev crop.
    cd data/sanborn; python -B .../code/devdbg.py TRUTH_DIR CROP OUT.png [--set k=v ...]
Panels: scan | base codes | new codes | words (accepted pieces red, refused blue, crossing strips dark grey, long lines
light grey). Prints the words that reach the crop."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import blockfix
from viz import paint, COL


def main():
    a = sys.argv; td, cid, outp = a[1], a[2], a[3]
    opts = {}
    for i, v in enumerate(a):
        if v == '--set': k, val = a[i + 1].split('=', 1); opts[k] = json.loads(val)
    if td == 'win':   # devdbg.py win PLATE:X0,Y0,X1,Y1 OUT.png
        p, w_ = cid.split(':'); c = dict(plate=p, win=[int(v) for v in w_.split(',')])
    else: c = json.load(open(os.path.join(td, 'crops.json')))[cid]
    p = c['plate']; x0, y0, x1, y1 = c['win']; M = 250
    full = cv2.imread(os.path.join(HERE, '..', 'base', f'{p}_text.png'), cv2.IMREAD_UNCHANGED); Hh, Ww = full.shape
    X0, Y0, X1, Y1 = max(0, x0 - M), max(0, y0 - M), min(Ww, x1 + M), min(Hh, y1 + M)
    dbg = {}
    out, info = blockfix.apply(p, full[Y0:Y1, X0:X1], None, blockfix.scale_of(p), debug=dbg, return_info=True, **opts)
    sl = (slice(y0 - Y0, y1 - Y0), slice(x0 - X0, x1 - X0))
    im = cv2.imread(f'cufp/22-{p}.jpg')[y0:y1, x0:x1]
    big = np.full((Y1 - Y0, X1 - X0, 3), 255, np.uint8); big[dbg['LB'] > 0] = (200, 200, 200)
    for w in dbg.get('words', []):
        wx0, wy0, wx1, wy1 = w['win']; bx = w['box']
        if bx[2] < sl[1].start or bx[0] > sl[1].stop or bx[3] < sl[0].start or bx[1] > sl[0].stop: continue
        reg = big[wy0:wy1, wx0:wx1]
        reg[w['strip'] > 0] = (90, 90, 90)
        reg[np.isin(w['lb'], w['members'])] = (0, 0, 230) if w['ok'] else (230, 100, 0)
        print(('OK ' if w['ok'] else '-- ') + f"{w['why']:10s} box {[bx[0]-sl[1].start, bx[1]-sl[0].start, bx[2]-sl[1].start, bx[3]-sl[0].start]} H {w['H']} W {w['W']} A {w['A']} anchor {w['anchor']} sw {w['sw']} dens {w['dens']} n {w['n']} drop {w.get('dropped_line_pieces')} stubs {w.get('stubs')} ring {w.get('ring_pieces')} band {w.get('out_of_band')} lines {w['lines']}")
    r = np.concatenate([im, paint(im, full[y0:y1, x0:x1], COL), paint(im, out[sl], COL), big[sl]], 1)
    cv2.imwrite(outp, cv2.resize(r, None, fx=float(os.environ.get('Z', 2.5)), fy=float(os.environ.get('Z', 2.5)), interpolation=cv2.INTER_NEAREST))


if __name__ == '__main__':
    main()
