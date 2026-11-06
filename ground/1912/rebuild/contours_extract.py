"""Stage contours, step 1: vectorise the red contour ink of one sheet into ordered pixel polylines.

Reused from the I4 pipeline (boldx.py, extract.py): red ink = LAB a* above its local background, black ink excluded,
skeletonised in 2048 px tiles at full scan resolution; segments split at junctions; per-segment stroke weight
(7 x 7 summed red excess, median along the segment); bold (index, 25 ft) segments by Otsu on the weights.
Output <work>/contours_px/<sid>.npz: concatenated pixel paths, segment offsets, bold flag, weight.
"""
import json, os, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np, cv2
from scipy import ndimage as ndi
from skimage.morphology import skeletonize, remove_small_objects
from skimage.filters import threshold_otsu

from common import load_paths, load_all, frame_px

T = 2048; OV = 64
MIN_SEG = 16          # px (about 6 m)


def tile(c):
    lab = cv2.cvtColor(c, cv2.COLOR_BGR2LAB); L = lab[..., 0].astype(np.float32); a = lab[..., 1]
    bga = cv2.medianBlur(a, 31).astype(np.float32); r = np.clip(a.astype(np.float32) - bga, 0, None)
    black = cv2.dilate((L < 100).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    m = (r > 6) & ~black; m = remove_small_objects(m, 40)
    m = ndi.binary_closing(m, np.ones((3, 3)))
    sk = skeletonize(m); sk = remove_small_objects(sk, 20, connectivity=2)
    ink = cv2.boxFilter(r, -1, (7, 7), normalize=False) / 7.0
    return sk, ink


def trace_paths(sk):
    """Split a skeleton at junctions and order each simple piece end to end. Returns list of (n,2) [x,y] arrays."""
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - 1
    seg = sk & (nb <= 2)
    seg &= ~ndi.binary_dilation(sk & (nb >= 3), np.ones((3, 3)))
    lab, n = ndi.label(seg, np.ones((3, 3)))
    if n == 0:
        return []
    objs = ndi.find_objects(lab)
    out = []
    for k, sl in enumerate(objs, 1):
        sub = lab[sl] == k
        ys, xs = np.nonzero(sub)
        if len(ys) < MIN_SEG:
            continue
        pts = set(zip(ys.tolist(), xs.tolist()))
        deg = {p: sum((p[0] + dy, p[1] + dx) in pts for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx) for p in pts}
        ends = [p for p, d in deg.items() if d <= 1]
        cur = ends[0] if ends else next(iter(pts))
        path = [cur]; seen = {cur}
        while True:
            nxt = None
            for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                q = (cur[0] + dy, cur[1] + dx)
                if q in pts and q not in seen:
                    nxt = q; break
            if nxt is None:
                break
            path.append(nxt); seen.add(nxt); cur = nxt
        if len(path) < MIN_SEG:
            continue
        p = np.array(path, float); p[:, 0] += sl[0].start; p[:, 1] += sl[1].start
        out.append(p[:, ::-1])          # x, y
    return out


def run_sheet(args):
    paths, sid = args
    P = load_paths(paths); ids, _ = load_all(P); d = ids[sid]
    out = Path(P['work']) / 'contours_px' / f'{sid}.npz'
    if out.exists():
        return sid, 'kept'
    t0 = time.time()
    im = cv2.imread(str(Path(P['sheets']) / d['file']))
    H, W = im.shape[:2]
    fr = np.zeros((H, W), np.uint8); cv2.fillPoly(fr, [np.int32(frame_px(d))], 1)
    fr = cv2.erode(fr, np.ones((25, 25), np.uint8)).astype(bool)
    SK = np.zeros((H, W), bool); INK = np.zeros((H, W), np.float32)
    for y in range(0, H, T):
        for x in range(0, W, T):
            ya, xa = max(0, y - OV), max(0, x - OV); yb, xb = min(H, y + T + OV), min(W, x + T + OV)
            sk, ink = tile(im[ya:yb, xa:xb])
            hh, ww = min(T, H - y), min(T, W - x)
            SK[y:y + hh, x:x + ww] = sk[y - ya:y - ya + hh, x - xa:x - xa + ww]
            INK[y:y + hh, x:x + ww] = ink[y - ya:y - ya + hh, x - xa:x - xa + ww]
    del im
    SK &= fr
    paths_ = trace_paths(SK)
    wt = np.array([np.median(INK[p[:, 1].astype(int), p[:, 0].astype(int)]) for p in paths_], np.float32)
    lens = np.array([len(p) for p in paths_])
    big = wt[lens >= 40]
    thr = float(threshold_otsu(big)) if len(big) > 200 else 57.0
    bold = wt >= thr
    off = np.r_[0, np.cumsum(lens)].astype(np.int64)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, xy=np.vstack(paths_).astype(np.float32) if paths_ else np.zeros((0, 2), np.float32),
                        off=off, bold=bold, weight=wt, thr=thr, shape=np.array([H, W]))
    return sid, f'{time.time() - t0:.0f}s segments {len(paths_)} px {off[-1]} bold {bold.mean():.2f} thr {thr:.1f}'


if __name__ == '__main__':
    paths = sys.argv[1] if len(sys.argv) > 1 else 'configs/ground_paths.json'
    P = load_paths(paths); ids, _ = load_all(P)
    want = [s for s in sys.argv[2:] if s.startswith('s')] or sorted(ids)
    with Pool(int(os.environ.get('NPROC', 6))) as pool:
        for sid, msg in pool.imap_unordered(run_sheet, [(paths, s) for s in want]):
            print(sid, msg, flush=True)
