"""Simulate make_labels.py lines 286-301 (Ben's edits applied to VER) on plate 44's current verified set, without
writing anything to the repo, and score the result against Ben's street map. Also try an order-independent variant."""
import json, os
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
N = '44'; H, W = 7219, 10768
alphaF = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
SM = json.load(open(SP + f'streetmap/22-{N}.json', encoding='utf8')); B = json.load(open(SP + f'picks22_guided/22-{N}/edges_ben.json', encoding='utf8'))['lines']
VER0 = [(np.array(a, float), np.array(b, float)) for a, b in json.load(open(U + f'{N}_verified.json', encoding='utf8'))]
I = lambda p: tuple(np.round(p).astype(int).tolist())
def _same(a_, b_, p_, q_):
    a_, b_, p_, q_ = (np.asarray(v_, float) for v_ in (a_, b_, p_, q_)); d1, d2 = b_ - a_, q_ - p_; L2 = np.hypot(*d2) or 1.0; m_ = (a_ + b_) / 2
    t_ = np.clip(((m_ - p_) @ d2) / L2 ** 2, 0, 1)
    return np.hypot(*(m_ - (p_ + t_ * d2))) < 8 and abs(d1 @ d2) / ((np.hypot(*d1) or 1.0) * L2) > 0.97
def apply(VER, lines):
    VER = list(VER)
    for s_ in lines:
        old = (s_['a0'], s_['b0']); new = (np.array(s_['a'], float), np.array(s_['b'], float)); v_ = s_.get('verdict')
        if v_ in ('wrong', 'none') or s_.get('moved'): VER = [e_ for e_ in VER if not _same(e_[0], e_[1], *old)]
        if v_ == 'ok':
            if not any(_same(e_[0], e_[1], *new) for e_ in VER): VER.append(new)
    return VER
def apply2(VER, lines):   # order-independent: remove every old/wrong first, then add every ok
    VER = list(VER)
    for s_ in lines:
        if s_.get('verdict') in ('wrong', 'none') or s_.get('moved'): VER = [e_ for e_ in VER if not _same(e_[0], e_[1], s_['a0'], s_['b0'])]
    for s_ in lines:
        if s_.get('verdict') == 'ok':
            new = (np.array(s_['a'], float), np.array(s_['b'], float))
            if not any(_same(e_[0], e_[1], *new) for e_ in VER): VER.append(new)
    return VER
ben = np.zeros((H, W), np.uint8)
for l in SM['lines']:
    if l['kind'] in ('printed', 'drawn'): cv2.line(ben, I(l['a']), I(l['b']), 1, 1)
benS = np.zeros((H, W), np.uint8)
for l in SM['lines']:
    if l['kind'] == 'sheet_edge': cv2.line(benS, I(l['a']), I(l['b']), 1, 1)
dB = cv2.distanceTransform(((ben | benS) == 0).astype(np.uint8), cv2.DIST_L2, 5)
def score(VER, nm):
    v = np.zeros((H, W), np.uint8)
    for a, b in VER: cv2.line(v, I(a), I(b), 1, 1)
    dV = cv2.distanceTransform((v == 0).astype(np.uint8), cv2.DIST_L2, 5)
    mb = (ben > 0) & alphaF; mv = (v > 0) & alphaF; ms = benS > 0
    print(nm, 'segments', len(VER), '| Ben printed+drawn within 3 px of target:', round(float((dV[mb] <= 3).mean()), 4), '| sheet-edge lines within 3:', round(float((dV[ms] <= 3).mean()), 4), '| target within 3 px of Ben (any kind):', round(float((dB[mv] <= 3).mean()), 4))
score(VER0, 'current 44_verified.json        ')
score(apply(VER0, B), 'after make_labels Ben step (as coded)')
score(apply2(VER0, B), 'order-independent variant        ')
# Ben's map alone as the target
VB = [(np.array(l['a'], float), np.array(l['b'], float)) for l in SM['lines'] if l['kind'] in ('printed', 'drawn')]
score(VB, 'streetmap printed+drawn only     ')
# how many 'ok' entries are dropped by a later 'wrong' (order effect)
lost = 0
for i, s in enumerate(B):
    if s.get('verdict') != 'ok': continue
    new = (s['a'], s['b'])
    for t in B[i + 1:]:
        if (t.get('verdict') in ('wrong', 'none') or t.get('moved')) and _same(new[0], new[1], t['a0'], t['b0']): lost += 1; break
print("'ok' lines that a LATER wrong/moved entry would delete again in make_labels (order effect):", lost, 'of', sum(s.get('verdict') == 'ok' for s in B))
