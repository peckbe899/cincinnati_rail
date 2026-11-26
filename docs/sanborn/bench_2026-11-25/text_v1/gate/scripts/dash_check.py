"""Gate check (26 Nov 2026): text pieces that look like dashes lying along Ben's tracks (44 and 5; rail_ben.json read only).
A text piece (8-connected, mask codes 2,3; v1 2,3,4) with any pixel within 12 px of a Ben streetcar track or 14 px of a
railroad track counts as dash-like when it is 18 px long or more, at most 6 px thick (second moments) and within 20 deg
of the track's direction there. Writes gate/out/dash_check.json and a contact sheet gate/pics/dash_<m>_<N>.jpg (scan | mask).
    cd data/sanborn; python -B .../dash_check.py"""
import json, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
Image.MAX_IMAGE_PIXELS = None
B = 'bench_2026-11-25/'
M = {'v1': (B + 'text/finder/out/{N}_finder.png', (2, 3, 4)), 'v2': (B + 'text_v1/finder2/out/final/{N}_text.png', (2, 3)),
     'v3': (B + 'text_v1/classifier/out/finder3/{N}_text.png', (2, 3))}
out = {}
for N in ('44', '5'):
    ben = json.load(open(f'picks22_guided/22-{N}/rail_ben.json'))['tracks']
    scan = Image.open(f'cufp/22-{N}.jpg')
    for m, (pat, codes) in M.items():
        c = np.array(Image.open(pat.format(N=N))); H, W = c.shape; tx = np.isin(c, codes)
        res = []
        for kind, tol in (('streetcar', 12), ('railroad', 14)):
            im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
            for t in ben:
                if t['kind'] == kind: d.line([tuple(p) for p in t['pts']], fill=1, width=1)
            lm = np.array(im) > 0
            dist, ind = ndi.distance_transform_edt(~lm, return_indices=True)
            band = dist <= tol
            lb, n = ndi.label(tx, structure=np.ones((3, 3)))
            hit = np.unique(lb[band & tx]); hit = hit[hit > 0]
            sl = ndi.find_objects(lb)
            for i in hit:
                s = sl[i - 1]; yy, xx = np.nonzero(lb[s] == i); yy = yy + s[0].start; xx = xx + s[1].start
                if len(yy) < 15: continue
                cy, cx = yy.mean(), xx.mean(); C = np.cov(np.c_[xx - cx, yy - cy].T); ev, evec = np.linalg.eigh(C)
                L = 4 * np.sqrt(max(ev[1], 0)); T = 4 * np.sqrt(max(ev[0], 0)); ang = np.degrees(np.arctan2(evec[1, 1], evec[0, 1]))
                # track direction near the piece: from the nearest line pixels' spread
                py, px = int(round(cy)), int(round(cx)); ny, nx = ind[0][py, px], ind[1][py, px]
                win = lm[max(0, ny - 25):ny + 26, max(0, nx - 25):nx + 26]; wy, wx = np.nonzero(win)
                if len(wy) < 3: continue
                Cw = np.cov(np.c_[wx - wx.mean(), wy - wy.mean()].T); e2, v2 = np.linalg.eigh(Cw); ta = np.degrees(np.arctan2(v2[1, 1], v2[0, 1]))
                da = abs((ang - ta + 90) % 180 - 90)
                if L >= 18 and T <= 6 and da <= 20:
                    res.append(dict(kind=kind, x=int(cx), y=int(cy), px=int(len(yy)), length=round(float(L), 1), thick=round(float(T), 1), dang=round(float(da), 1)))
        out[f'{m}_{N}'] = res
        print(m, N, 'dash-like text pieces on Ben tracks:', len(res), 'streetcar', sum(r['kind'] == 'streetcar' for r in res), 'railroad', sum(r['kind'] == 'railroad' for r in res))
        if m == 'v3' and res:
            tiles = []
            for r in res[:60]:
                box = (r['x'] - 45, r['y'] - 45, r['x'] + 45, r['y'] + 45); a = scan.crop(box).convert('RGB')
                cc = np.array(Image.fromarray(c).crop(box)); o = np.full(cc.shape + (3,), 255, np.uint8); o[cc == 1] = (150, 150, 150); o[cc == 5] = (0, 150, 0); o[np.isin(cc, codes)] = (220, 0, 220)
                t = Image.new('RGB', (186, 90), (0, 0, 0)); t.paste(a, (0, 0)); t.paste(Image.fromarray(o), (96, 0)); ImageDraw.Draw(t).text((2, 2), f"{r['kind'][0]} {r['x']},{r['y']}", fill=(255, 0, 0)); tiles.append(t.resize((372, 180), Image.NEAREST))
            cols = 4; rows = (len(tiles) + cols - 1) // cols; sheet = Image.new('RGB', (cols * 378, rows * 186), (0, 0, 0))
            for k, t in enumerate(tiles): sheet.paste(t, ((k % cols) * 378, (k // cols) * 186))
            sheet.save(B + f'text_v1/gate/pics/dash_{m}_{N}.jpg', quality=88)
json.dump(out, open(B + 'text_v1/gate/out/dash_check.json', 'w'), indent=1)
