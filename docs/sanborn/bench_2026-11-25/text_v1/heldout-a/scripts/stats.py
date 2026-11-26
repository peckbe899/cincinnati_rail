"""stats.py: counts for the README (words by kind and flag, pixels by class, words joined to a line) and a
0.6x overview picture of each crop (work/<crop>_overview.jpg: text red, don't care yellow, other ink grey)."""
import os, json, collections, cv2, numpy as np
HO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn'
out = {}
for cid in ('H1', 'H2'):
    d = json.load(open(os.path.join(os.path.dirname(HO), 'heldout', f'{cid}_words.json'), encoding='utf8'))
    M = cv2.imread(os.path.join(os.path.dirname(HO), 'heldout', f'{cid}_mask.png'), 0)
    W = d['words']
    kinds = collections.Counter(w['kind'] for w in W)
    flags = collections.Counter(f.split(':')[0] for w in W for f in w['flags'])
    ops = collections.Counter(b['op'] for b in d['boxes'])
    sc = int(((M == 1) | (M == 2)).sum())
    out[cid] = dict(words=len(W), kinds=dict(kinds.most_common()), flags=dict(flags), hand_boxes=dict(ops),
                    touches_line=sum(w['touches_line'] for w in W), curved=sum('path' in w for w in W),
                    px={k: int((M == v).sum()) for k, v in (('paper', 0), ('ink_not_text', 1), ('text', 2), ('dont_care', 3))},
                    text_share_of_scored_ink=round(int((M == 2).sum()) / sc, 3))
    X0, Y0, X1, Y1 = d['win']
    im = cv2.imread(f"{ROOT}/cufp/22-{d['plate']}.jpg")[Y0:Y1, X0:X1]
    v = (im * 0.3 + 255 * 0.7).astype(np.uint8); v[M == 1] = (130, 130, 130); v[M == 2] = (0, 0, 220); v[M == 3] = (0, 200, 255)
    cv2.imwrite(os.path.join(HO, 'work', f'{cid}_overview.jpg'), cv2.resize(v, None, fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 90])
json.dump(out, open(os.path.join(HO, 'stats.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
