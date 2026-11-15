"""Is a plate's street label complete: every crossing and every road (14 November 2026).

    cd data/sanborn
    python ../../tools/sanborn/unet/complete.py N

Checked against unet_data/N_label.png (0 street, 1 block, 255 not taught):
- crossings: every crossing both guided readers placed on the plate (picks22_guided/22-N/observations.json). A disc of
  R px round it must be taught street: "complete" if at least 90% of the disc that is on the paper is street,
  "partly" if some of it is blank, "missing" if the middle is block or blank.
- roads: every street the readers traced (merge.json "runs") and every street marked by eye (streets_marked.json).
  Its centre line is walked every 10 px: the share on street / blank / block, and the longest stretch not on street.
- joined up: the pieces the taught street area falls into. A complete label is one piece (plus stubs cut off by the
  paper edge); every extra piece is a road cut off from the rest by a gap.
Writes unet_data/N_complete.json and N_complete.jpg (crossings: green complete, orange partly, red missing; road
stretches not on street: red where block, orange where blank).
"""
import json, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import _ws  # noqa: E402
N = sys.argv[1]; SP = _ws.DATA; U = SP + 'unet_data/'; D = SP + f'picks22_guided/22-{N}/'; K, R = 2, 40
lab = cv2.imread(U + f'{N}_label.png', 0); h, w = lab.shape
alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h)) > 0.5
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); vis = cv2.resize(full, (w, h), interpolation=cv2.INTER_AREA); vis = (vis * 0.7 + 76).astype(np.uint8)
vis[lab == 0] = (vis[lab == 0] * 0.55 + np.array([220, 120, 40]) * 0.45).astype(np.uint8)
yy, xx = np.mgrid[-R // K:R // K + 1, -R // K:R // K + 1]; disc = (xx ** 2 + yy ** 2) <= (R // K) ** 2
def at(x, y):
    x, y = int(round(x / K)), int(round(y / K))
    return lab[y, x] if 0 <= x < w and 0 <= y < h and alpha[y, x] else None
cross = []
for c in json.load(open(D + 'observations.json', encoding='utf8'))['crossings']:
    x, y = int(round(c['x'] / K)), int(round(c['y'] / K)); r = R // K
    if not (r <= x < w - r and r <= y < h - r): continue
    win = lab[y - r:y + r + 1, x - r:x + r + 1][disc]; pap = alpha[y - r:y + r + 1, x - r:x + r + 1][disc]
    if pap.sum() < 20: continue
    st, bl = float((win[pap] == 0).mean()), float((win[pap] == 255).mean()); mid = lab[y, x]
    state = 'complete' if st >= 0.9 else ('missing' if mid != 0 else 'partly')
    cross.append(dict(id=c['id'], a=c['a'], b=c['b'], x=c['x'], y=c['y'], street=round(st, 2), blank=round(bl, 2), state=state))
    cv2.circle(vis, (x, y), 9, dict(complete=(0, 150, 0), partly=(0, 150, 255), missing=(0, 0, 230))[state], 2 if state == 'complete' else -1)
roads = []
lines = [(r_['name'], 'traced', np.array(r_['points'], float)) for r_ in json.load(open(D + 'merge.json', encoding='utf8'))['runs']]
if os.path.exists(D + 'streets_marked.json'):
    for m in json.load(open(D + 'streets_marked.json', encoding='utf8')):
        l, r_ = np.array(m['left'], float), np.array(m['right'], float); n = max(len(l), len(r_))
        f = lambda p: np.c_[np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(p)), p[:, 0]), np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(p)), p[:, 1])]
        lines.append((m['name'], 'marked', (f(l) + f(r_)) / 2))
for name, src, pts in lines:
    v = []; P = []
    for a, b in zip(pts[:-1], pts[1:]):
        for t in np.arange(0, 1, 10 / max(10.0, np.hypot(*(b - a)))):
            q = a + (b - a) * t; s = at(*q)
            if s is not None: v.append(int(s)); P.append(q)
    if len(v) < 5: continue
    v = np.array(v); off = v != 0; worst = cur = 0
    for o in off:
        cur = cur + 1 if o else 0; worst = max(worst, cur)
    roads.append(dict(name=name, source=src, length_px=len(v) * 10, street=round(float((v == 0).mean()), 2), blank=round(float((v == 255).mean()), 2),
                      block=round(float((v == 1).mean()), 2), longest_gap_px=worst * 10))
    for q, s in zip(P, v):
        if s != 0: cv2.circle(vis, (int(q[0] / K), int(q[1] / K)), 3, (0, 0, 230) if s == 1 else (0, 150, 255), -1)
n, cc, st, _ = cv2.connectedComponentsWithStats((lab == 0).astype(np.uint8), connectivity=8)
pieces = sorted([dict(area_px=int(st[i, cv2.CC_STAT_AREA]) * K * K, x=int(st[i, cv2.CC_STAT_LEFT] * K), y=int(st[i, cv2.CC_STAT_TOP] * K),
                      w=int(st[i, cv2.CC_STAT_WIDTH] * K), h=int(st[i, cv2.CC_STAT_HEIGHT] * K)) for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 150], key=lambda p: -p['area_px'])
for p in pieces[1:]: cv2.rectangle(vis, (p['x'] // K, p['y'] // K), ((p['x'] + p['w']) // K, (p['y'] + p['h']) // K), (200, 0, 200), 2)
rep = dict(crossings=dict(total=len(cross), complete=sum(c['state'] == 'complete' for c in cross), partly=sum(c['state'] == 'partly' for c in cross), missing=sum(c['state'] == 'missing' for c in cross)),
           roads=dict(total=len(roads), whole=sum(r_['longest_gap_px'] <= 40 for r_ in roads), with_gap=sum(r_['longest_gap_px'] > 40 for r_ in roads)),
           street_pieces=len(pieces), main_piece_share=round(pieces[0]['area_px'] / sum(p['area_px'] for p in pieces), 3) if pieces else 0,
           crossings_not_complete=[c for c in cross if c['state'] != 'complete'], roads_with_gap=sorted([r_ for r_ in roads if r_['longest_gap_px'] > 40], key=lambda r_: -r_['longest_gap_px']), other_pieces=pieces[1:])
json.dump(rep, open(U + f'{N}_complete.json', 'w', encoding='utf8', newline='\n'), indent=1)
cv2.imwrite(U + f'{N}_complete.jpg', vis, [cv2.IMWRITE_JPEG_QUALITY, 85])
print({k: rep[k] for k in ('crossings', 'roads', 'street_pieces', 'main_piece_share')})
for c in rep['crossings_not_complete']: print(' ', c['state'].ljust(8), c['a'], 'x', c['b'], (int(c['x']), int(c['y'])), 'street', c['street'], 'blank', c['blank'])
for r_ in rep['roads_with_gap']: print('  road', r_['name'][:40].ljust(40), r_['source'], 'on street', r_['street'], 'blank', r_['blank'], 'block', r_['block'], 'longest gap px', r_['longest_gap_px'])
for p in rep['other_pieces']: print('  piece', p)
