"""How much of the rules' false railroad on plate 5 lies on the street sides Ben kept or drew (25 Nov 2026, diag/rail5).
Ben's lines = street_map.editor_lines(5, ..., unet_data/5_edges.json, edges_ben.json): what the editor shows with his
edits (read-only import of tools/sanborn/unet). Also: the outline step's 'on rail' sides and whether Ben has a line there.
    cd data/sanborn; python -B bench_2026-11-25/diag/rail5/code/rail_on_lines5.py"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.normpath(os.path.join(ROOT, '..', '..', '..', '..', '..', 'tools', 'sanborn', 'unet')))
import street_map
H, W = 7150, 10076
benl = json.load(open('picks22_guided/22-5/edges_ben.json', encoding='utf8'))
L, SH = street_map.editor_lines('5', W, H, json.load(open(os.path.join(ROOT, 'inputs', '5_edges.json'), encoding='utf8')), benl)
from collections import Counter
print('Ben lines', len(L), Counter(l['kind'] for l in L))
m = np.zeros((H, W), np.uint8)
for l in L: cv2.line(m, tuple(np.round(l['a']).astype(int).tolist()), tuple(np.round(l['b']).astype(int).tolist()), 1, 1)
d = cv2.distanceTransform((m == 0).astype(np.uint8), cv2.DIST_L2, 5)
# Ben's deleted lines (verdict wrong) as well: the lines the networks drew and he took out
mw = np.zeros((H, W), np.uint8)
for l in benl['lines']:
    if l.get('verdict') == 'wrong': cv2.line(mw, tuple(np.round(l['a0']).astype(int).tolist()), tuple(np.round(l['b0']).astype(int).tolist()), 1, 1)
dw = cv2.distanceTransform((mw == 0).astype(np.uint8), cv2.DIST_L2, 5)
def samp(p, step=2):
    p = np.asarray(p, float); S = []
    for a, b in zip(p[:-1], p[1:]):
        n = max(2, int(np.hypot(*(b - a)) / step) + 1); S.append(a + np.linspace(0, 1, n)[:-1, None] * (b - a))
    S.append(p[-1:]); return np.vstack(S)
groups = json.load(open(os.path.join(ROOT, 'crops', 'groups.json')))
rule = [t for t in json.load(open(os.path.join(ROOT, 'inputs', '5_rail_rule.json'), encoding='utf8'))['tracks'] if t['kind'] == 'railroad']
out = dict(groups=[])
for g in groups:
    tot = on = onw = 0.0
    for i in g['tracks']:
        S = samp(rule[i]['pts']); q = S.round().astype(int); tot += len(S); on += (d[q[:, 1], q[:, 0]] <= 8).sum(); onw += (dw[q[:, 1], q[:, 0]] <= 8).sum()
    out['groups'].append(dict(group=g['group'], tracks=len(g['tracks']), len=sum(g['len']), share_on_ben_lines_8px=round(on / tot, 3), share_on_lines_ben_deleted_8px=round(onw / tot, 3)))
    print(out['groups'][-1])
for run in ('orig_nets', 'orig_none'):
    b = cv2.imread(os.path.join(ROOT, 'runs', run + '_bins.png'), 0) == 4
    out[run] = dict(rail_bin_px=int(b.sum()), on_ben_lines_6px=int((b & (d <= 6)).sum()))
    print(run, out[run])
# the outline step's sides 'on rail' and Ben's lines there
P = json.load(open(os.path.join(ROOT, 'inputs', 'outlines.json'), encoding='utf8')); out['on_rail_sides'] = []
for p in P:
    for s in p:
        if s.get('state') == 'on rail':
            S = samp([s['a'], s['b']]); q = S.round().astype(int)
            r = dict(a=s['a'], b=s['b'], was=s.get('was'), share_within_8px_of_ben_line=round(float((d[q[:, 1], q[:, 0]] <= 8).mean()), 3)); out['on_rail_sides'].append(r); print('on rail side', r)
json.dump(out, open(os.path.join(ROOT, 'scores', 'rail_on_lines5.json'), 'w'), indent=1)
