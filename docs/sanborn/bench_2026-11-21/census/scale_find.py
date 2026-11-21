"""Census step 1b: find the printed 'SCALE ... FT. TO AN INCH' note on the whole sheet of every batch plate (21 Nov 2026).

Cut plates (22-N.jpg from New Sanborn/PNG) are cut to the map and have no margin, so the note is read on the uncut
sheet: the one JPEG inside Sanborn/Maps[/TBD]/Sanborn Cincinnati <num>.pdf, the scan the PNG was cut from.
Template matching (the words 'SCALE' and 'TO AN INCH' cut from plate 20's note) at quarter size finds candidates;
each candidate is cropped at half size into scale/notes_<k>.jpg montages, which are then read by eye.
Read-only on everything outside this folder.

    python scale_find.py            -> scale/find.json, scale/notes_*.jpg (best hit per plate), scale/crops/N_k.jpg (every hit), scale/sheet_<N>.jpg (1/8 overviews)
"""
import json, os, re, sys
import numpy as np, cv2, fitz

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'scale'); os.makedirs(OUT, exist_ok=True)
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
MAPS = 'C:/Users/peckb/Documents/CS2/Sanborn/Maps/'
state = json.load(open(D + 'unet_data/run_plates.json', encoding='utf8'))


def pdf_of(n):
    src = D + f'cufp/{n}/source.json'
    if os.path.exists(src): return json.load(open(src, encoding='utf8'))['file']
    m = re.match(r'(\d+)([AB]?)$', n); num, suf = m.group(1), m.group(2)
    cands = []
    if suf: cands.append(f'Sanborn Cincinnati {num}{suf.lower()}.pdf')   # 1a, 1b, 59a have their own sheet
    cands += [f'Sanborn Cincinnati {num}.pdf', f'Sanborn CIncinnati {num}.pdf', f'Sanborn Cincinnati {num}_compressed.pdf']
    for c in cands:
        for d in (MAPS, MAPS + 'TBD/'):
            if os.path.exists(d + c): return d + c
    return None


def sheet(pdf):
    doc = fitz.open(pdf); ims = doc[0].get_images(full=True)
    x = doc.extract_image(ims[0][0])
    full_size = (x['width'], x['height'])
    a = cv2.imdecode(np.frombuffer(x['image'], np.uint8), cv2.IMREAD_REDUCED_COLOR_2)
    return a, full_size, len(doc), len(ims)


# templates from plate 20's note (full-size crop 8700:9800 x 550:780 of cufp/22-20.jpg), taken at quarter size
t20 = cv2.cvtColor(cv2.imread(D + 'cufp/22-20.jpg', cv2.IMREAD_REDUCED_COLOR_4), cv2.COLOR_BGR2GRAY)
ox, oy = 8700 // 4, 550 // 4
TPL = {'SCALE': t20[oy + 50 // 4:oy + 160 // 4, ox + 95 // 4:ox + 350 // 4], 'TO AN INCH': t20[oy + 50 // 4:oy + 160 // 4, ox + 600 // 4:ox + 985 // 4]}

if __name__ == '__main__':
    want = sys.argv[1:] or sorted(state, key=lambda n: (int(re.match(r'\d+', n).group()), n))
    res = json.load(open(OUT + '/find.json')) if os.path.exists(OUT + '/find.json') else {}
    crops = []
    for n in want:
        pdf = pdf_of(n)
        if pdf is None: res[n] = dict(pdf=None); print(n, 'no pdf'); continue
        a, fs, npg, nim = sheet(pdf)
        g = cv2.cvtColor(cv2.resize(a, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)   # quarter size
        cv2.imwrite(OUT + f'/sheet_{n}.jpg', cv2.resize(a, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 80])
        hits = []
        for name, t in TPL.items():
            for s in (0.8, 0.9, 1.0, 1.12, 1.25):
                tt = cv2.resize(t, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
                r = cv2.matchTemplate(g, tt, cv2.TM_CCOEFF_NORMED)
                for _ in range(4):
                    _, v, _, p = cv2.minMaxLoc(r)
                    hits.append((float(v), name, s, p[0] * 4, p[1] * 4, tt.shape[1] * 4, tt.shape[0] * 4))
                    cv2.rectangle(r, (p[0] - tt.shape[1], p[1] - tt.shape[0]), (p[0] + tt.shape[1], p[1] + tt.shape[0]), -1, -1)
        hits.sort(reverse=True); keep = []
        for h in hits:   # distinct places only
            if all(abs(h[3] - k[3]) > 1600 or abs(h[4] - k[4]) > 300 for k in keep): keep.append(h)
            if len(keep) == 3: break
        res[n] = dict(pdf=pdf.replace('\\', '/'), sheet_size=list(fs), pages=npg, images=nim, hits=[dict(score=round(h[0], 3), word=h[1], scale=h[2], x=h[3], y=h[4]) for h in keep])
        for k, h in enumerate(keep):
            x, y = h[3], h[4]
            x0 = x - (200 if h[1] == 'SCALE' else 1300); x1 = x + (1500 if h[1] == 'SCALE' else 700)   # full-size px
            y0, y1 = y - 120, y + 260
            c = a[max(0, y0 // 2):max(0, y1 // 2), max(0, x0 // 2):max(0, x1 // 2)]
            if c.size == 0: continue
            c = cv2.resize(c, (850, int(850 * c.shape[0] / c.shape[1])), interpolation=cv2.INTER_AREA)
            c = cv2.copyMakeBorder(c, 0, 0, 120, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            cv2.putText(c, f'{n}', (4, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 3); cv2.putText(c, f'{k}:{h[0]:.2f}', (4, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
            os.makedirs(OUT + '/crops', exist_ok=True); cv2.imwrite(OUT + f'/crops/{n}_{k}.jpg', c, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if k == 0: crops.append(c)
        print(n, os.path.basename(pdf), fs, [(round(h[0], 2), h[1], h[3], h[4]) for h in keep], flush=True)
    json.dump(res, open(OUT + '/find.json', 'w'), indent=1)
    if crops and len(sys.argv) == 1:
        W = max(c.shape[1] for c in crops)
        crops = [cv2.copyMakeBorder(c, 0, 4, 0, W - c.shape[1], cv2.BORDER_CONSTANT, value=(0, 0, 0)) for c in crops]
        for k in range(0, len(crops), 14):
            cv2.imwrite(OUT + f'/notes_{k // 14:02d}.jpg', np.vstack(crops[k:k + 14]), [cv2.IMWRITE_JPEG_QUALITY, 85])
