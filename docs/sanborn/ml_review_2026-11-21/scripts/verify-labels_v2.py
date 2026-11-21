"""labels-2: simulate make_labels.py:286-301 on plate 44's current verified set (no repo writes); split the loss by cause."""
import json
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
N = '44'; H, W = 7219, 10768; K = 2; UNSURE = 8; h, w = 3609, 5384
alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
SM = json.load(open(SP + f'streetmap/22-{N}.json', encoding='utf8'))
B = json.load(open(SP + f'picks22_guided/22-{N}/edges_ben.json', encoding='utf8'))['lines']
VER0 = [(np.array(a, float), np.array(b, float)) for a, b in json.load(open(U + f'{N}_verified.json', encoding='utf8'))]
P = lambda p: (int(round(p[0])), int(round(p[1])))
def _same(a_, b_, p_, q_):   # copied from make_labels.py:288-291
    a_, b_, p_, q_ = (np.asarray(v_, float) for v_ in (a_, b_, p_, q_)); d1, d2 = b_ - a_, q_ - p_; L2 = np.hypot(*d2) or 1.0; m_ = (a_ + b_) / 2
    t_ = np.clip(((m_ - p_) @ d2) / L2 ** 2, 0, 1)
    return np.hypot(*(m_ - (p_ + t_ * d2))) < 8 and abs(d1 @ d2) / ((np.hypot(*d1) or 1.0) * L2) > 0.97
def step(VER, lines, removals_first=False, moved_none_ok=False, add_always=False):
    VER = list(VER)
    rem = lambda s_: s_.get('verdict') in ('wrong', 'none') or s_.get('moved')
    isok = lambda s_: s_.get('verdict') == 'ok' or (moved_none_ok and s_.get('moved') and s_.get('verdict') is None)
    if removals_first:
        for s_ in lines:
            if rem(s_): VER = [e_ for e_ in VER if not _same(e_[0], e_[1], s_['a0'], s_['b0'])]
        for s_ in lines:
            if isok(s_):
                new = (np.array(s_['a'], float), np.array(s_['b'], float))
                if add_always or not any(_same(e_[0], e_[1], *new) for e_ in VER): VER.append(new)
        return VER
    for s_ in lines:
        old = (s_['a0'], s_['b0']); new = (np.array(s_['a'], float), np.array(s_['b'], float))
        if rem(s_): VER = [e_ for e_ in VER if not _same(e_[0], e_[1], *old)]
        if isok(s_):
            if add_always or not any(_same(e_[0], e_[1], *new) for e_ in VER): VER.append(new)
    return VER
ben = np.zeros((H, W), np.uint8)
for l in SM['lines']:
    if l['kind'] in ('printed', 'drawn'): cv2.line(ben, P(l['a']), P(l['b']), 1, 1)
mb = (ben > 0) & alpha
benall = np.zeros((H, W), np.uint8)
for l in SM['lines']: cv2.line(benall, P(l['a']), P(l['b']), 1, 1)
dB = cv2.distanceTransform((benall == 0).astype(np.uint8), cv2.DIST_L2, 5)
def score(VER, nm):
    v = np.zeros((H, W), np.uint8)
    for a, b in VER: cv2.line(v, P(a), P(b), 1, 1)
    dV = cv2.distanceTransform((v == 0).astype(np.uint8), cv2.DIST_L2, 5); mv = (v > 0) & alpha
    print(f'{nm:55s} segs {len(VER):5d} cover {float((dV[mb] <= 3).mean()):.4f} prec {float((dB[mv] <= 3).mean()):.4f} len {int(mv.sum())}')
score(VER0, 'current 44_verified.json')
score(step(VER0, B), 'as coded (in order)')
score(step(VER0, B, moved_none_ok=True), 'in order, moved+None treated ok')
score(step(VER0, B, removals_first=True), 'removals first')
score(step(VER0, B, removals_first=True, moved_none_ok=True), 'removals first + moved None ok')
score(step(VER0, B, removals_first=True, moved_none_ok=True, add_always=True), 'removals first + moved None ok + always add')
# what do the removals alone do
Vr = list(VER0)
for s_ in B:
    if s_.get('verdict') in ('wrong', 'none') or s_.get('moved'): Vr = [e_ for e_ in Vr if not _same(e_[0], e_[1], s_['a0'], s_['b0'])]
score(Vr, 'removals only')
# wrong-only removals: how many automatic segments match a 'wrong' line (by midpoint), and their length
wr = [s_ for s_ in B if s_.get('verdict') == 'wrong']
hitw = [e_ for e_ in VER0 if any(_same(e_[0], e_[1], s_['a0'], s_['b0']) for s_ in wr)]
print('auto segs matching a wrong line:', len(hitw), 'len', round(sum(np.hypot(*(b - a)) for a, b in hitw)), 'of', round(sum(np.hypot(*(b - a)) for a, b in VER0)))
# of those, how much lies within 3 px of a Ben kept line (printed/drawn)?
def seg_near(a, b):
    L = np.hypot(*(b - a)); n = max(2, int(L)); t = np.linspace(0, 1, n); q = a + np.outer(t, b - a)
    x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1)
    return float((dB[y, x] <= 3).mean())
nearw = [seg_near(a, b) for a, b in hitw]
print('  share of their length within 3 px of a Ben line (length-weighted):', round(sum(f * np.hypot(*(b - a)) for f, (a, b) in zip(nearw, hitw)) / max(1, sum(np.hypot(*(b - a)) for a, b in hitw)), 4))
# order effect count
lost = 0; oks = [i for i, s in enumerate(B) if s.get('verdict') == 'ok']
for i in oks:
    s = B[i]
    if any((t.get('verdict') in ('wrong', 'none') or t.get('moved')) and _same(s['a'], s['b'], t['a0'], t['b0']) for t in B[i + 1:]): lost += 1
print('ok lines deleted again by a later entry:', lost, 'of', len(oks))
# blanking area (make_labels:297,300) at half size
def strip(mask, a, b, half, val=1):
    a = np.asarray(a, float); b = np.asarray(b, float); d = b - a; L = np.hypot(*d)
    if L < 1e-6: return
    n = np.array([-d[1], d[0]]) / L * half
    cv2.fillPoly(mask, [np.array([a + n, b + n, b - n, a - n]).round().astype(np.int32)], val)
bb = np.zeros((h, w), np.uint8)
for s_ in B:
    old = (s_['a0'], s_['b0']); new = (np.array(s_['a'], float), np.array(s_['b'], float)); v_ = s_.get('verdict'); ch = s_.get('moved') or s_.get('added')
    if (v_ == 'wrong' or s_.get('moved')) and not s_.get('added'): strip(bb, np.array(old[0], float) / K, np.array(old[1], float) / K, UNSURE)
    if v_ == 'ok' and ch: strip(bb, new[0] / K, new[1] / K, UNSURE)
al = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > 0.5
lab = cv2.imread(U + f'{N}_label.png', 0)
print('blank band share of paper', round(float(bb[al].mean()), 4), 'share of taught px', round(float((bb[(lab != 255) & al] == 1).mean()), 4), 'band full width px', 2 * UNSURE * K)
