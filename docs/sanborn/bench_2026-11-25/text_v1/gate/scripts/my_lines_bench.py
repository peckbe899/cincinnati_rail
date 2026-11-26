"""Gate scorer's own editor-line check of one bench44 grid (26 Nov 2026), from the definitions of verify lines_recheck.py /
handoff lines_compare.py, written anew. Ben's lines: streetmap/22-44.json (all kinds).
    cd data/sanborn; python -B .../my_lines_bench.py CONTROL_RUN_DIR MASKED_RUN_DIR [MASK_PNG]
shown lines = 44_shown.json less state 'sheet', points every 1 px. false length = points more than 5 px from every Ben
line; false line = under 20% of its points within 8 px of Ben's; Ben line found = 50% or more of its points within 5 px of
a shown line; on text = a false line with 50% or more of its points within 5 px of text ink (mask codes 2, 3)."""
import json, sys, numpy as np
from scipy.spatial import cKDTree
from scipy import ndimage as ndi
from PIL import Image
Image.MAX_IMAGE_PIXELS = None


def P(a, b, step=1.0):
    a, b = np.asarray(a, float), np.asarray(b, float); n = max(1, int(np.ceil(np.hypot(*(b - a)) / step)))
    return a + (np.arange(n + 1) / n)[:, None] * (b - a)


ben = json.load(open('streetmap/22-44.json', encoding='utf8'))['lines']
BP = [P(l['a'], l['b']) for l in ben]; tB = cKDTree(np.vstack(BP))
tx = None
if len(sys.argv) > 3:
    m = np.array(Image.open(sys.argv[3])); dt = ndi.distance_transform_edt(~np.isin(m, (2, 3)))
res = {}
for rd in sys.argv[1:3]:
    S = [l for l in json.load(open(rd + '/44_shown.json', encoding='utf8')) if l.get('state') != 'sheet']
    SP = [P(l['a'], l['b']) for l in S]; allS = np.vstack(SP); tS = cKDTree(allS)
    dS = tB.query(allS)[0]
    fl = []; ont = 0
    for s in SP:
        d = tB.query(s)[0]
        if np.mean(d <= 8) < 0.2:
            fl.append(s)
            if len(sys.argv) > 3:
                q = s.round().astype(int); q[:, 0] = q[:, 0].clip(0, dt.shape[1] - 1); q[:, 1] = q[:, 1].clip(0, dt.shape[0] - 1)
                ont += int(np.mean(dt[q[:, 1], q[:, 0]] <= 5) >= 0.5)
    found = [bool(np.mean(tS.query(b)[0] <= 5) >= 0.5) for b in BP]
    res[rd] = dict(shown=len(S), false_len=int((dS > 5).sum()), false_lines=len(fl), false_on_text=ont, ben_found=sum(found), found=found)
    print(rd, {k: v for k, v in res[rd].items() if k != 'found'})
a, b = [res[r]['found'] for r in sys.argv[1:3]]
lost = [(ben[i]['kind'], round(float(np.hypot(*(np.subtract(ben[i]['b'], ben[i]['a'])))))) for i in range(len(ben)) if a[i] and not b[i]]
gain = [(ben[i]['kind'], round(float(np.hypot(*(np.subtract(ben[i]['b'], ben[i]['a'])))))) for i in range(len(ben)) if b[i] and not a[i]]
print('Ben lines lost', lost, 'gained', gain)
