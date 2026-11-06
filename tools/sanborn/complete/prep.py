"""Part 1 of the complete-control fit (rule 12): the reading jobs. Every OSM crossing of two named streets on each 1922
plate (tools/sanborn/dense/locate.py osm_network: realigned streets left out, renamed ones kept, rule 3 aliases them)
that no existing pick (sbg/picks22) with the same names, aliased as cufp/fit.py aliases them, covers within 45 m under
the plate's current model. For each, a region of the scan 1,800 px square around the crossing's predicted pixel.

    python tools/sanborn/complete/prep.py JOBS_DIR      (writes JOBS_DIR/jobs.json, info.json, regions/<job>.jpg)

Then two reads per job (READERS.md, crop.py) and collect.py.
"""
import json, os, re, sys, collections
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
os.chdir(REPO + '/data/sanborn')
sys.path.insert(0, REPO + '/tools/sanborn'); sys.path.insert(0, REPO + '/tools/sanborn/dense'); sys.path.insert(0, REPO + '/tools/sanborn/joint')
import _ws, seams as S, locate as L, curl  # noqa
from names import key, base  # noqa
HERE = os.path.abspath(sys.argv[1]); os.makedirs(HERE + '/regions', exist_ok=True)
src = open(_ws.CODE + 'cufp/fit.py', encoding='utf8').read()
ns = dict(key=key); exec(re.search(r"^ALIAS = \{.*?\}\.items\(\)\}", src, re.S | re.M).group(0), ns); ALIAS = ns['ALIAS']
SUFX = {'rd', 'av', 'ave', 'st', 'pl', 'ter', 'ln', 'dr', 'ct', 'blvd', 'way', 'pk', 'pike', 'al', 'aly', 'cir', 'pkwy', 'sq', 'row', 'road', 'avenue', 'street', 'place', 'terrace', 'lane', 'drive', 'court', 'alley'}
def stem(k):
    w = base(k).split(); return ' '.join(w[:-1]) if len(w) > 1 and w[-1] in SUFX else ' '.join(w)
def norm(name):
    k = key(name); k = ALIAS.get(k, k); return stem(k)
lines, inter = L.osm_network()
jobs, info = {}, {}
for pid in S.plate_ids():
    im, mask = L.plate_image(pid); h, w = im.shape[:2]
    side = curl.side_of(pid); fold = side if (side.get('fold') and pid[-1] in 'LR') else None
    mt = L.Matcher(im, mask, fold); M = L.Model(pid)
    G = M.fwd(np.array([[0, 0], [w, 0], [w, h], [0, h]], float)); lo, hi = G.min(0) - 50, G.max(0) + 50
    cand = [c for c in inter if lo[0] < c[0] < hi[0] and lo[1] < c[1] < hi[1]]
    q = M.inv(np.array([c[:2] for c in cand])); on = mt.on_page(q)
    picks, nf = S.plate_crossings(pid)
    P = np.array([[p['E'], p['N']] for p in picks]) if picks else np.zeros((0, 2))
    pn = [{norm(p['a']), norm(p['b'])} for p in picks]
    n_on = n_real = n_cov = 0; todo = []
    for c, qq, o in zip(cand, q, on):
        if not o: continue
        n_on += 1
        why = L.excluded(*c)
        if why and why.startswith('realigned'):
            n_real += 1; continue
        on_names = {stem(base(key(s))) for s in c[2]}
        d = np.hypot(*(P - c[:2]).T) if len(P) else np.zeros(0)
        cov = [i for i in np.where(d < 45)[0] if pn[i] <= on_names]
        if cov:
            n_cov += 1; continue
        near = [dict(names=f"{picks[i]['a']} / {picks[i]['b']}", m=round(float(d[i]), 1)) for i in np.where(d < 15)[0]]
        todo.append((c, qq, near))
    info[pid] = dict(on_plate=n_on, realigned=n_real, covered=n_cov, jobs=len(todo), picks=len(picks))
    print(pid, info[pid], flush=True)
    rgb = im[:, :, ::-1]
    for k, (c, qq, near) in enumerate(todo):
        j = f"{pid[3:]}_{k:03d}"
        R = 900; cx, cy = qq
        box = [max(0, int(cx - R)), max(0, int(cy - R)), min(w, int(cx + R)), min(h, int(cy + R))]
        crop = rgb[box[1]:box[3], box[0]:box[2]]
        mk = mask[box[1]:box[3], box[0]:box[2]]
        crop = np.where(mk[..., None], crop, 255).astype(np.uint8)
        Image.fromarray(crop).save(f'{HERE}/regions/{j}.jpg', quality=93)
        jobs[j] = dict(plate=pid, osm=[round(c[0], 2), round(c[1], 2)], osm_names=list(c[2]), predicted=[round(float(cx), 1), round(float(cy), 1)],
                       box=box, size=[w, h], renamed=bool(L.excluded(*c)), picks_within_15m=near)
    del im, rgb, mt
json.dump(jobs, open(HERE + '/jobs.json', 'w', encoding='utf8', newline='\n'), indent=1)
json.dump(info, open(HERE + '/info.json', 'w', encoding='utf8', newline='\n'), indent=1)
print('jobs', len(jobs), {k: sum(v['jobs'] for v in info.values()) for k in ['x']})
