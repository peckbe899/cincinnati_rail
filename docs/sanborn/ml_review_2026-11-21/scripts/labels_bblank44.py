"""Simulate make_labels.py 292-301 band blanking (area label) for plate 44 and the lines street_map keeps but make_labels would not teach."""
import json, collections
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
N = '44'; K, UNSURE = 2, 8
lab = cv2.imread(U + f'{N}_label.png', 0); h, w = lab.shape
alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > 0.5
B = json.load(open(SP + f'picks22_guided/22-{N}/edges_ben.json', encoding='utf8'))['lines']
def strip(mask, a, b, half, val=1):
    a = np.asarray(a, float); b = np.asarray(b, float); d = b - a; L = np.hypot(*d)
    if L < 1e-6: return
    n = np.array([-d[1], d[0]]) / L * half
    cv2.fillPoly(mask, [np.array([a + n, b + n, b - n, a - n]).round().astype(np.int32)], val)
bb = np.zeros((h, w), np.uint8)
for s_ in B:
    old = (s_['a0'], s_['b0']); new = (np.array(s_['a'], float), np.array(s_['b'], float)); v_ = s_.get('verdict'); changed = s_.get('moved') or s_.get('added')
    if (v_ == 'wrong' or s_.get('moved')) and not s_.get('added'): strip(bb, np.array(old[0], float) / K, np.array(old[1], float) / K, UNSURE)
    if v_ == 'ok' and changed: strip(bb, new[0] / K, new[1] / K, UNSURE)
m = (bb == 1) & alpha
print('band blanked by Ben step: share of paper', round(float(m.mean() / alpha.mean()), 4), '| of currently taught px it would blank', round(float((m & (lab != 255)).sum() / ((lab != 255) & alpha).sum()), 4))
c = collections.Counter((s.get('verdict'), bool(s.get('moved')), bool(s.get('added')), s.get('state')) for s in B)
print('moved with no verdict (kept by street_map, not taught by make_labels):', sum(v for k, v in c.items() if k[0] is None and k[1]))
print("'ok' on a sheet line (street_map: sheet_edge; make_labels: added to verified = line target on paper edge):", sum(v for k, v in c.items() if k[0] == 'ok' and k[3] == 'sheet'))
SM = json.load(open(SP + f'streetmap/22-{N}.json', encoding='utf8'))
print('streetmap kinds', SM['counts']['by_kind'])
# untouched orange edges in the editor's view that street_map counts as printed
import sys; sys.path.insert(0, 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet'); sys.path.insert(0, 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn')
import os; os.chdir(SP)
import edit_server as es
E = es.clean(json.load(open(U + f'{N}_edges.json', encoding='utf8')))
key = lambda a, b: tuple(round(v) for v in a + b); by = {key(l['a0'], l['b0']) for l in B if not l.get('added')}
unt = collections.Counter(e['state'] for e in E if key(e['a'], e['b']) not in by)
print('cleaned editor lines Ben did not touch, by state:', dict(unt))
L_or = sum(np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1]) for e in E if key(e['a'], e['b']) not in by and e['state'] == 'orange')
print('untouched orange length (street_map: printed truth; make_labels: blanked, not taught):', round(L_or))
