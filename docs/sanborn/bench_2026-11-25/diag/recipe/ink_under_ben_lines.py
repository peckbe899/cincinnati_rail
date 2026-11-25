"""How much of Ben's lines, by kind (printed / drawn / sheet_edge), lie on printed ink, on 1A (the map plate trained in
V1/V2) and on 44 (the benchmark), with outlines.py's own ink test (on_ink: the black/grey ink image, blurred 3x3; a
piece is on ink when the line is darker than the paper 3 and 6 px either side by more than 25 grey levels, for some
shift of -2..2 px). Lines are cut into 60 px pieces. Also: how much of 1A's taught street ground lies nearer a
sheet-edge line than any other of his lines, and the street share of taught ground near the paper edge on every
labelled plate (the 21 Nov labels) against 1A. Reads only; system python."""
import json, numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; OUT = SP + 'bench_2026-11-25/diag/recipe/'
def ink_gray(full):
    hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170))
    return cv2.GaussianBlur(np.where(ink, cv2.cvtColor(full, cv2.COLOR_BGR2GRAY), 255).astype(np.uint8), (3, 3), 0).astype(np.float32)
def along(img, a, b, o=0.0):
    H, W = img.shape; d = b - a; L = np.hypot(*d); nrm = np.array([-d[1], d[0]]) / (L or 1); t = np.linspace(0.06, 0.94, max(10, int(L))); q = a + np.outer(t, d) + nrm * o
    x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1); return img[y, x]
def on_ink(g, a, b):
    d = b - a; nrm = np.array([-d[1], d[0]]) / np.hypot(*d)
    return bool(max(np.mean([along(g, a + nrm * s, b + nrm * s, o).mean() for o in (-6, -3, 3, 6)]) - along(g, a + nrm * s, b + nrm * s).mean() for s in (-2, -1, 0, 1, 2)) > 25)
res = {}
for plate, smf in [('1A', SP + 'train_v2/1A/streetmap.json'), ('44', SP + 'streetmap/22-44.json')]:
    T = json.load(open(smf, encoding='utf8')); g = ink_gray(cv2.imread(SP + f'cufp/22-{plate}.jpg')); r = {}
    for l in T['lines']:
        a, b = np.array(l['a'], float), np.array(l['b'], float); L = float(np.hypot(*(b - a))); n = max(1, int(round(L / 60)))
        k = r.setdefault(l['kind'], dict(lines=0, length=0.0, on_ink_length=0.0))
        k['lines'] += 1; k['length'] += L
        for i in range(n):
            p, q = a + (b - a) * i / n, a + (b - a) * (i + 1) / n
            if np.hypot(*(q - p)) >= 8 and on_ink(g, p, q): k['on_ink_length'] += float(np.hypot(*(q - p)))
    for k in r.values(): k['on_ink_share'] = round(k['on_ink_length'] / max(1, k['length']), 3); k['length'] = round(k['length']); k['on_ink_length'] = round(k['on_ink_length'])
    res[plate] = r; print(plate, json.dumps(r), flush=True)
# 1A street ground nearest a sheet-edge line
T = json.load(open(SP + 'train_v2/1A/streetmap.json', encoding='utf8')); lab = cv2.imread(SP + 'train_v2/1A/label.png', 0); vm = cv2.imread(SP + 'train_v2/1A/valmask.png', 0) > 0; h, w = lab.shape
rs = {}
for kind in ('sheet_edge', 'other'):
    m = np.full((h, w), 255, np.uint8)
    for l in T['lines']:
        if (l['kind'] == 'sheet_edge') == (kind == 'sheet_edge'): cv2.line(m, tuple((np.array(l['a']) / 2).round().astype(int)), tuple((np.array(l['b']) / 2).round().astype(int)), 0, 1)
    rs[kind] = cv2.distanceTransform(m, cv2.DIST_L2, 5)
st = lab == 0; near_se = rs['sheet_edge'] < rs['other']
res['1A_street_nearest_sheet_edge'] = dict(street_px=int(st.sum()), nearest_sheet_edge_px=int((st & near_se).sum()), share=round(float((st & near_se).sum() / st.sum()), 4),
                                         train_part=dict(street_px=int((st & ~vm).sum()), nearest_sheet_edge_px=int((st & near_se & ~vm).sum())),
                                         block_px_within_30_of_sheet_edge_line=int(((lab == 1) & (rs['sheet_edge'] < 30)).sum()))
# street share near the paper edge, labelled plates (21 Nov labels) and 1A
pe = {}
for p in ['43', '45', '80', '82A', '1A', '44']:
    lab = cv2.imread(SP + (f'train_v2/{p}/label.png' if p != '44' else 'unet_data/44_label.png'), 0); h, w = lab.shape
    al = cv2.resize(np.load(SP + f'cufp/{p}/png_alpha_s4.npy').astype(np.float32), (w, h)) > 0.5
    d = cv2.distanceTransform(al.astype(np.uint8), cv2.DIST_L2, 5); e = al & (d < 60)
    pe[p] = dict(edge60_street=round(float((lab[e] == 0).mean()), 3), edge60_block=round(float((lab[e] == 1).mean()), 3), edge60_untaught=round(float((lab[e] == 255).mean()), 3),
                 paper_street=round(float((lab[al] == 0).mean()), 3), paper_block=round(float((lab[al] == 1).mean()), 3), paper_untaught=round(float((lab[al] == 255).mean()), 3),
                 taught_street_share=round(float((lab[al] == 0).sum() / max(1, (lab[al] != 255).sum())), 3))
res['paper_edge_labels'] = pe; print(json.dumps(res['1A_street_nearest_sheet_edge'])); print(json.dumps(pe, indent=0))
json.dump(res, open(OUT + 'ink_under_ben_lines.json', 'w'), indent=1)
