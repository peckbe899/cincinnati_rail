import json, collections, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
lab = cv2.imread(U + '44_label.png', 0); h, w = lab.shape
SM = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
bk = np.zeros((h, w), np.uint8)
for b in SM['blocks']: cv2.fillPoly(bk, [np.round(np.array(b['ring']) / 2).astype(np.int32)], 1)
for kind in ('railroad', 'streetcar'):
    m = np.zeros((h, w), np.uint8)
    for t in json.load(open(SP + 'picks22_guided/22-44/rail_ben.json', encoding='utf8'))['tracks']:
        if t['kind'] == kind: cv2.polylines(m, [np.round(np.array(t['pts']) / 2).astype(np.int32)], False, 1, 1)
    m = m > 0; c = collections.Counter(lab[m].tolist()); tot = sum(c.values())
    print(kind, 'track px (half)', tot, 'label under track:', {k: round(v / tot, 3) for k, v in sorted(c.items())}, '| inside a block Ben closed:', round(float(bk[m].mean()), 3))
