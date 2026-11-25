"""Measure the lettering: every word of the hand-checked truth crops (truth/T*_words.json + T*_mask.png) and every
example of catalogue.txt (placed by eye, snapped by the build_truth rules). Writes
  measure/words_truth.csv, measure/words_catalogue.csv   one row per word
  measure/summary.json, measure/summary.md               medians by kind and scale (ft per inch)
  crops/<plate>/<nn>_<kind>.png and crops/sheet_<plate>.jpg   1:1 crops of the catalogue examples, contact sheets
python -B measure.py

Measures (wordpix.glyph_stats), all in full-size scan px:
  glyph_h      median height across the reading direction of the word's glyph pieces (8-connected text ink, >= 12 px,
               at least 0.55 x the 90th percentile height, so periods, primes and ditto marks drop out). For digits
               and capitals this is the cap height; a glyph split in two by the ink threshold counts as two pieces.
  stroke_w     2 x median distance-transform value on its ridge (local maxima, the stroke centre line) - 1: the stroke width.
  touches_line the word's text ink is 8-connected to ink of a straight line that runs out of the word box
               (truth words: the same flag from build_truth.py).
  glyphs_touching_line  share of glyph pieces joined to such line ink.
  comps_per_char  glyph pieces / letters+digits in the reading: below 1 means glyphs joined to each other (or a line),
               above 1 means glyphs broken by the ink threshold.
  L, a, b      median CIE Lab of the text pixels (L 0-100); *_core the same on stroke centres (1 px eroded).
  orient       horizontal (within 10 deg), vertical (80-100 deg either way), oblique; curved from the annotation."""
import os, sys, json, math, csv
import numpy as np, cv2
from common import INV, ROOT, window, plate_img, jdump
from wordpix import word_pixels, glyph_stats

SCALE = {k: v['ft_per_inch'] for k, v in json.load(open(os.path.join(ROOT, 'scale_table.json'))).items()}
OUT = os.path.join(INV, 'measure'); CR = os.path.join(INV, 'crops'); os.makedirs(OUT, exist_ok=True); os.makedirs(CR, exist_ok=True)


def orient(ang, flags):
    if 'curved' in flags: return 'curved'
    a = abs(((ang + 180) % 360) - 180)
    if a <= 10 or a >= 170: return 'horizontal'
    if 80 <= a <= 100: return 'vertical'
    return 'oblique'


def parse_catalogue():
    rows = []
    for k, raw in enumerate(open(os.path.join(INV, 'catalogue.txt'), encoding='utf8')):
        s = raw.strip()
        if not s or s.startswith('#'): continue
        f = [q.strip() for q in s.split('|')]
        rows.append(dict(plate=f[0], geo=[float(v) for v in f[1].split()], reading=f[2], kind=f[3], flags=f[4].split() if len(f) > 4 else [], note=f[4] if len(f) > 4 else '', line=k + 1))
    return rows


def catalogue():
    res = []; per_plate = {}
    import re
    for d_ in os.listdir(CR):   # this script's own crops from an earlier run (nn_kind.png), so renumbered examples leave no strays
        if os.path.isdir(os.path.join(CR, d_)):
            for f_ in os.listdir(os.path.join(CR, d_)):
                if re.fullmatch(r'\d\d_[a-z]+\.png', f_): os.remove(os.path.join(CR, d_, f_))
    for i, r in enumerate(parse_catalogue()):
        x1, y1, x2, y2, h = r['geo']; L = math.hypot(x2 - x1, y2 - y1); P = int(L / 2 + 3 * h + 120)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        img, lab, ink, (wx0, wy0, wx1, wy1) = window(r['plate'], int(cx - P), int(cy - P), int(cx + P), int(cy + P))
        w = word_pixels(ink, (wx0, wy0), r['geo'], r['flags'])
        bx0, by0, bx1, by1 = w['sub']
        st = glyph_stats(w['text'], w['line'], w['cx'], w['cy'], w['ang'], r['reading'], lab[by0:by1, bx0:bx1])
        pcx, pcy, pL, ph, pang = w['plate_box']
        rec = dict(src='catalogue', plate=r['plate'], ft_per_inch=SCALE.get(r['plate']), kind=r['kind'], reading=r['reading'], angle=round(pang, 1),
                   orient=orient(pang, r['flags']), box_h=round(ph, 1), box_len=round(pL, 1), cx=round(pcx), cy=round(pcy), snapped=w['snapped'],
                   flags=' '.join(r['flags']), **st)
        res.append(rec)
        # crop for the contact sheet: the word with 30 px round it, box outline, and the text pixels beside it in red
        poly = cv2.boxPoints(((pcx, pcy), (pL, ph), pang))
        q0 = np.floor(poly.min(0)).astype(int) - 30; q1 = np.ceil(poly.max(0)).astype(int) + 30
        H, W = plate_img(r['plate']).shape[:2]; q0 = np.maximum(q0, 0); q1 = np.minimum(q1, [W, H])
        c = plate_img(r['plate'])[q0[1]:q1[1], q0[0]:q1[0]].copy()
        tm = np.zeros(c.shape[:2], bool)
        ty, tx = np.nonzero(w['text']); ty = ty + by0 + wy0 - q0[1]; tx = tx + bx0 + wx0 - q0[0]
        ok = (ty >= 0) & (ty < c.shape[0]) & (tx >= 0) & (tx < c.shape[1]); tm[ty[ok], tx[ok]] = True
        o = c.copy(); cv2.polylines(o, [np.round(poly - q0).astype(np.int32)], True, (255, 0, 200), 1)
        m = (c * 0.25 + 190).astype(np.uint8); m[tm] = (0, 0, 220)
        d = os.path.join(CR, r['plate']); os.makedirs(d, exist_ok=True)
        nm = f'{len(per_plate.get(r["plate"], [])) + 1:02d}_{r["kind"]}'
        cv2.imwrite(os.path.join(d, nm + '.png'), c)
        per_plate.setdefault(r['plate'], []).append((nm, np.hstack([o, m]) if c.shape[1] <= c.shape[0] * 2.5 else np.vstack([o, m]), rec))
    for p, items in per_plate.items():
        tiles = []
        for nm, t, rec in items:
            s = min(1.0, 380 / t.shape[1], 300 / t.shape[0]); t = cv2.resize(t, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            lab_ = f"{nm} {rec['reading'][:22]} h{rec.get('glyph_h', 0):.0f} sw{rec.get('stroke_w', 0):.1f}"
            card = np.full((max(t.shape[0], 1) + 18, 390, 3), 255, np.uint8); card[18:18 + t.shape[0], :t.shape[1]] = t
            cv2.putText(card, lab_, (2, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1); tiles.append(card)
        rows = []; row = []; rw = 0
        for t in tiles:
            if rw + t.shape[1] > 1600 and row: rows.append(row); row = []; rw = 0
            row.append(t); rw += t.shape[1]
        if row: rows.append(row)
        imgs = []
        for row in rows:
            hmax = max(t.shape[0] for t in row)
            imgs.append(np.hstack([cv2.copyMakeBorder(t, 0, hmax - t.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in row]))
        wmax = max(i.shape[1] for i in imgs)
        sheet = np.vstack([cv2.copyMakeBorder(i, 0, 4, 0, wmax - i.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for i in imgs])
        cv2.imwrite(os.path.join(CR, f'sheet_{p}.jpg'), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return res


def truth():
    res = []
    crops = json.load(open(os.path.join(INV, 'truth', 'crops.json')))
    for tid, c in crops.items():
        p = c['plate']; X0, Y0, X1, Y1 = c['win']
        M = cv2.imread(os.path.join(INV, 'truth', f'{tid}_mask.png'), 0)
        img = plate_img(p)[Y0:Y1, X0:X1]; lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        W = json.load(open(os.path.join(INV, 'truth', f'{tid}_words.json'), encoding='utf8'))
        for w in W['words']:
            poly = np.array(w['poly']) - [X0, Y0]
            x0, y0 = np.floor(poly.min(0)).astype(int) - 6; x1, y1 = np.ceil(poly.max(0)).astype(int) + 6
            x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(X1 - X0, x1), min(Y1 - Y0, y1)
            if x1 - x0 < 3 or y1 - y0 < 3: continue
            pm = np.zeros((y1 - y0, x1 - x0), np.uint8); cv2.fillPoly(pm, [np.round(poly - [x0, y0]).astype(np.int32)], 1)
            pm = cv2.dilate(pm, np.ones((5, 5), np.uint8)) > 0
            m = M[y0:y1, x0:x1]; text = (m == 2) & pm
            line = ((m == 1) | (m == 3)) & ~text
            cx_, cy_ = poly.mean(0) - [x0, y0]
            st = glyph_stats(text, line, cx_, cy_, w['angle'], w['reading'].replace(' ', '') if 'run' not in w['flags'] else w['reading'].split()[0], lab[y0:y1, x0:x1])
            st['touches_line'] = w['touches_line']   # the build's own flag (line ink running out of the box)
            inside = (cx_ + x0 >= 0)
            res.append(dict(src='truth', crop=tid, plate=p, ft_per_inch=SCALE.get(p), kind=w['kind'], reading=w['reading'], angle=w['angle'],
                            orient=orient(w['angle'], w['flags']), box_h=w['height'], box_len=w['length'], cx=round(float(np.mean(np.array(w['poly'])[:, 0]))),
                            cy=round(float(np.mean(np.array(w['poly'])[:, 1]))), snapped=w['snapped'], flags=' '.join(w['flags']), **st))
    return res


def summarise(rows):
    def med(v): v = [x for x in v if x is not None and not (isinstance(x, float) and math.isnan(x))]; return round(float(np.median(v)), 1) if v else None
    def q(v, p): v = [x for x in v if x is not None]; return round(float(np.percentile(v, p)), 1) if v else None
    groups = {}
    for r in rows:
        if r.get('text_px', 0) < 10: continue
        if 'partial' in r['flags'].split(): continue
        groups.setdefault((r['kind'], r['ft_per_inch']), []).append(r)
    out = []
    for (k, s), g in sorted(groups.items(), key=lambda t: (t[0][0], t[0][1] or 0)):
        single = [r for r in g if 'run' not in r['flags'].split()]
        gh = [r.get('glyph_h') for r in single if r.get('glyph_h')]
        o = {}
        for r in g: o[r['orient']] = o.get(r['orient'], 0) + 1
        out.append(dict(kind=k, ft_per_inch=s, n=len(g), plates=sorted({r['plate'] for r in g}),
                        glyph_h_med=med(gh), glyph_h_p10=q(gh, 10), glyph_h_p90=q(gh, 90),
                        stroke_w_med=med([r.get('stroke_w') for r in g]), stroke_w_p10=q([r.get('stroke_w') for r in g if r.get('stroke_w')], 10), stroke_w_p90=q([r.get('stroke_w') for r in g if r.get('stroke_w')], 90),
                        touches_line_share=round(float(np.mean([bool(r.get('touches_line')) for r in g])), 2),
                        glyphs_touching_line_share=med([r.get('glyphs_touching_line') for r in g]),
                        comps_per_char_med=med([r.get('comps_per_char') for r in single]),
                        merged_share=round(float(np.mean([r.get('comps_per_char', 1) < 1 for r in single])), 2) if single else None,
                        L=med([r.get('L') for r in g]), a=med([r.get('a') for r in g]), b=med([r.get('b') for r in g]),
                        L_core=med([r.get('L_core') for r in g]), a_core=med([r.get('a_core') for r in g]), b_core=med([r.get('b_core') for r in g]),
                        orient=o))
    return out


if __name__ == '__main__':
    t = truth(); c = catalogue()
    keys = ['src', 'crop', 'plate', 'ft_per_inch', 'kind', 'reading', 'angle', 'orient', 'box_h', 'box_len', 'cx', 'cy', 'snapped', 'flags', 'text_px', 'glyph_h', 'glyph_w',
            'n_glyph_comps', 'n_chars', 'comps_per_char', 'stroke_w', 'touches_line', 'glyphs_touching_line', 'L', 'a', 'b', 'L_core', 'a_core', 'b_core']
    for name, rows in (('words_truth.csv', t), ('words_catalogue.csv', c)):
        with open(os.path.join(OUT, name), 'w', newline='', encoding='utf8') as f:
            wr = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore'); wr.writeheader(); [wr.writerow(r) for r in rows]
    S = summarise(t + c)
    jdump(dict(note='medians by kind and scale; truth words (6 crops, 100 ft) + catalogue examples; partial words left out; glyph_h from single words, not runs. Made by measure.py', rows=S), os.path.join(OUT, 'summary.json'))
    with open(os.path.join(OUT, 'summary.md'), 'w', encoding='utf8') as f:
        f.write('| kind | ft/in | n | glyph h med (p10-p90) | stroke w med (p10-p90) | touches line | glyphs on line | pieces/char | merged | L a b (core) | orientation |\n|---|---|---|---|---|---|---|---|---|---|---|\n')
        for r in S:
            f.write(f"| {r['kind']} | {r['ft_per_inch']} | {r['n']} | {r['glyph_h_med']} ({r['glyph_h_p10']}-{r['glyph_h_p90']}) | {r['stroke_w_med']} ({r['stroke_w_p10']}-{r['stroke_w_p90']}) | {r['touches_line_share']} | {r['glyphs_touching_line_share']} | {r['comps_per_char_med']} | {r['merged_share']} | {r['L_core']} {r['a_core']} {r['b_core']} | {', '.join(f'{k} {v}' for k, v in sorted(r['orient'].items()))} |\n")
    print(open(os.path.join(OUT, 'summary.md'), encoding='utf8').read())
