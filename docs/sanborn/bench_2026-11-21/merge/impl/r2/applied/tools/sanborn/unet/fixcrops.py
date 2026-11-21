"""Close-up crops of every unsettled edge, for reading by eye (14 November 2026).

    cd data/sanborn
    python ../../tools/sanborn/unet/edges.py N        (writes unet_data/N_edges.json)
    python ../../tools/sanborn/unet/fixcrops.py N DIR

The unsettled (orange) edges of unet_data/N_edges.json are covered by squares of TILE plate px. Each square that holds
one is written at twice full size with a 50 px grid (labelled every 100) and the edges drawn: orange unsettled, green
on a printed line, blue declared paper or railway side.
"""
import json, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import _ws  # noqa: E402
N, D = sys.argv[1], sys.argv[2].rstrip('/') + '/'; SP = _ws.DATA; TILE, PAD, SC = 600, 75, 2.0
S = json.load(open(SP + f'unet_data/{N}_edges.json', encoding='utf8')); O = [s for s in S if s['state'] == 'orange']
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]; os.makedirs(D, exist_ok=True)
for f in os.listdir(D): os.remove(D + f)
COL = dict(green=(0, 150, 0), blue=(230, 120, 0), orange=(0, 140, 255))
tiles = sorted({(int(((s['a'][0] + s['b'][0]) / 2) // TILE), int(((s['a'][1] + s['b'][1]) / 2) // TILE)) for s in O})
for i, j in tiles:
    x0, y0 = max(0, i * TILE - PAD), max(0, j * TILE - PAD); x1, y1 = min(W, (i + 1) * TILE + PAD), min(H, (j + 1) * TILE + PAD)
    im = cv2.resize(full[y0:y1, x0:x1], None, fx=SC, fy=SC, interpolation=cv2.INTER_CUBIC)
    T = lambda p: tuple(((np.array(p) - [x0, y0]) * SC).round().astype(int))
    for s in S:
        if s['state'] in COL: cv2.line(im, T(s['a']), T(s['b']), COL[s['state']], 2 if s['state'] == 'orange' else 1, cv2.LINE_AA)
    for g in range((x0 // 50 + 1) * 50, x1, 50):
        X = int((g - x0) * SC); big = g % 100 == 0; cv2.line(im, (X, 0), (X, im.shape[0]), (255, 0, 255) if big else (255, 200, 255), 1)
        if big: cv2.putText(im, str(g), (X + 2, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 0, 160), 1); cv2.putText(im, str(g), (X + 2, im.shape[0] - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 0, 160), 1)
    for g in range((y0 // 50 + 1) * 50, y1, 50):
        Y = int((g - y0) * SC); big = g % 100 == 0; cv2.line(im, (0, Y), (im.shape[1], Y), (255, 0, 255) if big else (255, 200, 255), 1)
        if big: cv2.putText(im, str(g), (2, Y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 0, 160), 1); cv2.putText(im, str(g), (im.shape[1] - 50, Y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 0, 160), 1)
    cv2.imwrite(D + f't{i:02d}_{j:02d}.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 88])
print(len(O), 'unsettled edges in', len(tiles), 'crops:', ['t%02d_%02d' % t for t in tiles])
