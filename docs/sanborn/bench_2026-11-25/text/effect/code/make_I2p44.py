"""make_I2p44.py (text/effect, 25 Nov 2026): I2p = the idealised mask I2 less everything within 3 px of any long line's ink that is not itself in I2
(line core: straight 35 px in the ink grown 1 px; and the gap-tolerant straight lines of make_masks2.py; a big letter's
strokes are line core too, so ink in I2 is not counted as a line). The guarantee
under test: a text mask applied to the line map keeps a 3 px keep-out round every line, so digits written against a
block line are masked only beyond it. Uses no truth beyond I2's. Writes masks/44_map_I2p.png.
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/make_I2p44.py"""
import os, numpy as np, cv2
MK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'masks')
I2 = cv2.imread(os.path.join(MK, '44_map_I2.png'), 0) > 0; H, W = I2.shape
unp = lambda f: np.unpackbits(np.load(os.path.join(MK, f)))[:H * W].reshape(H, W) > 0
lines = ((unp('44_linecore.npy') | unp('44_glc.npy')) & ~I2).astype(np.uint8)   # the long lines' ink that is not text (letter strokes are line core too)
keep = cv2.dilate(lines, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))) > 0
I2p = I2 & ~keep; cv2.imwrite(os.path.join(MK, '44_map_I2p.png'), I2p.astype(np.uint8) * 255)
print('I2', int(I2.sum()), 'I2p', int(I2p.sum()), 'taken out by the keep-out', int((I2 & keep).sum()))
