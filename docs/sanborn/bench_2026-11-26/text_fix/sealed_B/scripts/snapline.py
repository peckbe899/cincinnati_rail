"""Snap a roughly typed line segment onto the printed line under it, for writing NOTTEXT / CARELINE strips (truth v2).

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/truth-fix/scripts/snapline.py PLATE,x1,y1,x2,y2[,search=6] [...]

For each half of the segment, the ink (ink_bins' rule, L < 140 on the paper) within +-search px across it is binned by
its offset across the segment; the line is the fullest 1 px bin, refined to the mean offset of the bins within 2 px of
it, and its width is the run of bins holding at least 40% of the peak. Prints the snapped segment and a strip width
(line width + 2). Only a helper: it writes nothing; the snapped numbers are typed into annot/T#.txt by hand."""
import os, sys, math
sys.dont_write_bytecode = True
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import window


def snap(p, x1, y1, x2, y2, s=6):
    L = math.hypot(x2 - x1, y2 - y1); u = np.array([(x2 - x1) / L, (y2 - y1) / L]); v = np.array([-u[1], u[0]])
    bx0, by0, bx1, by1 = int(min(x1, x2) - s - 3), int(min(y1, y2) - s - 3), int(max(x1, x2) + s + 4), int(max(y1, y2) + s + 4)
    _, _, ink, (wx0, wy0, _, _) = window(p, bx0, by0, bx1, by1)
    ys, xs = np.nonzero(ink); X = xs + wx0 - x1; Y = ys + wy0 - y1
    al = X * u[0] + Y * u[1]; ac = X * v[0] + Y * v[1]
    out = []; widths = []
    for lo, hi in ((0, L / 2), (L / 2, L)):
        k = (al >= lo) & (al <= hi) & (np.abs(ac) <= s)
        if k.sum() < 3: out.append(0.0); continue
        h, e = np.histogram(ac[k], bins=np.arange(-s - 0.5, s + 1.5, 1.0)); c = (e[:-1] + e[1:]) / 2
        i = int(np.argmax(h)); w = np.abs(c - c[i]) <= 2
        out.append(float((h[w] * c[w]).sum() / max(1, h[w].sum())))
        j0 = i
        while j0 > 0 and h[j0 - 1] >= 0.4 * h[i]: j0 -= 1
        j1 = i
        while j1 < len(h) - 1 and h[j1 + 1] >= 0.4 * h[i]: j1 += 1
        widths.append(j1 - j0 + 1)
    # the two half offsets are taken at the quarter points; extend to the ends
    o1, o2 = out; d = (o2 - o1) / 0.5
    e1 = o1 - d * 0.25; e2 = o2 + d * 0.25
    a = np.array([x1, y1]) + v * e1; b = np.array([x2, y2]) + v * e2
    return [int(round(a[0])), int(round(a[1])), int(round(b[0])), int(round(b[1]))], max(widths) if widths else 0


if __name__ == '__main__':
    for q in sys.argv[1:]:
        f = q.split(','); p = f[0]; x1, y1, x2, y2 = [float(v) for v in f[1:5]]; s = int(f[5]) if len(f) > 5 else 6
        seg, w = snap(p, x1, y1, x2, y2, s)
        print(p, ' '.join(str(int(v)) for v in (x1, y1, x2, y2)), '->', ' '.join(map(str, seg)), ' line width', w, ' strip', w + 2)
