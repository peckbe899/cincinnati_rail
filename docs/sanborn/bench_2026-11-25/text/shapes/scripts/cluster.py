"""Cluster the glyphs of extract_glyphs.py by shape, and draw montage sheets for labelling (shapes prototype).

    python -B bench_2026-11-25/text/shapes/scripts/cluster.py                    (from data/sanborn)   round 1
    python -B bench_2026-11-25/text/shapes/scripts/cluster.py --round2 pred.npz  (round 2)

Reads glyphs/*.npz. Round 1 writes clusters.npz (band and cluster of every glyph) and montage sheets in montage/.
Round 2 (after a round of labels and classify.py) clusters again only the glyphs of 12 px or more that the round-1
reader did not call junk, or called junk but from further than 0.35 from every training glyph (so the plain bits of
line are out of contention and the clusters are spent on lettering); it writes clusters2.npz (cluster ids 3000+
small, 4000+ large; -1 for glyphs left out) and montage2/. Its k: small 300, large 100.

Features of a glyph (all from its 32 x 32 image, turned upright by its word's direction):
  - pixels: the image blurred (sigma 1) and shrunk to 16 x 16, scaled to unit length            (256 values)
  - HOG: cv2.HOGDescriptor, 32 px window, 16 px blocks, 8 px stride and cells, 9 directions      (324 values)
  - size: log of its turned height and width in px (letter size on the print is the same at every scale)
Pixels and HOG each have weight 1, size weight 0.6 (per log unit). PCA to 60 dims, then k-means (cv2.kmeans,
k-means++ start, 3 tries) in three size bands of the longest side: tiny < 12 px (dots, quotes, commas, bits of line),
small 12-40 px (house numbers, lot figures, small letters), large 40-130 px (street names, block numbers).
k is set per band (K below). Inside a band the clusters are put in the leaf order of an average-linkage tree of
their centres, so look-alike clusters sit next to each other on the sheets.
"""
import glob, os, sys
import numpy as np
import cv2
from scipy.cluster.hierarchy import linkage, leaves_list

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANDS = [('tiny', 0, 12), ('small', 12, 40), ('large', 40, 131)]
K = dict(tiny=30, small=300, large=120)
K2 = dict(small=300, large=100)
W_SIZE = 0.6; NPCA = 60; PER_SHEET = 20; PER_ROW = 26; T = 38


def features(imgs, hw):
    x = imgs.astype(np.float32) / 255
    pix = np.stack([cv2.resize(cv2.GaussianBlur(g, (0, 0), 1.0), (16, 16), interpolation=cv2.INTER_AREA).ravel() for g in x])
    pix /= np.linalg.norm(pix, axis=1, keepdims=True) + 1e-6
    hog = cv2.HOGDescriptor((32, 32), (16, 16), (8, 8), (8, 8), 9)
    H = np.stack([hog.compute(g).ravel() for g in imgs])
    H /= np.linalg.norm(H, axis=1, keepdims=True) + 1e-6
    sz = np.log(np.maximum(hw, 1)) * W_SIZE
    return np.hstack([pix, H, sz]).astype(np.float32)


def load():
    P = []
    for f in sorted(glob.glob(os.path.join(HERE, 'glyphs', '*.npz'))):
        D = np.load(f); n = len(D['imgs'])
        P.append(dict(plate=np.array([str(D['plate'])] * n), idx=np.arange(n), imgs=D['imgs'], hw=D['hw']))
    return {k: np.concatenate([p[k] for p in P]) for k in P[0]}


def tile(g, lab=None):
    t = np.full((T, T), 255, np.uint8); t[3:35, 3:35] = 255 - g
    return t


def main():
    G = load(); n = len(G['imgs']); print(n, 'glyphs')
    F = features(G['imgs'], G['hw'])
    mx = G['hw'].max(1)
    r2 = '--round2' in sys.argv; bases = {'tiny': 0, 'small': 1000, 'large': 2000}; bands = BANDS; KK = K; mdir = 'montage'; cfile = 'clusters.npz'
    alive = np.ones(n, bool)
    if r2:
        P = np.load(sys.argv[sys.argv.index('--round2') + 1], allow_pickle=True)
        key = {(p, i): j for j, (p, i) in enumerate(zip(G['plate'], G['idx']))}
        alive[:] = False
        for p, i, c, d in zip(P['plate'], P['idx'], P['char'], P['dist']):
            if c != 'junk' or d > 0.35: alive[key[(p, int(i))]] = True
        bases = {'small': 3000, 'large': 4000}; bands = BANDS[1:]; KK = K2; mdir = 'montage2'; cfile = 'clusters2.npz'
        print(int(alive.sum()), 'glyphs kept for round 2')
    band = np.zeros(n, np.int8); cl = np.full(n, -1, np.int32); order = {}
    rng = np.random.default_rng(0)
    os.makedirs(os.path.join(HERE, mdir), exist_ok=True)
    pcas = {}
    for b, (name, lo, hi) in enumerate(bands):
        sel = np.nonzero((mx >= lo) & (mx < hi) & alive)[0]; band[sel] = b
        X = F[sel]; mu = X.mean(0); Xc = X - mu
        sub = Xc[rng.choice(len(Xc), min(30000, len(Xc)), replace=False)]
        _, _, Vt = np.linalg.svd(sub, full_matrices=False); V = Vt[:NPCA].T
        Z = (Xc @ V).astype(np.float32); pcas[name] = (mu, V)
        k = KK[name]
        crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 60, 1e-4)
        _, lab, C = cv2.kmeans(Z, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
        lab = lab.ravel()
        lv = leaves_list(linkage(C, 'average'))
        remap = np.empty(k, int); remap[lv] = np.arange(k)
        cl[sel] = remap[lab] + bases[name]
        print(name, len(sel), 'glyphs, k =', k)
    # sheets
    ids = np.unique(cl[cl >= 0])
    sheets = []
    for name, base in bases.items():
        cids = [c for c in ids if base <= c < base + 1000]
        for s0 in range(0, len(cids), PER_SHEET):
            rows = []
            for c in cids[s0:s0 + PER_SHEET]:
                mem = np.nonzero(cl == c)[0]
                pick = mem if len(mem) <= PER_ROW else rng.choice(mem, PER_ROW, replace=False)
                row = np.full((T, 150 + PER_ROW * T), 255, np.uint8)
                mean = G['imgs'][mem].astype(np.float32).mean(0).astype(np.uint8)
                row[:, 110:110 + T] = tile(mean)
                for j, i in enumerate(pick): row[:, 150 + j * T:150 + (j + 1) * T] = tile(G['imgs'][i])
                cv2.putText(row, f'{c}', (2, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.55, 0, 1)
                pl = np.unique(G['plate'][mem])
                cv2.putText(row, f'n{len(mem)} {int(np.median(mx[mem]))}px', (2, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 0, 1)
                rows.append(row); rows.append(np.full((2, row.shape[1]), 180, np.uint8))
            sheet = np.vstack(rows)
            fn = os.path.join(HERE, mdir, f'{name}_{s0 // PER_SHEET:02d}.png'); cv2.imwrite(fn, sheet); sheets.append(fn)
    np.savez_compressed(os.path.join(HERE, cfile), plate=G['plate'], idx=G['idx'], band=band, cl=cl)
    print(len(ids), 'clusters,', len(sheets), 'sheets')


if __name__ == '__main__':
    main()
