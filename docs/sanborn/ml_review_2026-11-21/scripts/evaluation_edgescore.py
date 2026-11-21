"""edgenet.score() re-implemented (same rule: TOL 3, LINE 3, GAP 4) on the CURRENT 44 target, for any saved line map"""
import json, sys, os, numpy as np, cv2, evallib as E
LINE, GAP, TOL = 3, 4, 3
def target(plate='44', verified=None):
    full = cv2.imread(E.SP + f'cufp/22-{plate}.jpg'); H, W = full.shape[:2]
    lab = cv2.resize(cv2.imread(E.U + f'{plate}_label.png', 0), (W, H), interpolation=cv2.INTER_NEAREST)
    line = np.zeros((H, W), np.uint8)
    for a, b in (verified if verified is not None else json.load(open(E.U + f'{plate}_verified.json'))):
        cv2.line(line, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), 1, LINE)
    alpha = cv2.resize(np.load(E.SP + f'cufp/{plate}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
    near = cv2.dilate(line, np.ones((2 * (LINE + GAP) + 1, 2 * (LINE + GAP) + 1), np.uint8)) > 0
    t = np.where(line > 0, 1, 0).astype(np.uint8); t[(lab == 255) & ~near] = 255; t[near & (line == 0)] = 255; t[~alpha] = 255
    return t
def score(pr, t):
    k = np.ones((2 * TOL + 1, 2 * TOL + 1), np.uint8); line = t == 1; scored = t != 255
    near_line = cv2.dilate(line.astype(np.uint8), k) > 0; near_pr = cv2.dilate(pr.astype(np.uint8), k) > 0
    drawn = pr & (scored | near_line)
    return dict(precision=round(float((drawn & near_line).sum() / max(1, drawn.sum())), 4), recall=round(float((line & near_pr).sum() / max(1, line.sum())), 4),
                drawn_share_of_plate=round(float(pr.mean()), 4), line_share_of_plate=round(float(line.mean()), 4),
                share_of_drawn_on_unscored_ground=round(float((pr & ~(scored | near_line)).sum() / max(1, pr.sum())), 4))
if __name__ == '__main__':
    t = target('44'); out = {}
    for f in sys.argv[1:]:
        out[os.path.basename(f)] = score(cv2.imread(f, 0) > 127, t)
    # Ben's own lines, drawn the way the target is drawn, scored as if they were a prediction: the ceiling this target allows
    T = E.truth('44'); W, H = T['size']; b = np.zeros((H, W), np.uint8)
    for l in T['lines']: cv2.line(b, tuple(np.round(l['a']).astype(int)), tuple(np.round(l['b']).astype(int)), 1, LINE)
    out['BEN_streetmap_as_prediction'] = score(b > 0, t)
    print(json.dumps(out, indent=1))
