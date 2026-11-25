"""make_masks2.py (text/effect, 25 Nov 2026): a cleaner idealised text mask, I2, after the eye check of bin 8
(crops/sample_bin8_*.png: about 1 sampled pixel in 8 is a broken line piece or a symbol, not a character).
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/make_masks2.py N SRC.png OUT.png [PROTECT_PX]

From a text mask SRC (bin 8 of some sorting):
  1. drop the pieces that are broken LINE: thin (largest distance to the piece's edge 2.5 px or less, so strokes up to
     about 5 px wide) with 60% or more of their pixels on a gap-tolerant straight line (ink closed along a direction with
     a 7 px line, then opened with a 61 px line, in 24 directions: a dotted or grainy line of 61 px or more, gaps up to
     6 px)
  2. drop solid dots (symbols): largest distance to the edge r of 5 px or more and an area of 0.6 to 1.6 times the disc pi r^2
  3. add the glued strokes: ink within 8 px of what is left that is neither line core (a straight 35 px line fits it in
     the ink grown by 1 px: ink_bins.railroad's long_) nor on the gap-tolerant straight lines
  4. take out everything within PROTECT_PX (default 16) of Ben's checked tracks (rail_ben.json, both kinds): a text
     stage that never takes a railroad tick or a streetcar dash. This uses the truth: it is an upper bound
Writes OUT.png and OUT.json (counts)."""
import sys, os, json, importlib.util
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location('ib_copy', os.path.join(HERE, 'orig', 'ink_bins.py')); IB = importlib.util.module_from_spec(spec); spec.loader.exec_module(IB)
N, src, out = sys.argv[1:4]; PROT = int(sys.argv[4]) if len(sys.argv) > 4 else 16
im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]; L = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0]; del im
paper = cv2.resize(np.load(f'cufp/{N}/png_alpha_s4.npy'), (W, H), interpolation=cv2.INTER_NEAREST) > 0
ink = (L < IB.INK_L) & paper; del L; r8 = ink.astype(np.uint8)
S = (cv2.imread(src, 0) > 0) & ink
fat = cv2.dilate(r8, np.ones((3, 3), np.uint8)); LC = np.zeros_like(r8); GLC = np.zeros_like(r8)
for i in range(24):
    a = np.pi * i / 24
    LC |= cv2.morphologyEx(fat, cv2.MORPH_OPEN, IB.line_kernel(35, a)) & r8
    GLC |= cv2.morphologyEx(cv2.morphologyEx(r8, cv2.MORPH_CLOSE, IB.line_kernel(7, a)), cv2.MORPH_OPEN, IB.line_kernel(61, a)) & r8
del fat
n, lab, st, _ = cv2.connectedComponentsWithStats(S.astype(np.uint8), connectivity=8)
dt = cv2.distanceTransform(S.astype(np.uint8), cv2.DIST_L2, 5)
ys, xs = np.nonzero(S); l = lab[ys, xs]
dmax = np.zeros(n); np.maximum.at(dmax, l, dt[ys, xs]); A = np.bincount(l, minlength=n).astype(float); g = np.bincount(l, GLC[ys, xs], minlength=n) / np.maximum(A, 1)
line_piece = (dmax <= 2.5) & (g >= 0.6); dot = (dmax >= 5) & (A >= 0.6 * np.pi * dmax ** 2) & (A <= 1.6 * np.pi * dmax ** 2); line_piece[0] = dot[0] = False
Sc = S & ~(line_piece | dot)[lab]
near = cv2.distanceTransform((~Sc).astype(np.uint8), cv2.DIST_L2, 5) <= 8
glued = ink & ~(LC > 0) & ~(GLC > 0) & near & ~Sc
RB = os.path.join(ROOT, 'inputs', f'rail_ben_{N}_copy.json'); band = np.zeros((H, W), np.uint8)
for t in json.load(open(RB, encoding='utf8'))['tracks']: cv2.polylines(band, [np.round(np.array(t['pts'], float)).astype(np.int32)], False, 1, 2 * PROT + 1)
I2 = (Sc | glued) & (band == 0)
cv2.imwrite(out, I2.astype(np.uint8) * 255)
rec = dict(plate=N, src=src, protect_px=PROT, src_px=int(S.sum()), pieces=int(n - 1), line_pieces=int(line_piece.sum()), line_piece_px=int(A[line_piece].sum()), dots=int(dot.sum()), dot_px=int(A[dot].sum()),
           glued_px=int(glued.sum()), removed_by_rail_band_px=int(((Sc | glued) & (band > 0)).sum()), I2_px=int(I2.sum()))
json.dump(rec, open(out[:-4] + '.json', 'w'), indent=1); print(json.dumps(rec))
np.save(os.path.join(ROOT, 'masks', f'{N}_glc.npy'), np.packbits(GLC > 0))
