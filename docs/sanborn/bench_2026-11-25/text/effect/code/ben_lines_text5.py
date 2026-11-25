"""ben_lines_text5.py (text/effect, 25 Nov 2026): plate 5, how much of Ben's checked lines (the editor lines with his edits,
street_map.editor_lines on diag/rail5 inputs/5_edges.json + edges_ben.json, read-only) each text mask lies on (within
1 px) and touches (within 2 px). Here the text bin comes from the networks' ground, not a street map.
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/ben_lines_text5.py      -> scores/ben_lines_text5.json"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.normpath(os.path.join(ROOT, '..', '..', '..', '..', '..', 'tools', 'sanborn', 'unet')))
import street_map
H, W = 7150, 10076
L, _ = street_map.editor_lines('5', W, H, json.load(open(os.path.join(ROOT, 'inputs', '5_edges.json'), encoding='utf8')), json.load(open('picks22_guided/22-5/edges_ben.json', encoding='utf8')))
P = []
for l in L:
    a, b = np.array(l['a'], float), np.array(l['b'], float); n = max(1, int(np.ceil(np.hypot(*(b - a))))); P.append(a + ((np.arange(n) + 0.5) / n)[:, None] * (b - a))
P = np.clip(np.round(np.concatenate(P)).astype(int), 0, [W - 1, H - 1]); out = dict(ben_lines=len(L), ben_len=int(len(P)))
for m in ('S0', 'S1', 'I2'):
    M = cv2.imread(os.path.join(ROOT, 'masks', f'5_nets_{m}.png'), 0) > 0
    out[m] = {nm: round(float((cv2.dilate(M.astype(np.uint8), np.ones((2 * r + 1, 2 * r + 1), np.uint8)) > 0)[P[:, 1], P[:, 0]].mean()), 4) for r, nm in ((1, 'on_1px'), (2, 'touch_2px'))}
print(json.dumps(out)); json.dump(out, open(os.path.join(ROOT, 'scores', 'ben_lines_text5.json'), 'w'), indent=1)
