"""Read-only: would line-2's fix (b) (unscore ink in label-block ground on long straight runs >10 px from a verified edge)
catch Ben's drawn street sides, and how much lot-line ink (ink_bins 'lot line' bin) would it unscore too? Plate 44."""
import json, numpy as np, cv2
R = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; D = R + 'unet_data/'
S = 'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/verify-line-net/'
full = cv2.imread(R + 'cufp/22-44.jpg'); H, W = full.shape[:2]
hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170)); del hsv, full
lab = cv2.resize(cv2.imread(D + '44_label.png', 0), (W, H), interpolation=cv2.INTER_NEAREST)
line = np.zeros((H, W), np.uint8)
for a_, b_ in json.load(open(D + '44_verified.json', encoding='utf8')): cv2.line(line, tuple(np.round(a_).astype(int)), tuple(np.round(b_).astype(int)), 1, 3)
far = cv2.distanceTransform((line == 0).astype(np.uint8), cv2.DIST_L2, 5) > 10
cand = (ink & (lab == 1) & far).astype(np.uint8) * 255
segs = cv2.HoughLinesP(cand, 1, np.pi / 360, threshold=120, minLineLength=150, maxLineGap=6)
mask = np.zeros((H, W), np.uint8)
for s in (segs if segs is not None else []):
    x1, y1, x2, y2 = s[0]; cv2.line(mask, (x1, y1), (x2, y2), 1, 5)
unsc = (mask > 0) & (cand > 0)
b = cv2.imread(D + '44_bins.png', cv2.IMREAD_UNCHANGED); print('bins', None if b is None else (b.shape, b.dtype))
bj = json.load(open(D + '44_bins.json', encoding='utf8')); print({k: v for k, v in bj.items() if k not in ('bins',)} if isinstance(bj, dict) else '')
sm = json.load(open(R + 'streetmap/22-44.json', encoding='utf8')); dr = np.zeros((H, W), np.uint8)
for l in sm['lines']:
    if l['kind'] == 'drawn': cv2.line(dr, tuple(np.round(l['a']).astype(int)), tuple(np.round(l['b']).astype(int)), 1, 3)
drn = (dr > 0) & (cand > 0)
out = dict(segments=0 if segs is None else len(segs), candidate_neg_ink_px=int((cand > 0).sum()), unscored_px=int(unsc.sum()),
           unscored_share_of_candidate=round(float(unsc.sum() / max(1, (cand > 0).sum())), 4),
           drawn_neg_ink_px=int(drn.sum()), drawn_caught=round(float(unsc[drn].mean()), 4) if drn.any() else None,
           unscored_that_is_drawn=round(float((unsc & (dr > 0)).sum() / max(1, unsc.sum())), 4))
if b is not None:
    ids = {v['name']: int(k) for k, v in bj['bins'].items()}
    x0, y0 = bj.get('crop', [0, 0, 0, 0])[:2] if 'crop' in bj else (0, 0)
    bb = b if b.ndim == 2 else b[:, :, 0]
    if bb.shape == (H, W):
        for nm in ('lot line', 'building outline', 'text and numbers', 'block line'):
            m = (bb == ids[nm]) & (cand > 0)
            out[f'{nm}_in_candidate_px'] = int(m.sum()); out[f'{nm}_unscored_share'] = round(float(unsc[m].mean()), 4) if m.any() else None
        out['unscored_by_bin'] = {nm: round(float(((bb == i) & unsc).sum() / max(1, unsc.sum())), 4) for nm, i in ids.items()}
print(json.dumps(out, indent=1)); json.dump(out, open(S + 'v6_fixb.json', 'w'), indent=1)
