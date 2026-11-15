"""Every street edge of a plate's label, tested against the print (14 November 2026).

    cd data/sanborn
    python ../../tools/sanborn/unet/edges.py N [--crops DIR]

Edges come from two places (make_labels.py): today's parcel sides slid onto the print (unet_data/N_snapped.json) and
the streets marked by eye (unet_data/N_marked_refined.json). An edge is
  green   on a printed line (the scan clearly darker along it than 3 to 6 px either side; for an edge read by eye, also
          when at least 78% of its length is ink),
  blue    declared to have no printed line (a marked edge with kind "paper": the trimmed paper edge, a railway side),
  grey    a parcel side with a marked edge beside it (the marked edge is the one taught), or one in a not_edge box of
          picks22_guided/22-N/edges_review.json (today's street or property line, nothing printed under it),
  orange  NOT TAUGHT: a parcel side or a marked edge with no printed line found under it and no explanation; a band along
          it is blank in the label. These are the edges still to be read,
  red     none of these (no longer produced: an edge that is not verified is never taught, so it is orange).
Green also covers an edge in an ok_box of edges_review.json (seen on the print by eye where the test fails among lettering).
Writes unet_data/N_edges_whole.jpg and unet_data/N_edges.json; prints the red edges grouped into 800 px squares.
With --crops, writes a gridded full-size crop of every square that has red in it (red edges drawn) into DIR.
"""
import collections, json, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import _ws  # noqa: E402
N = sys.argv[1]; SP = _ws.DATA; U = SP + 'unet_data/'; NEAR, SQ = 30.0, 800
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
_hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); _ink = (_hsv[:, :, 2] < 120) | ((_hsv[:, :, 1] < 90) & (_hsv[:, :, 2] < 170))      # black/grey ink only, as make_labels.py ink_image()
g = cv2.GaussianBlur(np.where(_ink, cv2.cvtColor(full, cv2.COLOR_BGR2GRAY), 255).astype(np.uint8), (3, 3), 0).astype(np.float32)
alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
def dark(a, b):
    d = b - a; L = np.hypot(*d); t = np.linspace(.06, .94, max(10, int(L))); q = a + np.outer(t, d)
    x = q[:, 0].round().astype(int); y = q[:, 1].round().astype(int); ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
    return float(g[y[ok], x[ok]].mean()) if ok.sum() > 8 else 255.
def on(a, b):
    d = b - a; n = np.array([-d[1], d[0]]) / np.hypot(*d)
    return bool(np.mean([dark(a + n * o, b + n * o) for o in (-6, -3, 3, 6)]) - dark(a, b) > 25)
def inkshare(a, b):
    d = b - a; L = np.hypot(*d); t = np.linspace(.04, .96, max(10, int(L))); q = a + np.outer(t, d)
    x = q[:, 0].round().astype(int); y = q[:, 1].round().astype(int); ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
    if ok.sum() <= 8: return 0.0
    nrm = np.array([-d[1], d[0]]) / (L or 1); g0 = g[y[ok], x[ok]]; side = []          # as make_labels.py ink(): dark, or darker than the paper 5 px either side
    for o in (-5, 5):
        xs = np.clip((q[ok, 0] + nrm[0] * o).round().astype(int), 0, W - 1); ys = np.clip((q[ok, 1] + nrm[1] * o).round().astype(int), 0, H - 1); side.append(g[ys, xs])
    return float(((g0 < 150) | ((g0 < 185) & (g0 < np.minimum(side[0], side[1]) - 18))).mean())
segs = []
RF = SP + f'picks22_guided/22-{N}/edges_review.json'; REV = json.load(open(RF, encoding='utf8')) if os.path.exists(RF) else {}   # red parcel sides explained by eye
marked = json.load(open(U + f'{N}_marked_refined.json', encoding='utf8')) if os.path.exists(U + f'{N}_marked_refined.json') else []
mk = np.zeros((H // 2, W // 2), np.uint8)                   # where a marked edge runs (for "a marked edge beside it")
strip = np.zeros((H // 2, W // 2), np.uint8)                # inside a marked street
for m in marked:
    cv2.fillPoly(strip, [(np.r_[np.array(m['left']), np.array(m['right'])[::-1]] / 2).round().astype(np.int32)], 1)
    for key in ('left', 'right'):
        kind = m.get(key + '_kind', 'line'); p = np.array(m[key], float)
        cv2.polylines(mk, [(p / 2).round().astype(np.int32)], False, 1, int(NEAR))
        for a, b in zip(p[:-1], p[1:]):
            if np.hypot(*(b - a)) < 28: continue
            mid = (a + b) / 2; okb = any(x0 <= mid[0] <= x1 and y0 <= mid[1] <= y1 for x0, y0, x1, y1 in REV.get('ok_boxes', []))
            segs.append(dict(src='read', name=m['name'], a=a.tolist(), b=b.tolist(), state='orange' if kind == 'unsure' else ('blue' if kind != 'line' else ('green' if on(a, b) or okb or inkshare(a, b) >= 0.78 else 'orange'))))
for q in json.load(open(U + f'{N}_snapped.json', encoding='utf8')):
    q = np.array(q, float)
    for k in range(len(q)):
        a, b = q[k], q[(k + 1) % len(q)]; m = ((a + b) / 2).astype(int)
        if np.hypot(*(b - a)) < 28 or not (0 <= m[0] < W and 0 <= m[1] < H and alpha[m[1], m[0]]): continue
        t = np.linspace(0.1, 0.9, 9); c = (a + np.outer(t, b - a)) / 2; c = c.round().astype(int)
        ok = (c[:, 0] >= 0) & (c[:, 0] < W // 2) & (c[:, 1] >= 0) & (c[:, 1] < H // 2)
        beside = ok.any() and ((mk[c[ok, 1], c[ok, 0]] > 0) | (strip[c[ok, 1], c[ok, 0]] > 0)).mean() >= 0.6
        mid = (a + b) / 2; inb = lambda key: any(x0 <= mid[0] <= x1 and y0 <= mid[1] <= y1 for x0, y0, x1, y1 in REV.get(key, []))
        segs.append(dict(src='parcel', a=a.tolist(), b=b.tolist(), state='green' if on(a, b) or inb('ok_boxes') else ('blue' if inb('paper_boxes') else ('grey' if beside or inb('not_edge_boxes') else 'orange'))))
COL = dict(green=(0, 150, 0), blue=(230, 120, 0), grey=(150, 150, 150), red=(0, 0, 230), orange=(0, 150, 255))
v = (full * 0.8 + 50).astype(np.uint8); I = lambda p: tuple(np.round(p).astype(int))
for s in sorted(segs, key=lambda s: s['state'] in ('red', 'orange')): cv2.line(v, I(s['a']), I(s['b']), COL[s['state']], 5, cv2.LINE_AA)
cv2.imwrite(U + f'{N}_edges_whole.jpg', cv2.resize(v, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
json.dump(segs, open(U + f'{N}_edges.json', 'w', encoding='utf8', newline='\n'))
cnt = collections.Counter((s['src'], s['state']) for s in segs); print(dict(cnt))
sq = collections.defaultdict(list)
for s in segs:
    if s['state'] in ('red', 'orange'): m = (np.array(s['a']) + s['b']) / 2; sq[(int(m[0] // SQ), int(m[1] // SQ))].append(s)
print('edges not taught', sum(len(v_) for v_ in sq.values()), 'in', len(sq), 'squares:', sorted((k, len(v_)) for k, v_ in sq.items()))
if '--crops' in sys.argv:
    D = sys.argv[sys.argv.index('--crops') + 1].rstrip('/') + '/'; os.makedirs(D, exist_ok=True)
    for f in os.listdir(D): os.remove(D + f)
    for (i, j) in sorted(sq):
        x0, y0 = i * SQ - 60, j * SQ - 60; x1, y1 = x0 + SQ + 120, y0 + SQ + 120; sc = 1.5
        c = np.full((y1 - y0, x1 - x0, 3), 255, np.uint8); a, b, e, f = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        c[b - y0:f - y0, a - x0:e - x0] = full[b:f, a:e]; c = cv2.resize(c, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
        P = lambda p: tuple(((np.array(p) - [x0, y0]) * sc).round().astype(int))
        for s in segs:
            if s['state'] in ('red', 'orange', 'green', 'blue'): cv2.line(c, P(s['a']), P(s['b']), COL[s['state']], 1 if s['state'] not in ('red', 'orange') else 2, cv2.LINE_AA)
        for gx in range((x0 // 50 + 1) * 50, x1, 50):
            X = int((gx - x0) * sc); big = gx % 100 == 0; cv2.line(c, (X, 0), (X, c.shape[0]), (255, 0, 255) if big else (255, 190, 255), 1)
            if big: cv2.putText(c, str(gx), (X + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 0, 160), 1); cv2.putText(c, str(gx), (X + 2, c.shape[0] - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 0, 160), 1)
        for gy in range((y0 // 50 + 1) * 50, y1, 50):
            Y = int((gy - y0) * sc); big = gy % 100 == 0; cv2.line(c, (0, Y), (c.shape[1], Y), (255, 0, 255) if big else (255, 190, 255), 1)
            if big: cv2.putText(c, str(gy), (2, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 0, 160), 1); cv2.putText(c, str(gy), (c.shape[1] - 44, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 0, 160), 1)
        cv2.imwrite(D + f'{i:02d}_{j:02d}.jpg', c, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print('crops', len(sq), 'in', D)
