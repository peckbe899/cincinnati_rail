"""Round 3 regions: the controls within 600 px of the 37L/37R gutter, and the 33/34R and 34R/38 tie crossings."""
import json, os, sys, pickle
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
REPO = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D'
sys.path.insert(0, REPO + '/tools/sanborn'); import _ws  # noqa
sys.path.insert(0, _ws.CODE + 'cuf'); sys.path.insert(0, _ws.CODE + 'sbg')
import plates as PL  # noqa
from sb import find  # noqa
SP = _ws.DATA; HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(HERE + '/regions.json', encoding='utf8'))
T = {e['n']: e for e in json.load(open(SP + 'reports/2026-11-06_seams_reread/ties15.json', encoding='utf8'))}
jobs = {}
for h, gut in (('37L', lambda x: x >= 6272 - 600), ('37R', lambda x: x <= 600)):
    d = pickle.load(open(SP + f'cuf_cw/{h}/fwd.pkl', 'rb')); X, O = np.asarray(d['X']), np.asarray(d['O'])
    MT = json.load(open(SP + f'cuf_cw/{h}/matches.json', encoding='utf8'))
    for i, (x, y) in enumerate(X):
        if not gut(x): continue
        m = min((q for q in MT if q.get('osm')), key=lambda q: np.hypot(q['x'] - x, q['y'] - y))
        jobs[f'g{h}_{i:02d}'] = dict(kind='control', plate='22-' + h, control_index=i, streets=[m['a'], m['b']], old=[float(x), float(y)], osm=[float(v) for v in O[i]])
for n in (3, 7, 9):
    for p, d in T[n]['plates'].items():
        jobs[f'r3t{n:02d}_{p[3:]}'] = dict(kind='tie', tie=n, plate=p, streets=[T[n]['street_1'], T[n]['street_2']], old=[d['old_pick']['x'], d['old_pick']['y']],
                                          osm=(d['osm_match'] or {}).get('osm'))
def scan(pid):
    n = pid[3:]
    if pid == '22-38': return _ws.ext('/mnt/user-data/uploads/38.png')
    if n in ('34L', '34R', '37L', '37R', '16R'): return find(pid)
    return PL.PNGPATH.get(n, _ws.ext(f'/mnt/user-data/uploads/PNG/{n}.png'))
byp = {}
for j, v in jobs.items(): byp.setdefault(v['plate'], []).append(j)
for pid, js in byp.items():
    im = Image.open(scan(pid)); im.load()
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA'); bg = Image.new('RGBA', im.size, (255, 255, 255, 255)); bg.alpha_composite(im); im = bg
    im = im.convert('RGB'); W, H = im.size
    for j in js:
        v = jobs[j]; cx, cy = v['old']; h = 800
        box = [max(0, int(cx - h)), max(0, int(cy - h)), min(W, int(cx + h)), min(H, int(cy + h))]
        im.crop(tuple(box)).save(f'{HERE}/regions/{j}.png')
        M[j] = dict(v, box=box, size=[W, H], round=3)
        print(j, pid, v['streets'], box)
json.dump(M, open(HERE + '/regions.json', 'w', encoding='utf8', newline='\n'), indent=1)
json.dump(jobs, open(HERE + '/jobs3.json', 'w', encoding='utf8', newline='\n'), indent=1)
