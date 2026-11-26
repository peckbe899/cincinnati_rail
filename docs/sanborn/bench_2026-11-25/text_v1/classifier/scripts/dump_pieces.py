"""Run finder v2 on a plate and keep its pieces for the classifier (classifier step, 26 Nov 2026).

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/classifier/scripts/dump_pieces.py N [N ...]

Imports text_v1/code/finder2.py read-only and runs it exactly as it is, except that the code image is also captured
just before its last step (shared_ink), because finder3 changes pieces there and then runs shared_ink itself.
Writes text_v1/classifier/data/pieces/N.npz:
  pre      the code image before shared_ink (0 paper, 1 line, 2 glyph, 3 by context, 5 other), PNG-encoded
  final    finder2's code image (as finder2/out/final/N_text.png), PNG-encoded
  pieces   one row per step-3 piece (8-connected ink less the line ink grown 1 px): bbox, finder2 kind, its features
           (area, bar length and thickness, stroke width, holes, line touch...), how many of its pixels finder2 gave each
           code, and the piece's own pixels (bit-packed crop)
No truth is read. Checks that 'final' equals finder2/out/final/N_text.png when that file exists."""
import os, sys, time, json
sys.dont_write_bytecode = True
import numpy as np, cv2
SP = os.getcwd()
CODE_DIR = os.path.join(SP, 'bench_2026-11-25', 'text_v1', 'code'); sys.path.insert(0, CODE_DIR)
import finder2  # noqa: E402
OUT = os.path.join(SP, 'bench_2026-11-25', 'text_v1', 'classifier', 'data', 'pieces')
FKEYS = ('A', 'long', 'thick', 'x', 'y', 'ang', 'sw', 'dtmax', 'holes', 'touch', 'ext', 'slen')


def dump(N):
    t0 = time.time(); cap = {}
    real = finder2.shared_ink
    def grab(code, ink):
        cap['pre'] = code.copy(); return real(code, ink)
    finder2.shared_ink = grab
    try: code, rec, (n, lb, F, k) = finder2.run(N, None, None, False, None, verbose=False)
    finally: finder2.shared_ink = real
    pre = cap['pre']
    ref = os.path.join(SP, 'bench_2026-11-25', 'text_v1', 'finder2', 'out', 'final', f'{N}_text.png')
    same = None
    if os.path.exists(ref): same = int((cv2.imread(ref, 0) != code).sum())
    # per piece: pixels of each code (pre-shared), on the piece's own ink
    m = lb > 0
    cc = np.zeros((n, 6), np.int64)
    for v in range(6): cc[:, v] = np.bincount(lb[m & (pre == v)], minlength=n)
    bits = []; off = np.zeros(n + 1, np.int64)
    bx, by, bw, bh = F['bx'], F['by'], F['bw'], F['bh']
    for i in range(1, n):
        x, y, w, h = int(bx[i]), int(by[i]), int(bw[i]), int(bh[i])
        b = np.packbits((lb[y:y + h, x:x + w] == i).ravel()); bits.append(b); off[i + 1] = off[i] + len(b)
    os.makedirs(OUT, exist_ok=True)
    np.savez_compressed(os.path.join(OUT, f'{N}.npz'), plate=N, size=np.array(code.shape), ft=rec['ft_per_inch'] or 0,
                        pre=np.frombuffer(cv2.imencode('.png', pre)[1].tobytes(), np.uint8),
                        final=np.frombuffer(cv2.imencode('.png', code)[1].tobytes(), np.uint8),
                        bbox=np.c_[bx, by, bw, bh][1:].astype(np.int32), kind=np.array(k[1:], dtype='U8'),
                        codes=cc[1:].astype(np.int32), bits=np.concatenate(bits) if bits else np.zeros(0, np.uint8), off=off[1:],
                        **{f'f_{q}': np.asarray(F[q])[1:].astype(np.float32) for q in FKEYS})
    print(f'plate {N}: {n - 1} pieces; differs from finder2/out/final in {same} px; {time.time() - t0:.0f} s', flush=True)


def load(N, root=OUT):
    """read a dump back: dict with pre, final (code images), and the piece arrays; mask(i) gives piece i's crop"""
    D = dict(np.load(os.path.join(root, f'{N}.npz')))
    D['pre'] = cv2.imdecode(D['pre'], 0); D['final'] = cv2.imdecode(D['final'], 0)
    return D


def mask(D, i):
    x, y, w, h = D['bbox'][i]; o = D['off']
    return np.unpackbits(D['bits'][o[i]:o[i + 1]])[:w * h].reshape(h, w)


if __name__ == '__main__':
    for N in sys.argv[1:]: dump(N)
