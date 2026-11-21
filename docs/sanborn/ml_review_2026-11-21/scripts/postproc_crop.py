"""crop.py N x0 y0 x1 y1 [scale] : full-size crop of the scan with outlines.json sides drawn (green on print, orange
other kept, red paper_edge, magenta short pieces), endpoints as dots; and the N_edges.json lines after clean() in cyan."""
import json, sys
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
N = sys.argv[1]; x0, y0, x1, y1 = map(int, sys.argv[2:6]); sc = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); im = full[y0:y1, x0:x1].copy()
o = json.load(open(SP + f'picks22_guided/22-{N}/outlines.json', encoding='utf8'))
P = lambda p: (int(round(p[0] - x0)), int(round(p[1] - y0)))
for p in o:
    for s in p:
        if s['state'] == 'short': col, w = (255, 0, 255), 1
        elif s.get('paper_edge'): col, w = (0, 0, 255), 2
        elif s['state'] == 'on print': col, w = (0, 170, 0), 2
        else: col, w = (0, 140, 255), 2
        cv2.line(im, P(s['a']), P(s['b']), col, w, cv2.LINE_AA)
        if s['state'] != 'short': cv2.circle(im, P(s['a']), 4, (255, 0, 0), -1); cv2.circle(im, P(s['b']), 3, (0, 0, 0), -1)
if len(sys.argv) > 7:
    pa = cv2.imread(U + f'{N}_pred_{sys.argv[7]}.png', 0)
    pa = cv2.resize(pa, (full.shape[1], full.shape[0]), interpolation=cv2.INTER_LINEAR)[y0:y1, x0:x1]
    cs, _ = cv2.findContours((pa > 127).astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE); cv2.drawContours(im, cs, -1, (200, 200, 0), 1)
if len(sys.argv) > 8:
    pl = cv2.imread(U + f'{N}_lines_{sys.argv[8]}.png', 0)[y0:y1, x0:x1]
    im[pl > 127] = (0.5 * im[pl > 127] + 0.5 * np.array([255, 120, 0])).astype(np.uint8)
cv2.imwrite(f'crop_{N}_{x0}_{y0}.jpg', cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 90])
