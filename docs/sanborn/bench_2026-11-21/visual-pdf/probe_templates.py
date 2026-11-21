"""Probe: best match of each template on each PDF sheet (quarter size), to set thresholds for map_area.py.

    python probe_templates.py  -> probe_templates.json, printed table
"""
import glob, json, os, time
import numpy as np, cv2
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
HERE = os.path.dirname(os.path.abspath(__file__)); T = os.path.join(HERE, 'templates')
names = ['key', 'title', 'bar200', 'bar400', 'note200a', 'note200b', 'note400a']
tpl = {k: cv2.imread(os.path.join(T, f'{k}.png'), 0) for k in names + ['rose']}
pl = sorted([os.path.basename(os.path.dirname(p)) for p in glob.glob(D + 'cufp/*/source.json')], key=lambda s: int(''.join(c for c in s if c.isdigit())))
out = {}
for n in pl:
    t0 = time.time(); g = cv2.imread(D + f'cufp/22-{n}.jpg', cv2.IMREAD_REDUCED_GRAYSCALE_4); row = {}
    for k in names:
        best = (-1, None, None)
        for s in (0.97, 1.0, 1.03):
            t = cv2.resize(tpl[k], None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            r = cv2.matchTemplate(g, t, cv2.TM_CCOEFF_NORMED); _, mx, _, loc = cv2.minMaxLoc(r)
            # second best peak away from the first
            r2 = r.copy(); x, y = loc; r2[max(0, y - t.shape[0]):y + t.shape[0], max(0, x - t.shape[1]):x + t.shape[1]] = -1
            if mx > best[0]: best = (mx, (x * 4, y * 4, s), float(r2.max()))
        row[k] = dict(score=round(best[0], 3), at=best[1], second=round(best[2], 3))
    # rose: 24 rotations
    best = (-1, None)
    c = (tpl['rose'].shape[1] / 2, tpl['rose'].shape[0] / 2)
    for a in range(0, 360, 15):
        M = cv2.getRotationMatrix2D(c, a, 1.0); t = cv2.warpAffine(tpl['rose'], M, tpl['rose'].shape[::-1], borderMode=cv2.BORDER_REPLICATE)
        t = t[15:-15, 15:-15]
        r = cv2.matchTemplate(g, t, cv2.TM_CCOEFF_NORMED); _, mx, _, loc = cv2.minMaxLoc(r)
        if mx > best[0]: best = (mx, (loc[0] * 4 + 60 * 2, loc[1] * 4 + 60 * 2, a))
    row['rose'] = dict(score=round(best[0], 3), at=best[1])
    out[n] = row
    print(n, f'{time.time() - t0:.1f}s', ' '.join(f"{k}={v['score']:.2f}/{v.get('second', 0):.2f}" for k, v in row.items()), flush=True)
json.dump(out, open(os.path.join(HERE, 'probe_templates.json'), 'w'), indent=1)
