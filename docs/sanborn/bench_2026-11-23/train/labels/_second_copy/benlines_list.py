# Ben's lines with the share of their length the pseudo line target teaches negative (longest first)
import sys, json, cv2, numpy as np
N, pdir, mdir = sys.argv[1:4]
pt = cv2.imread(f'{pdir}/{N}/lines.png', 0); pl = cv2.imread(f'unet_data/{N}_lines_lines_ng1.png', 0); sm = json.load(open(f'{mdir}/{N}/streetmap.json', encoding='utf8')); W, H = sm['size']
plm = cv2.dilate(pl, np.ones((7, 7), np.uint8)); rows = []
for l in sm['lines']:
    if l['kind'] not in ('printed', 'drawn'): continue
    a, b = np.array(l['a'], float), np.array(l['b'], float); n = max(2, int(np.hypot(*(b - a))) + 1); q = a + np.outer(np.linspace(0, 1, n), b - a)
    x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1); v = pt[y, x]
    rows.append((int((v == 0).sum()), n, l['kind'], [round(c) for c in l['a']], [round(c) for c in l['b']], round(float((plm[y, x] > 25).mean()), 2)))
rows.sort(key=lambda r: -r[0]); tot = sum(r[0] for r in rows)
print('total negative px', tot)
for r in rows[:25]: print(r)
