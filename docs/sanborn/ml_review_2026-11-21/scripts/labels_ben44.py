"""Plate 44: compare the training targets (N_verified.json, N_label.png, edgenet target) with Ben's checked street map.
Read-only on the repo; writes only into this scratch folder."""
import json, os, sys, collections
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
OUT = os.path.dirname(os.path.abspath(__file__)) + '/'
N = sys.argv[1] if len(sys.argv) > 1 else '44'
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
alphaF = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
SM = json.load(open(SP + f'streetmap/22-{N}.json', encoding='utf8'))
ver = json.load(open(U + f'{N}_verified.json', encoding='utf8'))
I = lambda p: tuple(np.round(p).astype(int).tolist())
# --- rasterise, 1 px
ben = {k: np.zeros((H, W), np.uint8) for k in ('printed', 'drawn', 'sheet_edge', 'no_printed_line')}
for l in SM['lines']: cv2.line(ben[l['kind']], I(l['a']), I(l['b']), 1, 1)
benall = np.zeros((H, W), np.uint8)
for k in ben: benall |= ben[k]
v1 = np.zeros((H, W), np.uint8)
for a, b in ver: cv2.line(v1, I(a), I(b), 1, 1)
dV = cv2.distanceTransform((v1 == 0).astype(np.uint8), cv2.DIST_L2, 5)
dB = cv2.distanceTransform((benall == 0).astype(np.uint8), cv2.DIST_L2, 5)
res = {}
for k, m in ben.items():
    m = (m > 0) & alphaF if k != 'sheet_edge' else (m > 0)
    if m.sum() == 0: continue
    res[f'ben_{k}_px'] = int(m.sum())
    for t in (3, 6, 12): res[f'ben_{k}_within{t}_of_verified'] = round(float((dV[m] <= t).mean()), 4)
mb = (benall > 0) & alphaF
for t in (3, 6, 12): res[f'ben_all_onpaper_within{t}'] = round(float((dV[mb] <= t).mean()), 4)
mv = (v1 > 0) & alphaF
res['verified_px'] = int(mv.sum())
for t in (3, 6, 12): res[f'verified_within{t}_of_ben'] = round(float((dB[mv] <= t).mean()), 4)
# per verified segment: share of its length within 6 px of Ben
segfar = []
for a, b in ver:
    L = np.hypot(b[0] - a[0], b[1] - a[1]); n = max(2, int(L)); t = np.linspace(0, 1, n); q = np.array(a) + np.outer(t, np.array(b) - np.array(a))
    x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1)
    segfar.append((L, float((dB[y, x] > 6).mean())))
segfar = np.array(segfar)
res['verified_len_total'] = round(float(segfar[:, 0].sum()))
res['verified_len_in_segments_mostly_off_ben(>50%_far6)'] = round(float(segfar[segfar[:, 1] > 0.5, 0].sum()))
res['n_segments_mostly_off_ben'] = int((segfar[:, 1] > 0.5).sum())
# --- what kind of ink the off-Ben verified pixels lie on (ink_bins.py bins, rule-based; 44's rail is Ben's own)
bins = cv2.imread(U + f'{N}_bins.png', 0)
NAMES = {0: 'no ink', 1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text', 9: 'not sorted'}
if bins is not None:
    v3 = cv2.dilate(v1, np.ones((3, 3), np.uint8)) > 0            # the 3 px target line
    off = v3 & alphaF & (dB > 6)
    on = v3 & alphaF & (dB <= 3)
    for nm, m in (('offben', off), ('onben', on)):
        c = collections.Counter(bins[m].tolist()); tot = sum(c.values())
        res[f'bins_under_verified_{nm}'] = {NAMES[k]: round(v / tot, 3) for k, v in sorted(c.items())}
        res[f'bins_under_verified_{nm}_px'] = tot
# --- rail: verified near Ben's tracks
rf = SP + f'picks22_guided/22-{N}/rail_ben.json'
if os.path.exists(rf):
    rail = np.zeros((H, W), np.uint8)
    for t in json.load(open(rf, encoding='utf8'))['tracks']: cv2.polylines(rail, [np.round(np.array(t['pts'])).astype(np.int32)], False, 1, 1)
    dR = cv2.distanceTransform((rail == 0).astype(np.uint8), cv2.DIST_L2, 5)
    res['verified_within6_of_rail'] = round(float((dR[mv] <= 6).mean()), 4)
    res['verified_within6_of_rail_and_far_from_ben'] = round(float(((dR[mv] <= 6) & (dB[mv] > 6)).mean()), 4)
    res['verified_px_within6_of_rail_far_from_ben'] = int(((dR <= 6) & (dB > 6) & mv).sum())
# --- the edgenet target as edgenet.load builds it (LINE 3, GAP 4)
LINE, GAP = 3, 4
lab = cv2.resize(cv2.imread(U + f'{N}_label.png', 0), (W, H), interpolation=cv2.INTER_NEAREST)
line = np.zeros((H, W), np.uint8)
for a, b in ver: cv2.line(line, I(a), I(b), 1, LINE)
near = cv2.dilate(line, np.ones((2 * (LINE + GAP) + 1, 2 * (LINE + GAP) + 1), np.uint8)) > 0
t = np.where(line > 0, 1, 0).astype(np.uint8); t[(lab == 255) & ~near] = 255; t[near & (line == 0)] = 255; t[~alphaF] = 255
hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170))
res['edgenet_line_share_of_plate'] = round(float((t == 1).mean()), 4)
res['edgenet_scored_share_of_paper'] = round(float((t != 255)[alphaF].mean()), 4)
# Ben's printed+drawn lines, thickened to the target's 3 px: how are they taught?
bl = cv2.dilate(((ben['printed'] | ben['drawn']) > 0).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
bl &= alphaF
tot = bl.sum()
res['ben_line3px_taught_positive'] = round(float((t[bl] == 1).sum() / tot), 4)
res['ben_line3px_unscored'] = round(float((t[bl] == 255).sum() / tot), 4)
res['ben_line3px_taught_negative'] = round(float((t[bl] == 0).sum() / tot), 4)
res['ben_line3px_taught_negative_on_ink(weight4)'] = round(float(((t[bl] == 0) & ink[bl]).sum() / tot), 4)
# Ben lines far (>8 px) from every verified edge: how are they taught
blf = bl & (dV > 8)
res['ben_line3px_far8_from_verified_share'] = round(float(blf.sum() / tot), 4)
if blf.sum():
    res['ben_far_lines_taught_negative'] = round(float((t[blf] == 0).mean()), 4)
    res['ben_far_lines_taught_negative_on_ink'] = round(float(((t[blf] == 0) & ink[blf]).mean()), 4)
# the line net's validation score recomputed against Ben's lines as the answer (what precision/recall would mean)
# --- area label vs Ben's blocks (half size)
labh = cv2.imread(U + f'{N}_label.png', 0); h, w = labh.shape
alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > 0.5
bk = np.zeros((h, w), np.uint8)
for b in SM['blocks']: cv2.fillPoly(bk, [np.round(np.array(b['ring']) / 2).astype(np.int32)], 1)
narrow = np.zeros((h, w), np.uint8)
for b in SM['blocks']:
    if b['narrow_px'] < 60: cv2.fillPoly(narrow, [np.round(np.array(b['ring']) / 2).astype(np.int32)], 1)
# Ben's lines at half size, 3 px dilated: boundary zone to leave out of the area comparison
bz = np.zeros((h, w), np.uint8)
for l in SM['lines']: cv2.line(bz, I(np.array(l['a']) / 2), I(np.array(l['b']) / 2), 1, 7)
core = alpha & (bz == 0)
benB = (bk == 1) & core; benS = (bk == 0) & core
res['ben_blocks_n'] = len(SM['blocks']); res['ben_narrow_blocks_n'] = sum(b['narrow_px'] < 60 for b in SM['blocks'])
res['ben_block_share_of_paper'] = round(float(bk[alpha].mean()), 4)
for nm, m in (('ben_block', benB), ('ben_notblock', benS)):
    res[f'label_on_{nm}'] = {k: round(float((labh[m] == k).mean()), 4) for k in (0, 1, 255)}
# confusion over taught pixels
taught = core & (labh != 255)
res['label_taught_agrees_with_ben'] = round(float(((labh == 1) == (bk == 1))[taught].mean()), 4)
res['label_block_where_ben_street_share_of_taught'] = round(float(((labh == 1) & (bk == 0))[taught].mean()), 4)
res['label_street_where_ben_block_share_of_taught'] = round(float(((labh == 0) & (bk == 1))[taught].mean()), 4)
# Ben street that the label calls block: connected regions (are they whole 1922 streets?)
wrongB = ((labh == 1) & (bk == 0) & core).astype(np.uint8)
wrongB = cv2.morphologyEx(wrongB, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
n, cc, st, cen = cv2.connectedComponentsWithStats(wrongB, connectivity=8)
big = sorted([(int(st[i, cv2.CC_STAT_AREA]), int(cen[i, 0] * 2), int(cen[i, 1] * 2), int(st[i, 2] * 2), int(st[i, 3] * 2)) for i in range(1, n)], reverse=True)
res['label1_on_ben_street_regions_gt2000px_half'] = [b for b in big if b[0] > 2000][:25]
wrongS = ((labh == 0) & (bk == 1) & core).astype(np.uint8)
wrongS = cv2.morphologyEx(wrongS, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
n, cc, st, cen = cv2.connectedComponentsWithStats(wrongS, connectivity=8)
big2 = sorted([(int(st[i, cv2.CC_STAT_AREA]), int(cen[i, 0] * 2), int(cen[i, 1] * 2), int(st[i, 2] * 2), int(st[i, 3] * 2)) for i in range(1, n)], reverse=True)
res['label0_on_ben_block_regions_gt2000px_half'] = [b for b in big2 if b[0] > 2000][:25]
json.dump(res, open(OUT + f'ben{N}_result.json', 'w'), indent=1)
for k, v in res.items(): print(k, v)
# picture: quarter of half size
img = cv2.imread(U + f'{N}_img.jpg'); vis = (img * 0.5 + 110).astype(np.uint8)
vis[(labh == 1) & (bk == 0) & core] = (0, 0, 230)        # red: label block, Ben not block
vis[(labh == 0) & (bk == 1) & core] = (230, 0, 230)      # magenta: label street, Ben block
vis[(labh == 255) & alpha] = (vis[(labh == 255) & alpha] * 0.5 + 60).astype(np.uint8)
for l in SM['lines']: cv2.line(vis, I(np.array(l['a']) / 2), I(np.array(l['b']) / 2), (0, 140, 0), 2)
for a, b in ver: cv2.line(vis, I(np.array(a) / 2), I(np.array(b) / 2), (230, 120, 0), 1)
cv2.imwrite(OUT + f'ben{N}_label_vs_map.jpg', cv2.resize(vis, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
