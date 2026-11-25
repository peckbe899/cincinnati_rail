"""verify: contact sheet of read_truth44 results (random 32 words, seed 5): crop of the truth box, truth reading (black) and
the shapes reader's raw reading (red). For checking the harness by eye. Writes verify/pics/read_truth44_sheet.jpg"""
import json, os, random
import numpy as np, cv2
T = os.path.join(os.getcwd(), 'bench_2026-11-25', 'text'); V = os.path.join(T, 'verify')
d = json.load(open(os.path.join(V, 'out', 'read_truth44_knn_ctx_model_no44.json')))
crops = {}
for tid in ('T1', 'T2', 'T3'):
    for w in json.load(open(os.path.join(T, 'inventory', 'truth', f'{tid}_words.json'), encoding='utf8'))['words']: crops[(tid, w['reading'], tuple(map(tuple, w['poly'])) if w.get('poly') else None)] = w
polys = {}
for (tid, rd, p), w in crops.items(): polys.setdefault((tid, rd), []).append(w)
im = cv2.imread('cufp/22-44.jpg'); random.seed(5); S = random.sample(d['words'], 32); tiles = []
for s in S:
    w = polys[(s['tid'], s['reading'])][0]; P = np.array(w['poly'], float); x0, y0 = (P.min(0) - 25).astype(int); x1, y1 = (P.max(0) + 25).astype(int)
    c = im[max(0, y0):y1, max(0, x0):x1].copy(); cv2.polylines(c, [np.round(P - [max(0, x0), max(0, y0)]).astype(np.int32)], True, (255, 0, 0), 1)
    f = min(220 / c.shape[1], 120 / c.shape[0], 2.0); c = cv2.resize(c, None, fx=f, fy=f)
    t = np.full((170, 230, 3), 255, np.uint8); t[:c.shape[0], :c.shape[1]] = c
    cv2.putText(t, s['reading'].encode('ascii', 'replace').decode(), (3, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(t, s['read_raw'][:22], (3, 164), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1); tiles.append(t)
rows = [np.hstack(tiles[k:k + 8]) for k in range(0, 32, 8)]
cv2.imwrite(os.path.join(V, 'pics', 'read_truth44_sheet.jpg'), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])
