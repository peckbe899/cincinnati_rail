"""merge/impl: the batch lines along the map edge that outline-nesting lost and the merged step does not have either,
drawn for a look (red), with the merged step's lines (green) and the map edge (white). -> pdf_edge/N_lost.jpg and crops"""
import json, sys
import numpy as np, cv2
import common as C
sys.argv += []
import importlib.util
spec = importlib.util.spec_from_file_location('pe', C.IMPL + 'scripts/pdf_edge.py')
src = open(C.IMPL + 'scripts/pdf_edge.py', encoding='utf8').read().split('res = {}; T = {}')[0]
g = {}; exec(compile(src, 'pdf_edge_head', 'exec'), g)
for n in sys.argv[1:]:
    polys = json.load(open(C.IMPL + f'plates/{n}/outlines.json', encoding='utf8')); M = g['BN'].step4(polys)
    Nn = g['step4_old'](json.load(open(g['NEST'] + f'{n}/outlines.json', encoding='utf8'))); Bt = json.load(open(C.U + f'{n}_edges.json', encoding='utf8'))
    m8 = cv2.imread(C.IMPL + f'plates/{n}/{n}_mapground.png', 0) > 127; inner = cv2.erode(m8.astype(np.uint8), np.ones((11, 11), np.uint8)) > 0
    a = g['found_in'](Bt, Nn) >= 0.5; b = g['found_in'](Bt, M) >= 0.5
    im = cv2.imread(C.DATA + f'cufp/22-{n}.jpg'); v = im.copy()
    cs = cv2.findContours(cv2.resize(m8.astype(np.uint8), (im.shape[1], im.shape[0]), interpolation=cv2.INTER_NEAREST), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)[0]; cv2.drawContours(v, cs, -1, (255, 255, 255), 6)
    for e in M: cv2.line(v, tuple(np.round(e['a']).astype(int)), tuple(np.round(e['b']).astype(int)), (0, 150, 0) if e['state'] == 'green' else (0, 140, 255), 5, cv2.LINE_AA)
    lost = []
    for e, x, y in zip(Bt, a, b):
        m = ((np.array(e['a']) + np.array(e['b'])) / 2 / 8).astype(int); yy, xx = min(m8.shape[0] - 1, max(0, m[1])), min(m8.shape[1] - 1, max(0, m[0]))
        if not x and not y and m8[yy, xx] and not inner[yy, xx]: lost.append(e); cv2.line(v, tuple(np.round(e['a']).astype(int)), tuple(np.round(e['b']).astype(int)), (0, 0, 230), 7, cv2.LINE_AA)
    cv2.imwrite(C.IMPL + f'pdf_edge/{n}_lost.jpg', cv2.resize(v, None, fx=0.2, fy=0.2, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
    for k, e in enumerate(sorted(lost, key=lambda e: -np.hypot(*(np.array(e['b']) - np.array(e['a']))))[:2]):
        c = ((np.array(e['a']) + np.array(e['b'])) / 2).astype(int); x0, y0 = max(0, c[0] - 700), max(0, c[1] - 450)
        cv2.imwrite(C.IMPL + f'pdf_edge/{n}_lost_crop{k}.jpg', v[y0:y0 + 900, x0:x0 + 1400], [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(n, 'lost and not back', len(lost), round(sum(np.hypot(*(np.array(e['b']) - np.array(e['a']))) for e in lost)))
