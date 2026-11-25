"""Does today's rule put free-standing characters in bins other than 8?
Takes every 8-connected piece of ALL ink on plate 44 (unet_data/44_bins.png > 0) that is character-sized
(16-48 px tall, 4 px to height+4 px wide, at least 30 px of ink) and finds the bin most of its pixels got.
Counts pieces per majority bin, and draws a random 60 of the pieces whose majority bin is NOT 8
(seed 3) into pics/missed_44.png for reading by eye. Writes out/missed_text_44.json.
Usage: python -B missed_text.py"""
import os, json, cv2, numpy as np
R = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D'
B = os.path.join(R, 'data/sanborn/bench_2026-11-25/text/research')
code = cv2.imread(os.path.join(R, 'data/sanborn/unet_data/44_bins.png'), cv2.IMREAD_UNCHANGED)
scan = cv2.imread(os.path.join(R, 'data/sanborn/cufp/22-44.jpg'))
ink = (code > 0).astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
x, y, w, h, a = st[1:].T
ok = (h >= 16) & (h <= 48) & (w >= 4) & (w <= h + 4) & (a >= 30)
idx = np.where(ok)[0] + 1
# majority bin per piece
flat_l = lab.ravel(); flat_c = code.ravel()
sel = np.isin(flat_l, idx)
L, C = flat_l[sel], flat_c[sel]
cnt = np.zeros((n, 10), np.int64)
np.add.at(cnt, (L, C), 1)
maj = cnt[idx].argmax(1)
by = {int(b): int((maj == b).sum()) for b in range(10)}
print('char-sized ink pieces', len(idx), 'by majority bin', by)
others = idx[maj != 8]
pick = np.random.default_rng(3).choice(others, 60, replace=False)
cell = 120
sheet = np.full((6 * (cell + 18), 10 * cell, 3), 255, np.uint8)
info = []
for j, p in enumerate(pick):
    X, Y, W, H = st[p, :4]
    c = scan[max(0, Y - 6):Y + H + 6, max(0, X - 6):X + W + 6].copy()
    cv2.rectangle(c, (5, 5), (6 + W, 6 + H), (0, 0, 255), 1)
    sc = min((cell - 6) / c.shape[0], (cell - 6) / c.shape[1], 2.0)
    c = cv2.resize(c, (int(c.shape[1] * sc), int(c.shape[0] * sc)), interpolation=cv2.INTER_CUBIC)
    r, q = divmod(j, 10)
    cv2.putText(sheet, f'{j} b{cnt[p].argmax()}', (q * cell + 2, r * (cell + 18) + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 0, 0), 1)
    sheet[r * (cell + 18) + 16:r * (cell + 18) + 16 + c.shape[0], q * cell + 2:q * cell + 2 + c.shape[1]] = c
    info.append({'i': j, 'box': [int(X), int(Y), int(W), int(H)], 'bin': int(cnt[p].argmax())})
cv2.imwrite(os.path.join(B, 'pics/missed_44.png'), sheet)
json.dump({'char_sized_pieces': int(len(idx)), 'by_majority_bin': by, 'sample_not_bin8': info},
          open(os.path.join(B, 'out/missed_text_44.json'), 'w'), indent=0)
