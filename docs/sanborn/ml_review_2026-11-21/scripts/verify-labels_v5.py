"""labels-8 (untouched lines on 44; what street_map does with saved lines that no longer match), labels-10 (sheet 'ok' lines)."""
import json, sys, collections
import numpy as np, cv2
sys.path.insert(0, 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet'); sys.path.insert(0, 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn')
import edit_server as es
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
N = '44'
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
B = json.load(open(SP + f'picks22_guided/22-{N}/edges_ben.json', encoding='utf8'))['lines']
E = es.clean(json.load(open(U + f'{N}_edges.json', encoding='utf8'))) + es.sheet(N, W, H)
key = lambda a, b: tuple(round(v) for v in a + b)
by = {key(l['a0'], l['b0']): l for l in B if not l.get('added')}
ek = {key(e['a'], e['b']) for e in E}
un = collections.Counter(e['state'] for e in E if key(e['a'], e['b']) not in by)
print('editor lines', len(E), 'by state', collections.Counter(e['state'] for e in E))
print('untouched by state', dict(un))
orph = [l for l in B if not l.get('added') and key(l['a0'], l['b0']) not in ek]
print('saved non-added lines that match no current editor line (street_map drops these):', len(orph))
# labels-10: Ben 'ok' sheet lines: distance to paper edge and ink along them
alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
dIn = cv2.distanceTransform(alpha.astype(np.uint8), cv2.DIST_L2, 5)     # distance inside the paper to its edge
hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170)); del hsv
rows = []
for s in B:
    if s.get('src') == 'sheet' and s.get('verdict') == 'ok':
        a, b = np.array(s['a'], float), np.array(s['b'], float); L = np.hypot(*(b - a)); t = np.linspace(0, 1, max(2, int(L))); q = a + np.outer(t, b - a)
        x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1)
        mv = float(np.hypot(*(np.array(s['a']) - np.array(s['a0']))) + np.hypot(*(np.array(s['b']) - np.array(s['b0']))))
        # ink within 2 px of the line
        inkn = cv2.dilate(ink[max(0, y.min() - 3):y.max() + 4, max(0, x.min() - 3):x.max() + 4].astype(np.uint8), np.ones((5, 5), np.uint8))
        on = inkn[y - max(0, y.min() - 3), x - max(0, x.min() - 3)].mean()
        rows.append((round(L), round(float(np.median(dIn[y, x])), 1), round(float(on), 2), round(mv, 1)))
rows.sort(key=lambda r: -r[0])
print('ok sheet lines (len, median px inside paper edge, share with ink within 2 px, endpoint move sum):')
for r in rows: print('  ', r)
L = np.array([r[0] for r in rows]); d = np.array([r[1] for r in rows]); o = np.array([r[2] for r in rows])
print('total len', L.sum(), 'len-weighted median-inside', round(float((L * d).sum() / L.sum()), 1), 'len-weighted ink share', round(float((L * o).sum() / L.sum()), 3))
# make_labels would add them only if no VER piece already matches them
ver = [(np.array(a, float), np.array(b, float)) for a, b in json.load(open(U + f'{N}_verified.json', encoding='utf8'))]
def _same(a_, b_, p_, q_):
    a_, b_, p_, q_ = (np.asarray(v_, float) for v_ in (a_, b_, p_, q_)); d1, d2 = b_ - a_, q_ - p_; L2 = np.hypot(*d2) or 1.0; m_ = (a_ + b_) / 2
    t_ = np.clip(((m_ - p_) @ d2) / L2 ** 2, 0, 1)
    return np.hypot(*(m_ - (p_ + t_ * d2))) < 8 and abs(d1 @ d2) / ((np.hypot(*d1) or 1.0) * L2) > 0.97
added = [s for s in B if s.get('src') == 'sheet' and s.get('verdict') == 'ok' and not any(_same(e[0], e[1], s['a'], s['b']) for e in ver)]
print('ok sheet lines with no matching automatic piece (would be appended):', len(added), 'len', round(sum(np.hypot(*(np.array(s['b']) - np.array(s['a']))) for s in added)))
