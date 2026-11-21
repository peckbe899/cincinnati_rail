"""Census step 3: thumbnails with the batch's exported sides and the regions the outline step dropped (21 Nov 2026).

    python thumbs.py N [N ...]  [--w 1700]   -> thumbs/thumb_N.jpg
    python thumbs.py --sheet N [N ...]        -> thumbs/sheet_<first>.jpg, small panels side by side (contact sheet)

Drawn on the scan (lightened):
  red fill       street ground enclosed by a block region (holes of area >= MIN_AREA): its sides are never fitted
  magenta fill   block regions inside such a hole (nesting depth 2, 4, ...): dropped by RETR_EXTERNAL (outlines.py:92)
  blue outline   the largest block region (the one that rings the sheet on uncut sheets)
  cyan fill      outer block regions that straighten() returned nothing for (no fitted side): also dropped
  green / orange the sides the line editor shows (N_edges.json)
  grey           sides dropped by step 4: 'short' pieces and paper-edge sides
For 43, 44, 45, 80, 82A the outlines are the census copy (guided_ol/), the batch did not run them.
"""
import json, os, sys
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'thumbs'); os.makedirs(OUT, exist_ok=True)
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = D + 'unet_data/'
GUIDED = {'43', '44', '45', '80', '82A'}; MIN_AREA = 6000


def draw(n, w_out):
    full = cv2.imread(D + f'cufp/22-{n}.jpg', cv2.IMREAD_REDUCED_COLOR_4); H4, W4 = full.shape[:2]
    if n in GUIDED:
        bm = cv2.imread(HERE + f'/guided_ol/{n}_blockmask.png', 0); polys = json.load(open(HERE + f'/guided_ol/{n}_outlines_poly.json', encoding='utf8'))
        edges = [dict(a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange') for p in polys for s in p if not (s['state'] == 'short' or s.get('paper_edge'))]
    else:
        bm = cv2.imread(U + f'{n}_blockmask.png', 0); polys = json.load(open(D + f'picks22_guided/22-{n}/outlines.json', encoding='utf8'))
        edges = json.load(open(U + f'{n}_edges.json', encoding='utf8'))
    b = (bm > 0).astype(np.uint8); s = W4 / b.shape[1]           # half size -> quarter size: 0.5
    vis = (full * 0.55 + 115).astype(np.uint8); over = vis.copy()
    allc, hier = cv2.findContours(b, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    if hier is not None:
        hier = hier[0]
        def dep(i):
            d = 0
            while hier[i][3] >= 0: i = hier[i][3]; d += 1
            return d
        D_ = [dep(i) for i in range(len(allc))]
        sc = lambda c: (c.astype(np.float32) * s).round().astype(np.int32)
        for i, c in enumerate(allc):        # holes (odd depth) red, then nested blocks (even depth > 0) magenta on top
            if D_[i] % 2 == 1 and cv2.contourArea(c) * 4 >= MIN_AREA: cv2.drawContours(over, [sc(c)], -1, (60, 60, 235), -1)
        for i, c in enumerate(allc):
            if D_[i] % 2 == 0 and D_[i] > 0: cv2.drawContours(over, [sc(c)], -1, (200, 60, 200), -1)
        k, cc, st, _ = cv2.connectedComponentsWithStats(b, connectivity=4)
        if k > 1:
            big = (cc == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
            bc = cv2.findContours(big, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]
        # outer regions that produced no polygon: compare each RETR_EXTERNAL contour with the polygons' vertices
        ext = cv2.findContours(b, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]
        pv = np.array([pt for p in polys for sd in p for pt in (sd['a'], sd['b'])], np.float32) / 2 if polys else np.zeros((0, 2), np.float32)
        for c in ext:
            if cv2.contourArea(c) * 4 < MIN_AREA: continue
            x, y, w, h = cv2.boundingRect(c)
            inside = ((pv[:, 0] >= x - 8) & (pv[:, 0] <= x + w + 8) & (pv[:, 1] >= y - 8) & (pv[:, 1] <= y + h + 8)).sum() if len(pv) else 0
            if inside == 0: cv2.drawContours(over, [sc(c)], -1, (220, 200, 40), -1)
        vis = cv2.addWeighted(over, 0.45, vis, 0.55, 0)
        if k > 1: cv2.drawContours(vis, [sc(c) for c in bc], -1, (200, 90, 0), 3)
    for p in polys:
        for sd in p:
            if sd['state'] == 'short' or sd.get('paper_edge'):
                a = tuple((np.array(sd['a']) / 4).round().astype(int)); bb = tuple((np.array(sd['b']) / 4).round().astype(int)); cv2.line(vis, a, bb, (150, 150, 150), 2, cv2.LINE_AA)
    for e in edges:
        a = tuple((np.array(e['a']) / 4).round().astype(int)); bb = tuple((np.array(e['b']) / 4).round().astype(int))
        cv2.line(vis, a, bb, (0, 150, 0) if e['state'] == 'green' else (0, 140, 255), 3, cv2.LINE_AA)
    f = w_out / W4; vis = cv2.resize(vis, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    return vis


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    w = int(sys.argv[sys.argv.index('--w') + 1]) if '--w' in sys.argv else 1700
    if '--w' in sys.argv: args = [a for a in args if a != str(w)]
    if '--sheet' in sys.argv:
        tiles = []
        for n in args:
            t = draw(n, 560); t = cv2.copyMakeBorder(t, 0, max(0, 380 - t.shape[0]), 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))[:380]
            cv2.putText(t, n, (8, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 200), 3); tiles.append(cv2.copyMakeBorder(t, 3, 3, 3, 3, cv2.BORDER_CONSTANT, value=(0, 0, 0)))
        while len(tiles) % 3: tiles.append(np.full_like(tiles[0], 255))
        rows = [np.hstack(tiles[k:k + 3]) for k in range(0, len(tiles), 3)]
        cv2.imwrite(OUT + f'/sheet_{args[0]}.jpg', np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])
    else:
        for n in args:
            cv2.imwrite(OUT + f'/thumb_{n}.jpg', draw(n, w), [cv2.IMWRITE_JPEG_QUALITY, 85]); print('thumb', n, flush=True)
