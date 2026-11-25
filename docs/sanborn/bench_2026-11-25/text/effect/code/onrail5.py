"""onrail5.py (text/effect, 25 Nov 2026): the outline step's 'on rail' test (outlines.py: a side with more than half its
length within 3 px of railroad ink, RAIL_TOL 3, RAIL_SHARE 0.5; dropped from the editor by RAIL_DROP) re-applied to the
sides of plate 5's outlines as Ben saw them (diag/rail5/inputs/outlines.json, copied to inputs/), with the railroad bin
of each run. Also whether each such side lies on Ben's lines (editor lines with his edits, street_map.editor_lines).
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/onrail5.py      -> scores/onrail5.json"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.normpath(os.path.join(ROOT, '..', '..', '..', '..', '..', 'tools', 'sanborn', 'unet')))
import street_map
H, W = 7150, 10076
benl = json.load(open('picks22_guided/22-5/edges_ben.json', encoding='utf8'))
L, _ = street_map.editor_lines('5', W, H, json.load(open(os.path.join(ROOT, 'inputs', '5_edges.json'), encoding='utf8')), benl)
m = np.zeros((H, W), np.uint8)
for l in L: cv2.line(m, tuple(np.round(l['a']).astype(int).tolist()), tuple(np.round(l['b']).astype(int).tolist()), 1, 1)
dben = cv2.distanceTransform((m == 0).astype(np.uint8), cv2.DIST_L2, 5)
P = json.load(open(os.path.join(ROOT, 'inputs', 'outlines.json'), encoding='utf8'))
sides = [s for p in P for s in p if s.get('state') != 'short' and not s.get('paper_edge')]
el = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
def along(img, a, b):
    a, b = np.array(a, float), np.array(b, float); t = np.linspace(0.06, 0.94, max(10, int(np.hypot(*(b - a))))); q = a + np.outer(t, b - a)
    return img[np.clip(q[:, 1].round().astype(int), 0, H - 1), np.clip(q[:, 0].round().astype(int), 0, W - 1)]
out = {}
for run in ('5_nets_base', '5_nets_tS0', '5_nets_tS1', '5_nets_tI2', '5_none_base', '5_none_tS1', '5_none_tI2'):
    rail = cv2.dilate((cv2.imread(os.path.join(ROOT, 'runs', run + '.png'), 0) == 4).astype(np.uint8), el)
    on = [s for s in sides if along(rail, s['a'], s['b']).mean() > 0.5]
    onben = [s for s in on if (along(dben, s['a'], s['b']) <= 8).mean() >= 0.8]
    out[run] = dict(sides=len(sides), on_rail=len(on), on_rail_and_on_ben_lines=len(onben), their_len=round(sum(float(np.hypot(*(np.array(s['b']) - np.array(s['a'])))) for s in onben)), which=[[s['a'], s['b']] for s in onben])
    print(run, {k: v for k, v in out[run].items() if k != 'which'}, flush=True)
json.dump(out, open(os.path.join(ROOT, 'scores', 'onrail5.json'), 'w'), indent=1)
