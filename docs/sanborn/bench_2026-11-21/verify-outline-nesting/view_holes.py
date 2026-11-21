"""verify-outline-nesting: crops of every kept hole (street-hole polygon) on a plate, for judging by eye (21 Nov 2026).

    python view_holes.py N [N ...]   -> holes_view/N_holes.jpg (one tile per hole), holes_view/N_holes.json

Reads the agent's outline-nesting/runs_plates/final/N/outlines.json (byte-identical to my rerun of the diff on the plates I
reran). Each tile: the full-size scan around the hole (hole bbox + 220 px), hole sides that reach the editor in CYAN (thick),
hole sides dropped as short/paper edge in grey, the other (block) sides in green/orange (thin). Tile title: hole k, its
exported side length.
"""
import json, os, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
AG = D + 'bench_2026-11-21/outline-nesting/runs_plates/final/'
TILE = 420
os.makedirs(HERE + 'holes_view', exist_ok=True)
for N in sys.argv[1:]:
    full = cv2.imread(D + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
    polys = json.load(open(AG + f'{N}/outlines.json', encoding='utf8'))
    holes = [p for p in polys if p and p[0].get('hole')]; blocks = [p for p in polys if not (p and p[0].get('hole'))]
    tiles, rows = [], []
    for k, h in enumerate(holes):
        pts = np.array([s['a'] for s in h] + [s['b'] for s in h], float)
        x0, y0 = (pts.min(0) - 220).astype(int); x1, y1 = (pts.max(0) + 220).astype(int)
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        side = max(x1 - x0, y1 - y0); sc = TILE / side
        crop = (full[y0:y1, x0:x1] * 0.85 + 30).astype(np.uint8)
        crop = cv2.resize(crop, (max(1, int((x1 - x0) * sc)), max(1, int((y1 - y0) * sc))), interpolation=cv2.INTER_AREA)
        P = lambda p: (int(round((p[0] - x0) * sc)), int(round((p[1] - y0) * sc)))
        for b in blocks:
            for s in b:
                if s['state'] == 'short' or s.get('paper_edge'): continue
                cv2.line(crop, P(s['a']), P(s['b']), (0, 160, 0) if s['state'] == 'on print' else (0, 140, 255), 1, cv2.LINE_AA)
        L_exp = 0.0
        for s in h:
            ex = not (s['state'] == 'short' or s.get('paper_edge'))
            if ex: L_exp += float(np.hypot(s['b'][0] - s['a'][0], s['b'][1] - s['a'][1]))
            cv2.line(crop, P(s['a']), P(s['b']), (255, 230, 0) if ex else (140, 140, 140), 3 if ex else 1, cv2.LINE_AA)
        tile = np.full((TILE + 24, TILE, 3), 255, np.uint8); tile[24:24 + crop.shape[0], :crop.shape[1]] = crop
        cv2.putText(tile, f'{N} hole {k}: {L_exp:.0f} px exported  @({int(pts[:, 0].mean())},{int(pts[:, 1].mean())})', (4, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
        tiles.append(tile); rows.append(dict(hole=k, exported_len=round(L_exp), centre=[int(pts[:, 0].mean()), int(pts[:, 1].mean())], bbox=[int(x0), int(y0), int(x1), int(y1)]))
    cols = 4; blank = np.full_like(tiles[0], 255) if tiles else None
    while tiles and len(tiles) % cols: tiles.append(blank)
    if tiles:
        grid = np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)])
        cv2.imwrite(HERE + f'holes_view/{N}_holes.jpg', grid, [cv2.IMWRITE_JPEG_QUALITY, 85])
    json.dump(rows, open(HERE + f'holes_view/{N}_holes.json', 'w'), indent=1)
    print(N, len(holes), 'holes;', round(sum(r['exported_len'] for r in rows)), 'px exported')
