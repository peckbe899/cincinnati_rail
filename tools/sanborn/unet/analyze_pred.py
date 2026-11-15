"""Check a U-net result the way the hand-built label was checked (14 November 2026).

    cd data/sanborn
    python ../../tools/sanborn/unet/analyze_pred.py N NAME

Reads unet_data/N_pred_NAME.png (P(block)) and picks22_guided/22-N/unet_blocks.json (extract.py's straight-sided block
outlines) and reports, in unet_data/N_analysis_NAME.json and N_analysis_NAME.jpg:
- edges: every side of the extracted blocks at least 28 px long, tested against the print's black/grey ink exactly as
  edges.py tests the label: on a printed line (green) or not (red); the share by length;
- crossings: every crossing both readers placed; the predicted street must cover the ground round it (complete / partly
  / missing), as complete.py;
- roads: every traced or marked street walked along its centre line; share on predicted street and the longest gap;
- joined up: the pieces the predicted street area falls into;
- against the label, where the label is taught: street found, street missed, block called street.
"""
import json, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import _ws  # noqa: E402
N, NAME = sys.argv[1], sys.argv[2]; SP = _ws.DATA; U = SP + 'unet_data/'; D = SP + f'picks22_guided/22-{N}/'; K, R = 2, 40
p = cv2.imread(U + f'{N}_pred_{NAME}.png', 0); h, w = p.shape
alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h)) > 0.5
st = (p <= 127) & alpha                                            # predicted street
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170))
g = cv2.GaussianBlur(np.where(ink, cv2.cvtColor(full, cv2.COLOR_BGR2GRAY), 255).astype(np.uint8), (3, 3), 0).astype(np.float32)
def dark(a, b):
    d = b - a; L = np.hypot(*d); t = np.linspace(.06, .94, max(10, int(L))); q = a + np.outer(t, d)
    x = q[:, 0].round().astype(int); y = q[:, 1].round().astype(int); ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
    return float(g[y[ok], x[ok]].mean()) if ok.sum() > 8 else 255.
def on(a, b):
    d = b - a; n = np.array([-d[1], d[0]]) / np.hypot(*d)
    return bool(max(np.mean([dark(a + n * (s + o), b + n * (s + o)) for o in (-6, -3, 3, 6)]) - dark(a + n * s, b + n * s) for s in (-2, -1, 0, 1, 2)) > 25)
vis = (cv2.resize(full, (w, h), interpolation=cv2.INTER_AREA) * 0.7 + 76).astype(np.uint8)
vis[st] = (vis[st] * 0.6 + np.array([220, 120, 40]) * 0.4).astype(np.uint8)
rep = dict(plate=N, model=NAME)
bf = D + 'unet_blocks.json'; Lg = Lr = 0.0; ng = nr = 0
if os.path.exists(bf):
    for poly in json.load(open(bf, encoding='utf8')):
        q = np.array(poly, float)
        for k in range(len(q)):
            a, b = q[k], q[(k + 1) % len(q)]; L = np.hypot(*(b - a)); m = ((a + b) / 2 / K).astype(int)
            if L < 28 or not (0 <= m[0] < w and 0 <= m[1] < h and alpha[m[1], m[0]]): continue
            ok = on(a, b); Lg += L * ok; Lr += L * (not ok); ng += ok; nr += not ok
            cv2.line(vis, tuple((a / K).astype(int)), tuple((b / K).astype(int)), (0, 150, 0) if ok else (0, 0, 230), 2, cv2.LINE_AA)
    rep['edges'] = dict(on_printed_line=int(ng), not_on_a_line=int(nr), share_on_line_by_length=round(Lg / max(1.0, Lg + Lr), 3))
yy, xx = np.mgrid[-R // K:R // K + 1, -R // K:R // K + 1]; disc = (xx ** 2 + yy ** 2) <= (R // K) ** 2; cross = []
if os.path.exists(D + 'observations.json'):
    for c in json.load(open(D + 'observations.json', encoding='utf8'))['crossings']:
        x, y = int(round(c['x'] / K)), int(round(c['y'] / K)); r = R // K
        if not (r <= x < w - r and r <= y < h - r): continue
        win = st[y - r:y + r + 1, x - r:x + r + 1][disc]; pap = alpha[y - r:y + r + 1, x - r:x + r + 1][disc]
        if pap.sum() < 20: continue
        s = float(win[pap].mean()); state = 'complete' if s >= 0.9 else ('missing' if not st[y, x] else 'partly')
        cross.append(dict(a=c['a'], b=c['b'], x=c['x'], y=c['y'], street=round(s, 2), state=state))
        cv2.circle(vis, (x, y), 9, dict(complete=(0, 150, 0), partly=(0, 150, 255), missing=(0, 0, 230))[state], 2 if state == 'complete' else -1)
    rep['crossings'] = dict(total=len(cross), complete=sum(c['state'] == 'complete' for c in cross), partly=sum(c['state'] == 'partly' for c in cross), missing=sum(c['state'] == 'missing' for c in cross),
                            not_complete=[c for c in cross if c['state'] != 'complete'])
lines = []
if os.path.exists(D + 'merge.json'): lines += [(r_['name'], np.array(r_['points'], float)) for r_ in json.load(open(D + 'merge.json', encoding='utf8'))['runs']]
if os.path.exists(D + 'streets_marked.json'):
    for m in json.load(open(D + 'streets_marked.json', encoding='utf8')):
        l, r_ = np.array(m['left'], float), np.array(m['right'], float); n = max(len(l), len(r_))
        f = lambda q: np.c_[np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(q)), q[:, 0]), np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(q)), q[:, 1])]
        lines.append((m['name'], (f(l) + f(r_)) / 2))
roads = []
for name, pts in lines:
    v = []
    for a, b in zip(pts[:-1], pts[1:]):
        for t in np.arange(0, 1, 10 / max(10.0, np.hypot(*(b - a)))):
            q = a + (b - a) * t; x, y = int(round(q[0] / K)), int(round(q[1] / K))
            if 0 <= x < w and 0 <= y < h and alpha[y, x]: v.append(bool(st[y, x]))
    if len(v) < 5: continue
    worst = cur = 0
    for o in v:
        cur = 0 if o else cur + 1; worst = max(worst, cur)
    roads.append(dict(name=name, on_street=round(float(np.mean(v)), 2), longest_gap_px=worst * 10))
rep['roads'] = dict(total=len(roads), whole=sum(r_['longest_gap_px'] <= 40 for r_ in roads), with_gap=sorted([r_ for r_ in roads if r_['longest_gap_px'] > 40], key=lambda r_: -r_['longest_gap_px']))
n, cc, stt, _ = cv2.connectedComponentsWithStats(st.astype(np.uint8), connectivity=8)
ar = sorted([int(stt[i, cv2.CC_STAT_AREA]) for i in range(1, n) if stt[i, cv2.CC_STAT_AREA] > 150], reverse=True)
rep['street_pieces'] = len(ar); rep['main_piece_share'] = round(ar[0] / sum(ar), 3) if ar else 0
lf = U + f'{N}_label.png'
if os.path.exists(lf):
    lab = cv2.imread(lf, 0); t = (lab != 255) & alpha; ls = lab == 0
    rep['against_label'] = dict(street_found=round(float((st & ls & t).sum() / max(1, (ls & t).sum())), 3), street_missed=round(float((~st & ls & t).sum() / max(1, (ls & t).sum())), 3),
                                block_called_street=round(float((st & ~ls & t).sum() / max(1, (~ls & t).sum())), 3),
                                iou_street=round(float((st & ls & t).sum() / max(1, ((st | ls) & t).sum())), 3))
json.dump(rep, open(U + f'{N}_analysis_{NAME}.json', 'w', encoding='utf8', newline='\n'), indent=1)
cv2.imwrite(U + f'{N}_analysis_{NAME}.jpg', vis, [cv2.IMWRITE_JPEG_QUALITY, 85])
print(json.dumps({k: (v if k not in ('crossings', 'roads') else {kk: (vv if not isinstance(vv, list) else len(vv)) for kk, vv in v.items()}) for k, v in rep.items()}, indent=1))
