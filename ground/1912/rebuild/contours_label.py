"""Stage contours, step 3: label every contour chain with its level (5 ft steps), for the whole survey at once.

Per sheet (prepare): join fragments into chains (contours_link), map them to the ground with the sheet's georef,
measure today's LiDAR along each chain, and cast short rays across every chain to find the next contour on each side.
A contour has one level, so a chain along which today's LiDAR is nearly constant lies on unchanged ground and its
LiDAR level is a trustworthy prior; where the LiDAR varies along the chain the ground has changed and only the
neighbour relations decide (this replaces the I4 rule "LiDAR outside the works zones").
Relations (the I4 pilot_label2 idea, with rays instead of gradient paths): the neighbour is one step up or down;
the direction comes from today's LiDAR between the two lines when that ground is unchanged and sloping, it is
'same level' when the LiDAR says so (across a valley floor or a hilltop), otherwise undirected.
Merged bands (converging contours printed as one solid stroke, contours_extract): a ray that crosses a band records
'several steps' rather than one; its pixel width across the band gives a soft count, and the band's inside is left
to the surface solve between its fixed top and bottom contours.
Seams: contours meeting at a shared sheet edge are tied to the same level.
Index contours (25 ft) are levels divisible by 5 steps; the stroke weight relative to nearby contours votes for them.
Solve (label_all): robust iterated conditional modes over all chains of all sheets, from the LiDAR start.
"""
import json, os, pickle, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from shapely.geometry import shape
from shapely.prepared import prep
from shapely import contains_xy

from common import load_paths, load_all, frame_px
from sheets_index import load_sheet_model
from contours_link import link, chain_xy, index_flags
from lidar import Lidar

FT = 1200 / 3937
MIN_CHAIN = 20          # px
RAY_STEP = 6            # px between ray origins along a chain
RAY_MAX = 70            # px (about 25 m)


def zones_mask(repo):
    gj = json.load(open(Path(repo) / 'ground' / 'zones' / 'zones_post1912_works.geojson'))
    from pyproj import Transformer
    from shapely.ops import transform, unary_union
    tr = Transformer.from_crs(4326, 26916, always_xy=True).transform
    from shapely.validation import make_valid
    return unary_union([make_valid(transform(tr, shape(f['geometry']))) for f in gj['features']])


def prepare(args):
    paths, sid, outdir = args
    P = load_paths(paths); ids, _ = load_all(P); d = ids[sid]
    out = Path(P['work']) / 'chains' / f'{sid}.pkl'
    if out.exists():
        return sid, 'kept'
    t0 = time.time()
    z = np.load(Path(P['work']) / 'contours_px' / f'{sid}.npz')
    xy, off = z['xy'], z['off']; H, W = z['shape']
    paths_ = [xy[off[k]:off[k + 1]].astype(float) for k in range(len(off) - 1)]
    blk = np.unpackbits(z['black'])[:H * W].reshape(H, W).astype(bool)
    band = np.unpackbits(z['band'])[:H * W].reshape(H, W).astype(bool)
    chains = link(paths_, blk); del blk
    segl = np.diff(off); segw = z['weight']
    C = []; Wt = []
    for c in chains:
        p = chain_xy(paths_, c)
        if len(p) < MIN_CHAIN:
            continue
        C.append(p); ks = [k for k, _ in c]; Wt.append(np.average(segw[ks], weights=segl[ks]))
    Wt = np.array(Wt); L = np.array([len(p) for p in C], float)
    M, g = load_sheet_model(ids, sid, outdir)
    mpp = 0.364
    idx_flag, rel = index_flags(C, Wt, L, mpp)
    # ground coordinates (every 2nd pixel) and LiDAR along each chain
    lid = Lidar(P); zon = zones_mask(Path(paths).resolve().parent.parent)
    G = []; Z = []
    allp = np.vstack([p[::2] for p in C]); own = np.concatenate([np.full(len(p[::2]), i) for i, p in enumerate(C)])
    E, N = M.p2utm(allp[:, 0], allp[:, 1])
    zl = lid.sample(E, N) / FT
    inz = contains_xy(zon, E, N)
    zl[inz] = np.nan
    zmed = np.full(len(C), np.nan); zspr = np.full(len(C), np.nan); zfrac = np.zeros(len(C))
    o = np.argsort(own, kind='stable'); b = np.r_[0, np.cumsum(np.bincount(own, minlength=len(C)))]
    for i in range(len(C)):
        s = o[b[i]:b[i + 1]]; v = zl[s]; ok = np.isfinite(v); zfrac[i] = ok.mean() if len(v) else 0
        if ok.sum() >= 4:
            zmed[i] = np.median(v[ok]); zspr[i] = 1.4826 * np.median(np.abs(v[ok] - zmed[i]))
        G.append(np.c_[E[s], N[s]])
    # id raster and rays
    R = np.zeros((H, W), np.int32)
    for i, p in enumerate(C):
        R[p[:, 1].astype(int), p[:, 0].astype(int)] = i + 1
    R = ndi.grey_dilation(R, size=(2, 2))
    rel_a = []; rel_b = []; rel_side = []; ox = []; oy = []; hx = []; hy = []; xband = []
    for i, p in enumerate(C):
        n = len(p)
        for j in range(3, n - 3, RAY_STEP):
            t = p[min(n - 1, j + 3)] - p[max(0, j - 3)]; tl = np.hypot(*t)
            if tl < 1e-6:
                continue
            nx, ny = -t[1] / tl, t[0] / tl
            for side in (1, -1):
                nb_ = 0
                for s in range(2, RAY_MAX):
                    x = int(round(p[j, 0] + side * s * nx)); y = int(round(p[j, 1] + side * s * ny))
                    if not (0 <= x < W and 0 <= y < H):
                        break
                    nb_ += band[y, x]
                    v = R[y, x]
                    if v and v != i + 1:
                        rel_a.append(i); rel_b.append(v - 1); rel_side.append(side)
                        ox.append(p[j, 0]); oy.append(p[j, 1]); hx.append(x); hy.append(y); xband.append(nb_)
                        break
    del R, band
    rel_a = np.array(rel_a, int); rel_b = np.array(rel_b, int)
    ox, oy, hx, hy = map(lambda a: np.array(a, float), (ox, oy, hx, hy))
    # LiDAR between origin and hit: direction / equality where the ground is unchanged
    Eo, No = M.p2utm(ox, oy); Eh, Nh = M.p2utm(hx, hy)
    zo = lid.sample(Eo, No) / FT; zh = lid.sample(Eh, Nh) / FT
    bad = contains_xy(zon, Eo, No) | contains_xy(zon, Eh, Nh)
    dz = np.where(bad, np.nan, zh - zo)
    out.parent.mkdir(parents=True, exist_ok=True)
    pickle.dump(dict(sheet=sid, px=C, ground=G, weight=Wt, rel_weight=rel, idx_flag=idx_flag, length_px=L,
                     zmed=zmed, zspr=zspr, zfrac=zfrac,
                     rel=np.c_[rel_a, rel_b], dz=dz, ray_len_m=np.hypot(Eh - Eo, Nh - No),
                     band_px=np.array(xband, int)), open(out, 'wb'))
    return sid, f'{time.time() - t0:.0f}s chains {len(C)} relations {len(rel_a)} lidar-ok {np.mean(np.isfinite(zmed)):.2f}'


if __name__ == '__main__':
    paths = sys.argv[1] if len(sys.argv) > 1 else 'configs/ground_paths.json'
    outdir = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('s') else 'ground/1912'
    P = load_paths(paths); ids, _ = load_all(P)
    want = [s for s in sys.argv[2:] if s.startswith('s')] or sorted(ids)
    with Pool(int(os.environ.get('NPROC', 6))) as pool:
        for sid, msg in pool.imap_unordered(prepare, [(paths, s, outdir) for s in want]):
            print(sid, msg, flush=True)
