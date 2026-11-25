"""The plate context the string classifier reads, at half size (2 full px per context px):
  lines   Ben's street sides: streetmap/22-N.json on 44; his edited editor lines (street_map.editor_lines with
          picks22_guided/22-N/edges_ben.json) on 1A and 5; the networks' editor lines with no edits elsewhere
  block   inside a closed ring of those lines (polygonized as street_map.py does) = 1
  dist    distance to the nearest line (full px) and that line's direction
  fill    building fill by colour (the formula of ink_bins.py)
  pipe    ink_bins bins 6 and 7 (water pipe, sewer)
  lot     ink_bins bin 2 (lot line)
  paper   the sheet
Read only: nothing in the repo is written. Import of street_map / edit_server from tools/sanborn/unet needs python -B."""
import json, os, sys
import numpy as np
import cv2
from shapely.geometry import LineString
from shapely.ops import unary_union, polygonize_full

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *(['..'] * 6)))
UNET = os.path.join(REPO, 'tools', 'sanborn', 'unet')
F = 2   # full px per context px


def ben_lines(N, W, H):
    smf = f'streetmap/22-{N}.json'
    if os.path.exists(smf):
        J = json.load(open(smf, encoding='utf8'))
        return [dict(a=l['a'], b=l['b'], kind=l['kind']) for l in J['lines']], 'streetmap (Ben ground truth)'
    sys.path.insert(0, UNET)
    import street_map  # noqa: E402
    bf = f'picks22_guided/22-{N}/edges_ben.json'
    ben = json.load(open(bf, encoding='utf8')) if os.path.exists(bf) else None
    L, _ = street_map.editor_lines(N, W, H, json.load(open(f'unet_data/{N}_edges.json', encoding='utf8')), ben)
    return [dict(a=l['a'], b=l['b'], kind=l['kind']) for l in L], ('editor lines with Ben edits (' + bf + ')' if ben else 'networks editor lines, no Ben edits')


def blocks_of(L, tol=1.5):
    def ext(l):
        a, b = np.array(l['a'], float), np.array(l['b'], float); d = (b - a) / max(np.hypot(*(b - a)), 1e-6); return LineString([a - d * tol, b + d * tol])
    P = [p for p in polygonize_full(unary_union([ext(l) for l in L]))[0].geoms if p.area >= 400]
    return [np.array(p.exterior.coords) for p in P]


def load(N):
    im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
    h2, w2 = (H + F - 1) // F, (W + F - 1) // F
    sm = cv2.resize(im, (w2, h2), interpolation=cv2.INTER_AREA)
    L, src = ben_lines(N, W, H)
    lid = np.zeros((h2, w2), np.int32)
    for i, l in enumerate(L):
        cv2.line(lid, tuple(np.round(np.array(l['a']) / F).astype(int).tolist()), tuple(np.round(np.array(l['b']) / F).astype(int).tolist()), i + 1, 1)
    src0 = (lid == 0).astype(np.uint8)
    dist, lab = cv2.distanceTransformWithLabels(src0, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    zl = lab[lid > 0]; zi = lid[lid > 0]; look = np.zeros(lab.max() + 1, np.int32); look[zl] = zi
    near = look[lab] - 1                                    # index of the nearest line at every context px
    dirs = np.array([[l['b'][0] - l['a'][0], l['b'][1] - l['a'][1]] for l in L], float)
    dirs /= np.maximum(np.hypot(*dirs.T), 1e-6)[:, None]
    blk = np.zeros((h2, w2), np.uint8)
    rings = blocks_of(L)
    for r in rings: cv2.fillPoly(blk, [np.round(r / F).astype(np.int32)], 1)
    lab_ = cv2.cvtColor(sm, cv2.COLOR_BGR2LAB); Lc = lab_[..., 0]
    a = cv2.medianBlur(lab_[..., 1], 5).astype(np.int16) - 128; b = cv2.medianBlur(lab_[..., 2], 5).astype(np.int16) - 128
    fill = (((a >= 7) & (b <= 26)) | (b >= 32)) & (Lc >= 140)
    fill = cv2.morphologyEx(cv2.morphologyEx(fill.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)), cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    bins = cv2.imread(f'unet_data/{N}_bins.png', 0)
    def half(m): return cv2.resize(m.astype(np.uint8), (w2, h2), interpolation=cv2.INTER_AREA) > 0
    pipe = half((bins == 6) | (bins == 7)); lot = half(bins == 2); bline = half(bins == 1)
    al = np.load(f'cufp/{N}/png_alpha_s4.npy'); paper = cv2.resize((al > 0).astype(np.uint8), (w2, h2), interpolation=cv2.INTER_NEAREST) > 0
    names = []
    sf = f'picks22_guided/22-{N}/streets_marked.json'
    if os.path.exists(sf):
        for s in json.load(open(sf, encoding='utf8')):
            if s.get('left') and s.get('right'):
                ring = np.array(s['left'] + s['right'][::-1], float)
                names.append(dict(name=s['name'], ring=ring))
    return dict(N=N, W=W, H=H, lines=L, src=src, dist=dist * F, near=near, dirs=dirs, block=blk, fill=fill > 0, pipe=pipe, lot=lot,
                bline=bline, paper=paper, rings=rings, streets=names, im_small=sm)


def at(C, m, x, y):
    """value of context raster m at full-size point(s) x, y"""
    xi = np.clip(np.round(np.asarray(x) / F).astype(int), 0, m.shape[1] - 1); yi = np.clip(np.round(np.asarray(y) / F).astype(int), 0, m.shape[0] - 1)
    return m[yi, xi]
