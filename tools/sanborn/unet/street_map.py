"""The street map of a plate: Ben's finished lines, saved as the plate's street sides (17 November 2026).

    cd data/sanborn
    python ../../tools/sanborn/unet/street_map.py N [--tol 1.5] [--edge 60]

Ben, 17 November 2026, on plate 44: "I have given the ground truth for 44" and "Let's save this is the street map".
Reads the plate's lines as the line editor shows them (unet_data/N_edges.json, cleaned by edit_server.clean, plus the
sheet's outline) with Ben's edits applied (picks22_guided/22-N/edges_ben.json): a line he deleted is gone, a line he
moved is where he put it, a line he drew is added, and a line he never touched stands if it was shown to him (on a
printed line, not settled, or sheet edge; the pieces hidden by default are not part of the truth).

Writes streetmap/22-N.json:
  lines      every street side: a, b (plate px), kind (printed | sheet_edge | drawn | no_printed_line), name
  blocks     the shapes the lines close into (ends within --tol px count as meeting: "1px on this is a rounding error")
  open_ends  line ends that meet no other line, each marked sheet_edge (within --edge px of the paper's edge) or inside

Open ends are meant. Ben: "I did not close any streets that continue on other sheets. if we close them, it only makes
it so that the road 'ends' on this sheet. Any road that continues is kept open." The same holds where a street stops at
the creek, the canal or the railway ("Yes, leave open"), and Ludlow's two sides do not line up because it is a viaduct.
Nothing here closes a street. A picture goes to unet_data/N_streetmap.jpg (blocks tinted, open ends ringed).
"""
import json, os, sys
import numpy as np
import cv2
from shapely.geometry import LineString, Point
from shapely.ops import unary_union, polygonize_full
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
import edit_server as es  # noqa: E402

def arg(name, default):
    return float(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default

def main():
    N = sys.argv[1]; TOL = arg('--tol', 1.5); EDGE = arg('--edge', 60.0)
    bf = f'picks22_guided/22-{N}/edges_ben.json'; B = json.load(open(bf, encoding='utf8'))
    im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
    SH = es.sheet(N, W, H); E = es.clean(json.load(open(f'unet_data/{N}_edges.json', encoding='utf8'))) + SH
    key = lambda a, b: tuple(round(v) for v in a + b); by = {key(l['a0'], l['b0']): l for l in B['lines'] if not l.get('added')}
    KIND = dict(green='printed', orange='printed', sheet='sheet_edge'); L = []
    for e in E:
        s = by.get(key(e['a'], e['b']))
        if s:
            if s.get('verdict') == 'wrong': continue
            L.append(dict(a=s['a'], b=s['b'], kind='no_printed_line' if s.get('verdict') == 'none' else KIND.get(e['state'], 'printed'), name=e.get('name', ''), moved=bool(s.get('moved'))))
        elif e['state'] in KIND: L.append(dict(a=e['a'], b=e['b'], kind=KIND[e['state']], name=e.get('name', ''), moved=False))
    L += [dict(a=l['a'], b=l['b'], kind='no_printed_line' if l.get('verdict') == 'none' else 'drawn', name='', moved=False) for l in B['lines'] if l.get('added') and l.get('verdict') != 'wrong']
    L = [l for l in L if np.hypot(l['b'][0] - l['a'][0], l['b'][1] - l['a'][1]) > 0.05]
    def ext(l):
        a, b = np.array(l['a'], float), np.array(l['b'], float); d = (b - a) / np.hypot(*(b - a)); return LineString([a - d * TOL, b + d * TOL])
    ls = [LineString([l['a'], l['b']]) for l in L]; paper = unary_union([LineString([s['a'], s['b']]) for s in SH])
    P = sorted(polygonize_full(unary_union([ext(l) for l in L]))[0].geoms, key=lambda p: (round(p.centroid.y / 400), p.centroid.x))
    P = [p for p in P if p.area >= 400]   # slivers where three lines cross within the tolerance
    blocks = []
    for i, p in enumerate(P):
        (cx, cy), (w, h), _ = cv2.minAreaRect(np.array(p.exterior.coords, np.float32))
        blocks.append(dict(id=i + 1, area_px=round(p.area), narrow_px=round(min(w, h)), ring=[[round(x, 1), round(y, 1)] for x, y in p.exterior.coords[:-1]]))
    ends = []
    for i, l in enumerate(L):
        for p in (l['a'], l['b']):
            g = min(o.distance(Point(p)) for j, o in enumerate(ls) if j != i)
            if g > TOL: d = paper.distance(Point(p)); ends.append(dict(at=[round(p[0], 1), round(p[1], 1)], gap_px=round(g, 1), where='sheet_edge' if d <= EDGE else 'inside', paper_edge_px=round(d)))
    kinds = {k: [sum(1 for l in L if l['kind'] == k), round(sum(ls[i].length for i, l in enumerate(L) if l['kind'] == k))] for k in ('printed', 'drawn', 'sheet_edge', 'no_printed_line')}
    out = dict(plate=N, size=[W, H], source=bf, source_saved_at=B.get('saved_at'), tolerance_px=TOL, sheet_edge_px=EDGE,
               note="Ben's ground truth street sides. Open ends are meant: a street that carries on to another sheet, or stops at the creek, canal or railway, is left open.",
               counts=dict(lines=len(L), length_px=round(sum(l.length for l in ls)), by_kind=kinds, blocks=len(blocks), open_ends=len(ends), open_at_sheet_edge=sum(e['where'] == 'sheet_edge' for e in ends), open_inside=sum(e['where'] == 'inside' for e in ends)),
               lines=[dict(a=[round(v, 1) for v in l['a']], b=[round(v, 1) for v in l['b']], kind=l['kind'], name=l['name']) for l in L], blocks=blocks, open_ends=ends)
    os.makedirs('streetmap', exist_ok=True); f = f'streetmap/22-{N}.json'
    json.dump(out, open(f, 'w', encoding='utf8', newline='\n'), separators=(',', ':')); print(f, json.dumps(out['counts']))
    print('blocks under 60 px across (alleys closed at both ends, or slivers):', [(b['id'], b['narrow_px'], b['area_px']) for b in blocks if b['narrow_px'] < 60])
    sc = 0.25; c = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA); ov = c.copy(); rng = np.random.default_rng(3)
    for p in P: cv2.fillPoly(ov, [(np.array(p.exterior.coords) * sc).astype(np.int32)], tuple(int(v) for v in rng.integers(60, 230, 3)))
    c = (c * 0.5 + ov * 0.5).astype(np.uint8); COL = dict(printed=(0, 90, 0), drawn=(200, 0, 200), sheet_edge=(180, 140, 0), no_printed_line=(255, 90, 0))
    for l in L: cv2.line(c, tuple((np.array(l['a']) * sc).astype(int).tolist()), tuple((np.array(l['b']) * sc).astype(int).tolist()), COL[l['kind']], 2, cv2.LINE_AA)
    for b, p in zip(blocks, P): q = p.representative_point(); cv2.putText(c, str(b['id']), (int(q.x * sc) - 8, int(q.y * sc) + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2, cv2.LINE_AA)
    for e in ends: cv2.circle(c, (int(e['at'][0] * sc), int(e['at'][1] * sc)), 8, (200, 120, 0) if e['where'] == 'sheet_edge' else (0, 0, 255), 2)
    cv2.imwrite(f'unet_data/{N}_streetmap.jpg', c, [cv2.IMWRITE_JPEG_QUALITY, 88])

if __name__ == '__main__':
    main()
