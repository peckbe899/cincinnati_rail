"""Random sample of exported hole sides (runs_plates/new) for an eye check: is the side a real street side?

    python sample_holes.py [K] [SEED] [PLATES_FILE] [RUN] [OUTDIR]   -> OUTDIR/montage_*.jpg, OUTDIR/sample.json
      RUN default new, OUTDIR default sample_holes (the PDF sample); e.g. 24 11 cut_plates.txt final sample_holes_cut

Draws K points uniformly by length over every exported hole side (not short, not paper_edge) of the plates in
PLATES_FILE (default pdf_sheets.txt), marks for each whether the hole survives the gate (runs_plates/new_gate has the same
hole polygon), and cuts a 640 x 640 full-px window around the point, scaled to 320 px: the scan, the side cyan (point
red), other exported sides of that run thin green/orange. Montages of 4 x 3 tiles with the sample number.
Judged by eye afterwards into sample_holes/verdicts.json (written by hand from the montages).
"""
import json, os, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
K = int(sys.argv[1]) if len(sys.argv) > 1 else 48; SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 7
pf = sys.argv[3] if len(sys.argv) > 3 else HERE + 'pdf_sheets.txt'
RUN = sys.argv[4] if len(sys.argv) > 4 else 'new'; OD = HERE + (sys.argv[5] if len(sys.argv) > 5 else 'sample_holes') + '/'
plates = open(pf).read().split()
segs = []
for n in plates:
    P = json.load(open(HERE + f'runs_plates/{RUN}/{n}/outlines.json', encoding='utf8'))
    G = json.load(open(HERE + f'runs_plates/new_gate/{n}/outlines.json', encoding='utf8')) if os.path.exists(HERE + f'runs_plates/new_gate/{n}/outlines.json') else []
    gkeys = {(tuple(p[0]['a']), tuple(p[0]['b'])) for p in G if p and p[0].get('hole')}
    for hi, p in enumerate(P):
        if not (p and p[0].get('hole')): continue
        kept = (tuple(p[0]['a']), tuple(p[0]['b'])) in gkeys
        for s in p:
            if s['state'] == 'short' or s.get('paper_edge'): continue
            L = float(np.hypot(s['b'][0] - s['a'][0], s['b'][1] - s['a'][1])); segs.append(dict(plate=n, hole=hi, a=s['a'], b=s['b'], len=L, state=s['state'], gate_keeps=kept))
L = np.array([s['len'] for s in segs]); cum = np.cumsum(L); rng = np.random.default_rng(SEED)
pts = np.sort(rng.uniform(0, cum[-1], K))
out = []
for k, u in enumerate(pts):
    i = int(np.searchsorted(cum, u)); s = segs[i]; t = (u - (cum[i] - L[i])) / L[i]
    p = np.array(s['a']) + t * (np.array(s['b']) - np.array(s['a'])); out.append(dict(k=k, **s, point=p.round(1).tolist()))
os.makedirs(OD, exist_ok=True)
json.dump(dict(total_len=float(cum[-1]), n_sides=len(segs), gate_keeps_len=float(sum(s['len'] for s in segs if s['gate_keeps'])), sample=out), open(OD + 'sample.json', 'w'), indent=1)
R = 320; tiles = []; cache = {}
for o in out:
    n = o['plate']
    if n not in cache: cache = {n: cv2.imread(D + f'cufp/22-{n}.jpg')}
    im = cache[n]; H, W = im.shape[:2]; cx, cy = int(o['point'][0]), int(o['point'][1])
    x0, y0 = max(0, cx - R), max(0, cy - R); x1, y1 = min(W, cx + R), min(H, cy + R)
    t = np.full((2 * R, 2 * R, 3), 255, np.uint8); t[y0 - (cy - R):y1 - (cy - R), x0 - (cx - R):x1 - (cx - R)] = im[y0:y1, x0:x1]
    off = np.array([cx - R, cy - R])
    for p in json.load(open(HERE + f'runs_plates/{RUN}/{n}/outlines.json', encoding='utf8')):
        for s in p:
            if s['state'] == 'short' or s.get('paper_edge'): continue
            col = (255, 200, 0) if p[0].get('hole') else ((0, 170, 0) if s['state'] == 'on print' else (0, 140, 255))
            cv2.line(t, tuple((np.array(s['a']) - off).astype(int)), tuple((np.array(s['b']) - off).astype(int)), col, 1, cv2.LINE_AA)
    cv2.line(t, tuple((np.array(o['a']) - off).astype(int)), tuple((np.array(o['b']) - off).astype(int)), (255, 255, 0), 3, cv2.LINE_AA)
    cv2.circle(t, (R, R), 7, (0, 0, 255), 2)
    t = cv2.resize(t, (R, R), interpolation=cv2.INTER_AREA)
    cv2.rectangle(t, (0, 0), (R, 20), (255, 255, 255), -1)
    cv2.putText(t, f"#{o['k']} p{n} {'KEEP' if o['gate_keeps'] else 'gate drops'}", (4, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    tiles.append(t)
for m in range(0, len(tiles), 12):
    ts = tiles[m:m + 12] + [np.full((R, R, 3), 255, np.uint8)] * (12 - len(tiles[m:m + 12]))
    rows = [np.hstack([np.pad(x, ((2, 2), (2, 2), (0, 0)), constant_values=40) for x in ts[r * 4:(r + 1) * 4]]) for r in range(3)]
    cv2.imwrite(OD + f'montage_{m // 12}.jpg', np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])
print(len(segs), 'hole sides,', round(cum[-1]), 'px; gate keeps', round(sum(s['len'] for s in segs if s['gate_keeps'])), 'px; sample', K)
