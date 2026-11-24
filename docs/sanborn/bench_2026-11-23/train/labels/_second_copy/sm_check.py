# explore: Ben's street map of a plate, rebuilt as street_map.py does (nothing written outside this folder)
import json, os, sys
import numpy as np, cv2
sys.path.insert(0, '../../tools/sanborn/unet'); sys.path.insert(0, '../../tools/sanborn')
import street_map as SM
from shapely.geometry import LineString, Point
from shapely.ops import unary_union, polygonize_full
N = sys.argv[1]; TOL = 1.5
B = json.load(open(f'picks22_guided/22-{N}/edges_ben.json', encoding='utf8'))
im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
L, SH = SM.editor_lines(N, W, H, json.load(open(f'unet_data/{N}_edges.json', encoding='utf8')), B)
def ext(l):
    a, b = np.array(l['a'], float), np.array(l['b'], float); d = (b - a) / np.hypot(*(b - a)); return LineString([a - d * TOL, b + d * TOL])
P = sorted(polygonize_full(unary_union([ext(l) for l in L]))[0].geoms, key=lambda p: (round(p.centroid.y / 400), p.centroid.x))
P = [p for p in P if p.area >= 400]
import collections
print(N, W, H, 'lines', len(L), collections.Counter(l['kind'] for l in L), 'faces', len(P))
for i, p in enumerate(P):
    (cx, cy), (w, h), _ = cv2.minAreaRect(np.array(p.exterior.coords, np.float32)); print(i + 1, round(p.area), 'narrow', round(min(w, h)), 'c', round(cx), round(cy), 'holes', len(p.interiors))
if N == '44':
    S = json.load(open('streetmap/22-44.json', encoding='utf8'))
    same = [dict(a=[round(v, 1) for v in l['a']], b=[round(v, 1) for v in l['b']], kind=l['kind'], name=l['name']) for l in L] == S['lines']
    print('lines equal to streetmap/22-44.json:', same, 'blocks', len(S['blocks']), len(P))
sc = 0.25; c = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA); ov = c.copy(); rng = np.random.default_rng(3)
for p in P: cv2.fillPoly(ov, [(np.array(p.exterior.coords) * sc).astype(np.int32)], tuple(int(v) for v in rng.integers(60, 230, 3)))
c = (c * 0.5 + ov * 0.5).astype(np.uint8); COL = dict(printed=(0, 90, 0), drawn=(200, 0, 200), sheet_edge=(180, 140, 0), no_printed_line=(255, 90, 0))
for l in L: cv2.line(c, tuple((np.array(l['a']) * sc).astype(int).tolist()), tuple((np.array(l['b']) * sc).astype(int).tolist()), COL[l['kind']], 2, cv2.LINE_AA)
for s in B['lines']:
    if s.get('verdict') == 'wrong': cv2.line(c, tuple((np.array(s['a0']) * sc).astype(int).tolist()), tuple((np.array(s['b0']) * sc).astype(int).tolist()), (0, 0, 255), 1, cv2.LINE_AA)
cv2.imwrite(f'bench_2026-11-23/train/labels/explore/{N}_sm.jpg', c, [cv2.IMWRITE_JPEG_QUALITY, 88])
