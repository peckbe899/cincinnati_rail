"""Read-only checks of edgenet.py's target, weights, crop sampling and score() (system python, no torch).
Replicates edgenet.load() (lines 42-63) and score() (77-82) exactly, then:
  - target line px per plate (compare with train_ng1.log / train_l2.log)
  - how much of the target lies on ink, crop statistics of the 80% rule
  - lines_v2's saved 44 prediction re-scored on TODAY's 44 target, a threshold sweep, and the share of drawing score() ignores
  - the 44 target against Ben's checked street map (streetmap/22-44.json)"""
import json, sys
import numpy as np, cv2
R = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; D = R + 'unet_data/'
LINE, GAP, TOL, NEG_INK, POS, CROP, JIT = 3, 4, 3, 4.0, 3.0, 448, 24
res = {}

def ink_image(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV); gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170))
    return ink

def target(plate):
    full = cv2.imread(R + f'cufp/22-{plate}.jpg'); H, W = full.shape[:2]; ink = ink_image(full); del full
    lab = cv2.resize(cv2.imread(D + f'{plate}_label.png', 0), (W, H), interpolation=cv2.INTER_NEAREST)
    line = np.zeros((H, W), np.uint8)
    for a, b in json.load(open(D + f'{plate}_verified.json', encoding='utf8')):
        cv2.line(line, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), 1, LINE)
    alpha = cv2.resize(np.load(R + f'cufp/{plate}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
    near = cv2.dilate(line, np.ones((2 * (LINE + GAP) + 1, 2 * (LINE + GAP) + 1), np.uint8)) > 0
    t = np.where(line > 0, 1, 0).astype(np.uint8)
    t[(lab == 255) & ~near] = 255; t[near & (line == 0)] = 255; t[~alpha] = 255
    return t, ink, lab, alpha, line

def score(p, t, thr=0.5):
    pr = p > thr; k = np.ones((2 * TOL + 1, 2 * TOL + 1), np.uint8); line = t == 1; scored = t != 255
    near_line = cv2.dilate(line.astype(np.uint8), k) > 0; near_pr = cv2.dilate(pr.astype(np.uint8), k) > 0
    drawn = pr & (scored | near_line)
    return dict(thr=thr, precision=round(float((drawn & near_line).sum() / max(1, drawn.sum())), 4), recall=round(float((line & near_pr).sum() / max(1, line.sum())), 4),
                drawn_share_of_plate=round(float(pr.mean()), 4), line_share_of_plate=round(float(line.mean()), 4),
                share_of_drawing_not_scored=round(float(1 - drawn.sum() / max(1, pr.sum())), 4))

rng = np.random.default_rng(1)
for plate in ('82A', '80', '43', '45', '44'):
    t, ink, lab, alpha, line = target(plate); H, W = t.shape
    lp = int((t == 1).sum()); on_ink = float(ink[t == 1].mean())
    # distance from target line px to nearest ink: how far the verified edge sits off the printed line
    dist_ink = cv2.distanceTransform((~ink).astype(np.uint8), cv2.DIST_L2, 3)
    d = dist_ink[t == 1]
    # 'centre' of the 3-px line: thin line drawn 1 px
    l1 = np.zeros((H, W), np.uint8)
    for a, b in json.load(open(D + f'{plate}_verified.json', encoding='utf8')):
        cv2.line(l1, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), 1, 1)
    dc = dist_ink[l1 > 0]
    neg = t == 0; neg_ink = neg & ink
    # the effective unscored margin: distance (px) from the line centre to where scoring resumes
    near = cv2.dilate(line, np.ones((15, 15), np.uint8)) > 0
    dl = cv2.distanceTransform((l1 == 0).astype(np.uint8), cv2.DIST_L2, 3)
    margin_px = float(np.percentile(dl[near & ~(cv2.dilate(near.astype(np.uint8), np.ones((3, 3), np.uint8)) == 0)], 50)) if False else None
    # ink inside the unscored margin (lot lines / walls parallel to a block line are neither positive nor negative there)
    marg = near & (line == 0) & alpha
    # crop sampling: share of uniform crops with >= 60 line px, and share of crops kept by the 80% rule that are mostly unscored
    n, has, keep_unsc, kept = 2000, 0, 0, 0; frac_line_in_kept = []
    for _ in range(n):
        y = rng.integers(JIT, H - CROP - JIT); x = rng.integers(JIT, W - CROP - JIT); b = t[y:y + CROP, x:x + CROP]
        h_ = (b == 1).sum() >= 60; has += h_
        if h_ or rng.random() >= 0.8:
            kept += 1; keep_unsc += (b != 255).mean() < 0.1; frac_line_in_kept.append(float((b == 1).sum() / max(1, (b != 255).sum())))
    res[plate] = dict(line_px=lp, scored_share=round(float((t != 255).mean()), 3), line_px_on_ink=round(on_ink, 4),
                      line_centre_on_ink=round(float((dc == 0).mean()), 4), line_centre_median_px_to_ink=round(float(np.median(dc)), 2), line_centre_p90_px_to_ink=round(float(np.percentile(dc, 90)), 2),
                      line_centre_over_2px_from_ink=round(float((dc > 2).mean()), 4),
                      neg_px=int(neg.sum()), neg_ink_px=int(neg_ink.sum()), weight_share_pos=round(float(lp * POS / (lp * POS + neg.sum() + neg_ink.sum() * (NEG_INK - 1))), 4),
                      ink_share_in_margin=round(float(ink[marg].mean()), 4), margin_px=int(marg.sum()),
                      crops_with_line=round(has / n, 3), kept_crops_mostly_unscored=round(keep_unsc / max(1, kept), 3),
                      pos_share_of_scored_in_kept_crops=round(float(np.mean(frac_line_in_kept)), 4), pos_share_of_scored_plate=round(lp / max(1, int((t != 255).sum())), 4))
    print(plate, json.dumps(res[plate]), flush=True)
    if plate == '44':
        for name in ('lines_v2', 'lines_v1'):
            p = cv2.imread(D + f'44_lines_{name}.png', 0)
            if p is None: continue
            p = p.astype(np.float32) / 255
            res[f'44/{name}/today_target'] = [score(p, t, th) for th in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8)]
            for s in res[f'44/{name}/today_target']: print(name, json.dumps(s), flush=True)
        # Ben's checked street map: lines by kind, 3 px, against the target
        sm = json.load(open(R + 'streetmap/22-44.json', encoding='utf8'))
        ben = {k: np.zeros((H, W), np.uint8) for k in ('printed', 'drawn', 'sheet_edge')}
        for l in sm['lines']:
            cv2.line(ben[l['kind']], tuple(np.round(l['a']).astype(int)), tuple(np.round(l['b']).astype(int)), 1, LINE)
        kT = np.ones((2 * TOL + 1, 2 * TOL + 1), np.uint8)
        near_ver = cv2.dilate((t == 1).astype(np.uint8), kT) > 0
        benall = (ben['printed'] | ben['drawn']) > 0
        near_ben = cv2.dilate(benall.astype(np.uint8), kT) > 0
        g = {}
        for k, m in ben.items():
            m = (m > 0) & alpha
            g[k] = dict(px=int(m.sum()), in_target_pos=round(float((t[m] == 1).mean()), 4), within_tol_of_target=round(float(near_ver[m].mean()), 4),
                        on_scored_negative=round(float((t[m] == 0).mean()), 4), unscored=round(float((t[m] == 255).mean()), 4), on_ink=round(float(ink[m].mean()), 4))
        g['target_pos_within_tol_of_ben_printed_or_drawn'] = round(float(near_ben[t == 1].mean()), 4)
        sheet_near = cv2.dilate(ben['sheet_edge'], kT) > 0
        g['target_pos_within_tol_of_ben_sheet_edge'] = round(float(sheet_near[t == 1].mean()), 4)
        # Ben's street sides that would be scored as NOT a line, and how many of those px are ink (real printed line taught as negative)
        bn = benall & (t == 0)
        g['ben_px_scored_negative'] = int(bn.sum()); g['ben_px_scored_negative_on_ink'] = int((bn & ink).sum())
        res['44/ben_vs_target'] = g; print(json.dumps(g), flush=True)
        # lines_v2's drawing against Ben's map over the whole paper (what a reader of an unplaced plate gets)
        for name in ('lines_v2',):
            p = cv2.imread(D + f'44_lines_{name}.png', 0) > 127
            pa = p & alpha
            inner = cv2.erode(alpha.astype(np.uint8), np.ones((121, 121), np.uint8)) > 0
            near_ben_all = cv2.dilate(((ben['printed'] | ben['drawn'] | ben['sheet_edge']) > 0).astype(np.uint8), kT) > 0
            near_p = cv2.dilate(p.astype(np.uint8), kT) > 0
            res[f'44/{name}/vs_ben'] = dict(precision_whole_paper=round(float(near_ben_all[pa].mean()), 4), precision_inner=round(float(near_ben_all[pa & inner].mean()), 4),
                                           recall_printed=round(float(near_p[(ben['printed'] > 0) & alpha].mean()), 4), recall_drawn=round(float(near_p[(ben['drawn'] > 0) & alpha].mean()), 4))
            print(name, 'vs Ben', json.dumps(res[f'44/{name}/vs_ben']), flush=True)
    del t, ink, lab, alpha, line, dist_ink
json.dump(res, open(sys.argv[1], 'w'), indent=1)
