"""outlines.py:92 uses RETR_EXTERNAL: street ground enclosed by a block region (a hole) gives no sides. How much boundary is that?"""
import json, os, numpy as np, cv2
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = D + 'unet_data/'
here = os.path.dirname(os.path.abspath(__file__))
cen = {r['n']: r for r in json.load(open(here + '/census.json'))}
res = {}
for n, r in cen.items():
    f = U + f'{n}_blockmask.png'
    if r['blocks'] is None or not os.path.exists(f) or os.path.getmtime(f) < os.path.getmtime(U + 'models/lines_ng1.done'): continue
    b = (cv2.imread(f, 0) > 0).astype(np.uint8)     # half size
    cs, hier = cv2.findContours(b, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None: continue
    hier = hier[0]; ext = hol = 0.0; nh = 0
    for c, h in zip(cs, hier):
        L = cv2.arcLength(c, True) * 2   # full-size px
        if h[3] < 0: ext += L
        elif cv2.contourArea(c) * 4 >= 6000: hol += L; nh += 1     # holes at least MIN_AREA (full px)
    res[n] = dict(kind=r['kind'], blocks=r['blocks'], holes=nh, hole_len=round(hol), ext_len=round(ext), hole_share=round(hol / max(1, hol + ext), 3))
json.dump(res, open(here + '/holes.json', 'w'), indent=1)
for n, v in sorted(res.items(), key=lambda kv: -kv[1]['hole_share']): print(n, v)
import statistics as s
print('median hole share pdf', s.median(v['hole_share'] for v in res.values() if v['kind'] == 'pdf'), 'png', s.median(v['hole_share'] for v in res.values() if v['kind'] == 'png'))
print('plates with hole share > 0.3:', sum(v['hole_share'] > 0.3 for v in res.values()), 'of', len(res))
