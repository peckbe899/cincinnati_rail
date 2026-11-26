"""finder2 CHECK (25 Nov 2026): text near Ben's tracks that finder2 calls text and finder v1 did not, as a contact sheet to
look at by eye (a rail tick or a streetcar dash must never be text). Bands: 14 px round his railroad tracks, 12 px round
his streetcar tracks (picks22_guided/22-N/rail_ben.json, read only). Never an input to the finder.
    cd data/sanborn; python -B <this> N NEW_PATTERN NEWCODES OLD_PATTERN OLDCODES OUT.jpg"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
N, newp, newc, oldp, oldc, out = sys.argv[1:7]
new = cv2.imread(newp.replace('{plate}', N), 0); old = cv2.imread(oldp.replace('{plate}', N), 0); H, W = new.shape
tn = np.isin(new, [int(v) for v in newc.split(',')]); to = np.isin(old, [int(v) for v in oldc.split(',')])
B = json.load(open(f'picks22_guided/22-{N}/rail_ben.json', encoding='utf8')); band = np.zeros((H, W), bool); ml = np.zeros((H, W), np.uint8)
for kind, tol in (('railroad', 14), ('streetcar', 12)):
    m = np.zeros((H, W), np.uint8)
    for t in B['tracks']:
        if t['kind'] == kind and len(t['pts']) > 1: cv2.polylines(m, [np.round(np.array(t['pts'])).astype(np.int32)], False, 1, 1)
    ml |= m; band |= cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * tol + 1, 2 * tol + 1))) > 0
d = (tn & ~to & band).astype(np.uint8); g = (to & ~tn & band).astype(np.uint8)
n, lb, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(d, np.ones((9, 9), np.uint8)), connectivity=8)
cnt = np.bincount(lb[d > 0], minlength=n); order = np.argsort(-cnt); order = order[cnt[order] > 0]
im = cv2.imread(f'cufp/22-{N}.jpg'); tiles = []
for i in order[:48]:
    cx, cy = st[i, 0] + st[i, 2] // 2, st[i, 1] + st[i, 3] // 2; s = max(50, st[i, 2] // 2 + 15, st[i, 3] // 2 + 15)
    X0, Y0, X1, Y1 = max(0, cx - s), max(0, cy - s), min(W, cx + s), min(H, cy + s)
    a = im[Y0:Y1, X0:X1]; o = (a * 0.35 + 255 * 0.65).astype(np.uint8); c = new[Y0:Y1, X0:X1]
    o[c == 1] = (150, 150, 150); o[tn[Y0:Y1, X0:X1]] = (220, 0, 220); o[c == 4] = (0, 200, 230); o[ml[Y0:Y1, X0:X1] > 0] = (255, 160, 0); o[d[Y0:Y1, X0:X1] > 0] = (0, 0, 255)
    t_ = cv2.resize(np.concatenate([a, o], 1), (360, 180)); cv2.putText(t_, f'{cx},{cy} +{cnt[i]}', (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1); tiles.append(t_)
cols = 4; rows = max(1, (len(tiles) + cols - 1) // cols); sheet = np.full((rows * 182, cols * 362, 3), 255, np.uint8)
for i, t_ in enumerate(tiles): r, c = divmod(i, cols); sheet[r * 182:r * 182 + 180, c * 362:c * 362 + 360] = t_
cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
print(N, 'text in band new (not in v1):', int(d.sum()), 'px in', len(order), 'blobs; text in band dropped (in v1, not new):', int(g.sum()), 'px')
