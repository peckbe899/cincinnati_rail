"""RETR_EXTERNAL (outlines.py:92) also drops every block that lies inside a hole of another block: count them"""
import json, os, numpy as np, cv2
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = D + 'unet_data/'
here = os.path.dirname(os.path.abspath(__file__)); H = json.load(open(here + '/holes.json'))
tot = dict(comp=0, ext=0, lost_len=0.0, all_len=0.0); rows = {}
for n in H:
    b = (cv2.imread(U + f'{n}_blockmask.png', 0) > 0).astype(np.uint8)
    ext = cv2.findContours(b, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]
    allc, hier = cv2.findContours(b, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE); hier = hier[0]
    def depth(i):
        d = 0
        while hier[i][3] >= 0: i = hier[i][3]; d += 1
        return d
    outer = [i for i in range(len(allc)) if depth(i) % 2 == 0]          # every block's outer boundary
    nested = [i for i in outer if depth(i) > 0]                           # blocks lying inside another block's hole
    lost = sum(cv2.arcLength(allc[i], True) * 2 for i in nested); al = sum(cv2.arcLength(allc[i], True) * 2 for i in outer)
    rows[n] = dict(blocks_found=len(outer), exported=len(ext), nested_dropped=len(nested), nested_len=round(lost))
    tot['comp'] += len(outer); tot['ext'] += len(ext); tot['lost_len'] += lost; tot['all_len'] += al
for n, v in sorted(rows.items(), key=lambda kv: -kv[1]['nested_dropped'])[:16]: print(n, H[n]['kind'], v)
print('all plates: block regions', tot['comp'], 'exported', tot['ext'], 'dropped as nested', tot['comp'] - tot['ext'], 'nested outline length share', round(tot['lost_len'] / tot['all_len'], 3))
json.dump(rows, open(here + '/islands.json', 'w'), indent=1)
