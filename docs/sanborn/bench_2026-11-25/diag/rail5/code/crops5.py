"""Full-size crops of the rule railroad tracks Ben saw on plate 5 (unet_data/5_rail_rule.json, copied to inputs/), grouped
by place, plus a small overview (25 Nov 2026, diag/rail5). Writes only into diag/rail5/crops.
    cd data/sanborn; python -B bench_2026-11-25/diag/rail5/code/crops5.py"""
import json, os, sys
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = os.path.join(ROOT, 'crops')
im = cv2.imread('cufp/22-5.jpg'); H, W = im.shape[:2]
rule = json.load(open(os.path.join(ROOT, 'inputs', '5_rail_rule.json'), encoding='utf8'))['tracks']
ben = json.load(open(os.path.join(ROOT, 'inputs', 'rail_ben_5_copy.json'), encoding='utf8'))['tracks']
prop = json.load(open(os.path.join(ROOT, 'runs', 'proposed_nets_tracks.json'), encoding='utf8'))['tracks']
bins = cv2.imread(os.path.join(ROOT, 'runs', 'orig_nets_bins.png'), 0)
rr = [np.array(t['pts'], float) for t in rule if t['kind'] == 'railroad']
prr = [np.array(t['pts'], float) for t in prop if t['kind'] == 'railroad']
# group tracks lying within 150 px of each other
from scipy.spatial import cKDTree
S = [np.vstack([a + np.linspace(0, 1, max(2, int(np.hypot(*(b - a)) / 5) + 1))[:, None] * (b - a) for a, b in zip(p[:-1], p[1:])]) for p in rr]
up = list(range(len(rr)))
def root(i):
    while up[i] != i: i = up[i]
    return i
for i in range(len(rr)):
    for j in range(i + 1, len(rr)):
        if cKDTree(S[i]).query(S[j])[0].min() < 150: up[root(j)] = root(i)
groups = {}
for i in range(len(rr)): groups.setdefault(root(i), []).append(i)
G = sorted(groups.values(), key=lambda g: min(rr[i][:, 1].min() for i in g))
rec = []
for gi, g in enumerate(G):
    P = np.vstack([rr[i] for i in g]); x0, y0 = (P.min(0) - 140).astype(int); x1, y1 = (P.max(0) + 140).astype(int)
    x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(W, x1), min(H, y1)
    raw = im[y0:y1, x0:x1].copy(); ov = raw.copy(); lay = raw.copy()
    m = (bins[y0:y1, x0:x1] == 4); lay[m] = (0, 0, 230)                    # railroad bin ink in red
    for i in g: cv2.polylines(lay, [np.round(rr[i] - [x0, y0]).astype(np.int32)], False, (255, 120, 0), 2)   # rule track centre line, blue
    for p in prr:
        if p[:, 0].max() >= x0 and p[:, 0].min() <= x1 and p[:, 1].max() >= y0 and p[:, 1].min() <= y1:
            cv2.polylines(lay, [np.round(p - [x0, y0]).astype(np.int32)], False, (0, 200, 0), 1)   # still there after the proposed fix: green
    for t in ben:
        p = np.array(t['pts'], float)
        if p[:, 0].max() >= x0 and p[:, 0].min() <= x1 and p[:, 1].max() >= y0 and p[:, 1].min() <= y1:
            cv2.polylines(lay, [np.round(p - [x0, y0]).astype(np.int32)], False, (0, 220, 255), 1)   # Ben's streetcar: yellow
    ov = cv2.addWeighted(raw, 0.45, lay, 0.55, 0)
    pic = np.vstack([raw, np.full((6, raw.shape[1], 3), 255, np.uint8), ov]) if raw.shape[1] > raw.shape[0] * 1.2 else np.hstack([raw, np.full((raw.shape[0], 6, 3), 255, np.uint8), ov])
    f = os.path.join(OUT, f'rr_group{gi:02d}_{x0}_{y0}.png'); cv2.imwrite(f, pic)
    rec.append(dict(group=gi, tracks=g, len=[round(float(np.hypot(*np.diff(rr[i], axis=0).T).sum())) for i in g], box=[int(x0), int(y0), int(x1), int(y1)], kept_by_proposed=any(cKDTree(np.vstack(prr)).query(rr[i])[0].max() < 3 for i in g) if prr else False, file=os.path.basename(f)))
    print(rec[-1])
json.dump(rec, open(os.path.join(OUT, 'groups.json'), 'w'), indent=1)
# overview at 1/8 with the groups numbered
c = cv2.resize(im, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
for t in ben: cv2.polylines(c, [np.round(np.array(t['pts']) / 8).astype(np.int32)], False, (0, 200, 255), 2)
for r in rec:
    x0, y0, x1, y1 = (np.array(r['box']) / 8).astype(int); cv2.rectangle(c, (x0, y0), (x1, y1), (0, 0, 255), 2); cv2.putText(c, str(r['group']), (x0, max(12, y0 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
cv2.imwrite(os.path.join(OUT, 'overview_5.jpg'), c, [cv2.IMWRITE_JPEG_QUALITY, 90])
