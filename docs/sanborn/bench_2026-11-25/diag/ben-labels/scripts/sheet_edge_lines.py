"""Q3 (ben-labels, 25 Nov 2026): the street sides Ben drew along the sheet edges on 1A and 5 (and 44 for comparison).
    cd data/sanborn; python -B bench_2026-11-25/diag/ben-labels/scripts/sheet_edge_lines.py
A line of his final street map (kind drawn = added by him, or printed / sheet_edge) is 'along the sheet edge' when the
median distance of its points (every 2 px) to the paper's edge is at most EDGE_PX (60, street_map.py's sheet_edge_px).
Ink support = share of its points with edgenet ink within 2 px, the ink taken only on the paper at least 4 px in from
its edge (the scan's dark background and the trimmed edge's shadow are not ink). 'no ink' = support < 0.3; 'weak'
0.3-0.7. Taught = shares of the line target (LINE 3 px) in the current labels: 1A train_v2 (map), 5 map recipe now.
Writes crops of the inkless ones (sheet_edge_crops_N.jpg).
"""
import sys, os, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa
EDGE_PX = 60
SETS = {'1A': (SP + 'train_v2/1A/streetmap.json', SP + 'train_v2/1A/lines.png', 'train_v2 map (V1, V2)'),
        '5': (DIAG + '/map_now/5_streetmap.json', DIAG + '/map_now/5_lines.png', 'map recipe now (not trained)'),
        '44': (SP + 'streetmap/22-44.json', DIAG + '/map_now/44_lines.png', 'map recipe (hypothetical)')}
def pts(a, b, step=2.0):
    a, b = np.asarray(a, float), np.asarray(b, float); L = np.hypot(*(b - a)); n = max(2, int(L / step) + 1)
    return a + np.linspace(0, 1, n)[:, None] * (b - a)
res = {}
for N, (smf, tf, tname) in SETS.items():
    full = scan(N); H, W = full.shape[:2]; af = alpha_full(N, W, H)
    inner = cv2.erode(af.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    ink = ink_edgenet(full) & inner
    dink = cv2.distanceTransform((~ink).astype(np.uint8), cv2.DIST_L2, 5); dedge = cv2.distanceTransform(af.astype(np.uint8), cv2.DIST_L2, 5)
    t = cv2.imread(tf, 0); sm = json.load(open(smf, encoding='utf8'))
    rows = []
    for l in sm['lines']:
        p = pts(l['a'], l['b']); x = np.clip(p[:, 0].round().astype(int), 0, W - 1); y = np.clip(p[:, 1].round().astype(int), 0, H - 1)
        de = float(np.median(dedge[y, x])); sup = float((dink[y, x] <= 2).mean()); L = float(np.hypot(l['b'][0] - l['a'][0], l['b'][1] - l['a'][1]))
        m = (raster([(l['a'], l['b'])], (H, W), 1.0, LINE) > 0) & af; v = t[m]
        rows.append(dict(kind=l['kind'], a=l['a'], b=l['b'], length=round(L), edge_dist=round(de, 1), ink=round(sup, 3), along_edge=de <= EDGE_PX,
                         taught=dict(pos=round(float((v == 1).mean()), 3) if len(v) else None, neg=round(float((v == 0).mean()), 3) if len(v) else None, uns=round(float((v == 255).mean()), 3) if len(v) else None, px=int(len(v)))))
    out = {}
    for kind in ('drawn', 'printed', 'sheet_edge'):
        R = [r for r in rows if r['kind'] == kind]; E = [r for r in R if r['along_edge']]
        cat = lambda rr: {'no ink (<0.3)': sum(r['ink'] < 0.3 for r in rr), 'weak (0.3-0.7)': sum(0.3 <= r['ink'] < 0.7 for r in rr), 'inked (>=0.7)': sum(r['ink'] >= 0.7 for r in rr)}
        catL = lambda rr: {'no ink (<0.3)': sum(r['length'] for r in rr if r['ink'] < 0.3), 'weak (0.3-0.7)': sum(r['length'] for r in rr if 0.3 <= r['ink'] < 0.7), 'inked (>=0.7)': sum(r['length'] for r in rr if r['ink'] >= 0.7)}
        tpx = lambda rr: (lambda P: {k: round(sum(r['taught'][k] * r['taught']['px'] for r in rr if r['taught']['px']) / max(1, P), 3) for k in ('pos', 'neg', 'uns')})(sum(r['taught']['px'] for r in rr))
        out[kind] = dict(lines=len(R), along_edge=len(E), along_edge_by_ink=cat(E), along_edge_length_by_ink=catL(E), inside_by_ink=cat([r for r in R if not r['along_edge']]),
                         along_edge_noink_taught=tpx([r for r in E if r['ink'] < 0.3]), along_edge_weak_taught=tpx([r for r in E if 0.3 <= r['ink'] < 0.7]), all_inkless_taught=tpx([r for r in R if r['ink'] < 0.3]))
    res[N] = dict(labels=tname, **out); print(N, json.dumps(res[N]), flush=True)
    # crops of the drawn lines along the edge with little ink
    sel = [r for r in rows if r['kind'] == 'drawn' and r['along_edge'] and r['ink'] < 0.7][:12]
    tiles = []
    for r in sel:
        a, b = np.array(r['a']), np.array(r['b']); c = ((a + b) / 2).round().astype(int); half = 220
        x0, y0 = max(0, c[0] - half), max(0, c[1] - half); x1, y1 = min(W, c[0] + half), min(H, c[1] + half)
        crop = full[y0:y1, x0:x1].copy(); cv2.line(crop, tuple((a - [x0, y0]).round().astype(int)), tuple((b - [x0, y0]).round().astype(int)), (255, 0, 255), 1, cv2.LINE_AA)
        crop = cv2.copyMakeBorder(crop, 0, 2 * half - crop.shape[0], 0, 2 * half - crop.shape[1], cv2.BORDER_CONSTANT, value=(80, 80, 80))
        cv2.putText(crop, f"ink {r['ink']:.2f} edge {r['edge_dist']:.0f}px", (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2); tiles.append(crop)
    if tiles:
        while len(tiles) % 4: tiles.append(np.full_like(tiles[0], 80))
        cv2.imwrite(os.path.join(DIAG, f'sheet_edge_crops_{N}.jpg'), np.vstack([np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]), [cv2.IMWRITE_JPEG_QUALITY, 85])
    json.dump(rows, open(os.path.join(DIAG, f'sheet_edge_rows_{N}.json'), 'w'), indent=0)
wj(os.path.join(DIAG, 'sheet_edge_lines.json'), res)
