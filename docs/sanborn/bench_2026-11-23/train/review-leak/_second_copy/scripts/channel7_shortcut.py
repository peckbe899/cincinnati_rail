"""review-leak: how much of the line net's target can be read straight off its 7th input? On the pseudo plates the line
target comes from the merged outline step, which itself used area_ng1's map: the same map that is the 7th input. Rule
tested, per plate: "a line wherever area_in (resized to full size as edgenet.pack does) crosses 0.5, within TOL px".
Its precision and recall against lines.png (scored pixels only, as edgenet.score counts them). If the rule is much
better on the pseudo plates than on the labelled plates and 1A, the 7th channel carries the label there (a shortcut
that 44 will not offer). Reads only.
cd data/sanborn; python -B bench_2026-11-23/train/review-leak/scripts/channel7_shortcut.py"""
import json
import numpy as np, cv2
OUT = 'bench_2026-11-23/train/review-leak/'; D = 'train_v2/'; TOL = 3
man = json.load(open(D + 'manifest.json', encoding='utf8'))['plates']; res = {}
k = np.ones((2 * TOL + 1, 2 * TOL + 1), np.uint8)
for N, e in man.items():
    t = cv2.imread(D + N + '/lines.png', 0); H, W = t.shape
    a = cv2.resize(cv2.imread(D + N + '/area_in.png', 0), (W, H), interpolation=cv2.INTER_LINEAR)
    b = cv2.morphologyEx((a > 127).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0; del a
    v = None
    if N == '1A':
        v = cv2.resize(cv2.imread(D + '1A/valmask.png', 0), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    out = {}
    for part, sel in (('train', None if v is None else ~v), ('val', v)):
        if part == 'val' and v is None: continue
        line = t == 1; scored = t != 255; pr = b.copy()
        if sel is not None: line &= sel; scored &= sel; pr &= sel
        near_line = cv2.dilate(line.astype(np.uint8), k) > 0; near_pr = cv2.dilate(pr.astype(np.uint8), k) > 0
        drawn = pr & (scored | near_line)
        P = float((drawn & near_line).sum() / max(1, drawn.sum())); R = float((line & near_pr).sum() / max(1, line.sum()))
        out[part] = dict(precision=round(P, 4), recall=round(R, 4), f1=round(2 * P * R / max(1e-9, P + R), 4), line_px=int(line.sum()))
    res[N] = dict(source=e['source'], **out); print(N, e['source'], json.dumps(out), flush=True)
agg = {}
for s in ('label', 'map', 'pseudo'):
    f = [r['train']['f1'] for r in res.values() if r['source'] == s]; rr = [r['train']['recall'] for r in res.values() if r['source'] == s]; pp = [r['train']['precision'] for r in res.values() if r['source'] == s]
    agg[s] = dict(plates=len(f), f1_mean=round(float(np.mean(f)), 4), recall_mean=round(float(np.mean(rr)), 4), precision_mean=round(float(np.mean(pp)), 4))
res['_by_source'] = agg; print(json.dumps(agg, indent=1))
json.dump(res, open(OUT + 'channel7_shortcut.json', 'w'), indent=1)
