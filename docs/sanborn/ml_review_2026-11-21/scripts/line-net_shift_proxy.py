"""Read-only proxies: (1) how unsure area_ng1 is on the training plates, on 44, and on unplaced plates (no labels there),
(2) where Ben's 'drawn' street sides of 44 sit in the label, and how far the target's positives are from Ben's lines."""
import json, glob, os, time
import numpy as np, cv2
R = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; D = R + 'unet_data/'
out = {}
files = sorted(glob.glob(D + '*_pred_area_ng1.png'), key=os.path.getmtime)
now = time.time()
for f in files:
    if now - os.path.getmtime(f) < 120: continue                    # skip a file the batch may still be writing
    n = os.path.basename(f).split('_pred_')[0]
    p = cv2.imread(f, 0)
    if p is None: continue
    a = np.load(R + f'cufp/{n}/png_alpha_s4.npy').astype(np.float32); a = cv2.resize(a, (p.shape[1], p.shape[0])) > 0.5
    pf = p[a].astype(np.float32) / 255
    q = cv2.imread(D + f'{n}_lines_lines_ng1.png', 0)
    out[n] = dict(unsure_0p1_0p9=round(float(((pf > 0.1) & (pf < 0.9)).mean()), 4), block_share=round(float((pf > 0.5).mean()), 3),
                  line_drawn_share_of_paper=None if q is None else round(float((q[cv2.resize(a.astype(np.uint8), (q.shape[1], q.shape[0])) > 0] > 127).mean()), 4))
for k in ('82A', '80', '43', '45', '44'): print(k, out.get(k))
others = {k: v for k, v in out.items() if k not in ('82A', '80', '43', '45', '44')}
u = [v['unsure_0p1_0p9'] for v in others.values()]; l = [v['line_drawn_share_of_paper'] for v in others.values() if v['line_drawn_share_of_paper'] is not None]
print('unplaced plates', len(others), 'unsure median', np.median(u), 'min', min(u), 'max', max(u), '| line drawn share median', np.median(l) if l else None)
out['_unplaced_summary'] = dict(n=len(others), unsure_median=float(np.median(u)), unsure_min=float(min(u)), unsure_max=float(max(u)), line_share_median=float(np.median(l)) if l else None)
# (2) plate 44
full_shape = (7219, 10768); H, W = full_shape
lab = cv2.resize(cv2.imread(D + '44_label.png', 0), (W, H), interpolation=cv2.INTER_NEAREST)
sm = json.load(open(R + 'streetmap/22-44.json', encoding='utf8'))
dr = np.zeros((H, W), np.uint8); allb = np.zeros((H, W), np.uint8)
for l_ in sm['lines']:
    a_, b_ = tuple(np.round(l_['a']).astype(int)), tuple(np.round(l_['b']).astype(int))
    cv2.line(allb, a_, b_, 1, 1)
    if l_['kind'] == 'drawn': cv2.line(dr, a_, b_, 1, 3)
# label on each side: sample the label 10 px either side of Ben's drawn lines
both_block = 0; tot = 0
for l_ in sm['lines']:
    if l_['kind'] != 'drawn': continue
    a_, b_ = np.array(l_['a'], float), np.array(l_['b'], float); d = b_ - a_; L = np.hypot(*d); nrm = np.array([-d[1], d[0]]) / L
    for s in np.linspace(0.1, 0.9, 9):
        c = a_ + d * s; p1 = (c + nrm * 12).round().astype(int); p2 = (c - nrm * 12).round().astype(int)
        if not (0 <= p1[0] < W and 0 <= p1[1] < H and 0 <= p2[0] < W and 0 <= p2[1] < H): continue
        tot += 1; both_block += (lab[p1[1], p1[0]] == 1) and (lab[p2[1], p2[0]] == 1)
m = dr > 0
out['44_ben_drawn'] = dict(px=int(m.sum()), on_label_block=round(float((lab[m] == 1).mean()), 4), on_label_street=round(float((lab[m] == 0).mean()), 4), on_label_ignore=round(float((lab[m] == 255).mean()), 4),
                           samples=tot, label_block_both_sides_12px=round(both_block / max(1, tot), 4))
print(json.dumps(out['44_ben_drawn']))
line = np.zeros((H, W), np.uint8)
for a_, b_ in json.load(open(D + '44_verified.json', encoding='utf8')):
    cv2.line(line, tuple(np.round(a_).astype(int)), tuple(np.round(b_).astype(int)), 1, 3)
dist = cv2.distanceTransform((allb == 0).astype(np.uint8), cv2.DIST_L2, 3)
dv = dist[line > 0]
out['44_target_pos_dist_to_ben_any'] = {f'within_{k}px': round(float((dv <= k).mean()), 4) for k in (3, 5, 8, 12, 20, 40)}
print(json.dumps(out['44_target_pos_dist_to_ben_any']))
json.dump(out, open('C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/line-net/shift_proxy.json', 'w'), indent=1)
