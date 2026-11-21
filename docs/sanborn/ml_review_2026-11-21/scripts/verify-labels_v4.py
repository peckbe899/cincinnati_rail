"""labels-6 (area rescoring), labels-7 (sheet rule on 43/80/82A/44; 43 wrong lines), labels-11 (in-sample area acc)."""
import json, sys
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
K = 2
def ascore(p, lab):
    m = lab != 255; pr = p[m] > 127; gt = lab[m] == 1
    iou = lambda a, b: float((a & b).sum() / max(1, (a | b).sum()))
    return dict(pixels=int(m.sum()), acc=round(float((pr == gt).mean()), 4), iou_street=round(iou(~pr, ~gt), 4), conf=round(float(np.abs(p[m].astype(np.float32) / 255 - 0.5).mean() * 2), 3))
print('--- labels-6 / labels-11: saved area predictions vs current labels')
for N in ('44', '43', '45', '80', '82A'):
    lab = cv2.imread(U + f'{N}_label.png', 0)
    for m in ('edge_v1', 'area_ng1'):
        p = cv2.imread(U + f'{N}_pred_{m}.png', 0)
        if p is not None: print(N, m, ascore(p, lab))
print('--- labels-7: sheet-edge street rule (make_labels.py:258-279) replayed on current labels')
for N in ('43', '44', '80', '82A', '45'):
    out = cv2.imread(U + f'{N}_label.png', 0); h, w = out.shape
    alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > 0.5
    VER = [(np.array(a, float), np.array(b, float)) for a, b in json.load(open(U + f'{N}_verified.json', encoding='utf8'))]
    mr = U + f'{N}_marked_refined.json'
    wd = [float(np.hypot(*(np.array(m_['left'][0]) - np.array(m_['right'][0])))) for m_ in json.load(open(mr, encoding='utf8'))]
    SHEET_D = float(np.clip(1.3 * np.median(wd), 80, 220)) if wd else 170.0; sheet_st = np.zeros((h, w), np.uint8); nsheet = 0
    steps = np.arange(3.0, SHEET_D / K)
    for a_, b_ in VER:
        a2, b2 = a_ / K, b_ / K; L_ = np.hypot(*(b2 - a2))
        if L_ < 10: continue
        d_ = (b2 - a2) / L_; n_ = np.array([-d_[1], d_[0]]); pts = a2 + np.outer(np.arange(0, L_, 1.0), d_)
        for sg in (1, -1):
            g_ = pts[:, None, :] + sg * steps[None, :, None] * n_; gx_ = g_[:, :, 0].round().astype(int); gy_ = g_[:, :, 1].round().astype(int)
            inside = (gx_ >= 0) & (gx_ < w) & (gy_ >= 0) & (gy_ < h); cxp, cyp = np.clip(gx_, 0, w - 1), np.clip(gy_, 0, h - 1)
            off = ~inside | ~alpha[cyp, cxp]; first = np.where(off.any(1), off.argmax(1), -1)
            before = np.arange(len(steps))[None, :] < first[:, None]
            good = (first > 0) & ~((out[cyp, cxp] == 1) & before).any(1)
            if good.mean() < 0.7: continue
            sel_ = before & good[:, None]; sheet_st[cyp[sel_], cxp[sel_]] = 1; nsheet += 1
    sheet_st = cv2.morphologyEx(sheet_st, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    chg = (sheet_st == 1) & (out != 1) & alpha
    kq = int(2.5 * SHEET_D / 1.3 / K) | 1; a8 = alpha.astype(np.uint8)
    tab = cv2.morphologyEx(a8 & (1 - cv2.morphologyEx(a8, cv2.MORPH_OPEN, np.ones((kq, kq), np.uint8))), cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    chg2 = chg | ((tab == 1) & (out != 1))
    flip = chg2 & (out == 255)
    print(N, 'SHEET_D', round(SHEET_D), 'sheet sides', nsheet, '| px that would become street:', int(flip.sum()), f'= {float(flip.sum() / alpha.sum()):.4f} of paper,', f'{float(flip.sum() / max(1, (out == 0).sum())):.4f} of current street px', '| already street there', int((chg2 & (out == 0)).sum()), '| block in strip (never changed)', int(((sheet_st == 1) & (out == 1)).sum()))
print('--- labels-7: 43 wrong lines vs 43 target')
H, W = cv2.imread(SP + 'cufp/22-43.jpg', cv2.IMREAD_REDUCED_GRAYSCALE_2).shape; H, W = H * 2, W * 2
B = json.load(open(SP + 'picks22_guided/22-43/edges_ben.json', encoding='utf8'))['lines']
ver = json.load(open(U + '43_verified.json', encoding='utf8'))
P = lambda p: (int(round(p[0])), int(round(p[1])))
t = np.zeros((H, W), np.uint8)
for a, b in ver: cv2.line(t, P(a), P(b), 1, 3)
wr = np.zeros((H, W), np.uint8)
for s in B:
    if s.get('verdict') == 'wrong': cv2.line(wr, P(s['a0']), P(s['b0']), 1, 17)
print('43 target px', int(t.sum()), 'within 8 px of a wrong line', int((t & wr).sum()), round(float((t & wr).sum() / t.sum()), 4))
