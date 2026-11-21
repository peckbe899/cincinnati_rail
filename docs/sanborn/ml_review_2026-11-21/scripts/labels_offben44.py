"""Plate 44: verified segments that are mostly off Ben's lines; do they match lines Ben marked wrong / moved?"""
import json, os
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
OUT = os.path.dirname(os.path.abspath(__file__)) + '/'
N = '44'
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
alphaF = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
SM = json.load(open(SP + f'streetmap/22-{N}.json', encoding='utf8')); B = json.load(open(SP + f'picks22_guided/22-{N}/edges_ben.json', encoding='utf8'))['lines']
ver = json.load(open(U + f'{N}_verified.json', encoding='utf8'))
I = lambda p: tuple(np.round(p).astype(int).tolist())
benall = np.zeros((H, W), np.uint8)
for l in SM['lines']: cv2.line(benall, I(l['a']), I(l['b']), 1, 1)
dB = cv2.distanceTransform((benall == 0).astype(np.uint8), cv2.DIST_L2, 5)
def same(a_, b_, p_, q_, tol=8):   # make_labels.py _same
    a_, b_, p_, q_ = (np.asarray(v_, float) for v_ in (a_, b_, p_, q_)); d1, d2 = b_ - a_, q_ - p_; L2 = np.hypot(*d2) or 1.0; m_ = (a_ + b_) / 2
    t_ = np.clip(((m_ - p_) @ d2) / L2 ** 2, 0, 1)
    return np.hypot(*(m_ - (p_ + t_ * d2))) < tol and abs(d1 @ d2) / ((np.hypot(*d1) or 1.0) * L2) > 0.97
wrong = [(l['a0'], l['b0']) for l in B if l.get('verdict') == 'wrong']
moved = [(l['a0'], l['b0']) for l in B if l.get('moved')]
off = []; Ltot = 0
for a, b in ver:
    L = np.hypot(b[0] - a[0], b[1] - a[1]); Ltot += L; t = np.linspace(0, 1, max(2, int(L))); q = np.array(a) + np.outer(t, np.array(b) - np.array(a))
    x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1)
    far = float((dB[y, x] > 6).mean()); onp = float(alphaF[y, x].mean())
    if far > 0.5: off.append(dict(a=a, b=b, L=L, onpaper=onp, wrong=any(same(a, b, *o) for o in wrong), moved=any(same(a, b, *o) for o in moved)))
print('verified segments', len(ver), 'length', round(Ltot))
print('mostly off Ben', len(off), 'length', round(sum(o['L'] for o in off)))
print('  of those Ben marked wrong:', sum(o['wrong'] for o in off), round(sum(o['L'] for o in off if o['wrong'])))
print('  Ben moved (old position):', sum(o['moved'] and not o['wrong'] for o in off), round(sum(o['L'] for o in off if o['moved'] and not o['wrong'])))
print('  neither (untouched by Ben, yet not on his map):', sum(not o['moved'] and not o['wrong'] for o in off), round(sum(o['L'] for o in off if not o['moved'] and not o['wrong'])))
print('  mostly off paper (<50% on paper):', sum(o['onpaper'] < 0.5 for o in off))
# all verified segments matched to Ben's wrong lines, whatever the distance
nw = [(a, b) for a, b in ver if any(same(a, b, *o) for o in wrong)]
print('verified segments that match a line Ben marked wrong:', len(nw), 'length', round(sum(np.hypot(b[0] - a[0], b[1] - a[1]) for a, b in nw)))
vis = cv2.resize(full, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA); vis = (vis * 0.6 + 90).astype(np.uint8)
for l in SM['lines']: cv2.line(vis, I(np.array(l['a']) / 4), I(np.array(l['b']) / 4), (0, 150, 0), 1)
for o in off: cv2.line(vis, I(np.array(o['a']) / 4), I(np.array(o['b']) / 4), (0, 0, 255) if o['wrong'] else ((255, 0, 255) if o['moved'] else (255, 120, 0)), 3)
cv2.imwrite(OUT + 'offben44.jpg', vis, [cv2.IMWRITE_JPEG_QUALITY, 85])
