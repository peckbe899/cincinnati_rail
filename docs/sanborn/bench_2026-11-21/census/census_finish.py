"""Census step 1e: add scale, ground area and a few geometric indicators to census_raw.json; write census_base.json (classify.py adds the verdict columns and writes census.csv / census.json).

    tools/sanborn/unet/.venv/Scripts/python.exe census_finish.py   -> census_base.json   (the venv: its OpenCV has ximgproc.thinning)

Added per plate:
  ft_per_inch, scale_status, inset, measured_ft_per_inch   from scale/scale_table.json (scale_table.py)
  px_per_ft (300 / ft_per_inch), ground_acres (paper px / px_per_ft^2), blocks_per_100_acres, editor_ft_per_acre
  training_scale     '100 (as 43, 44)', '200 (as 45, 80, 82A)' or '400 (none)'
  line_skel_len_px   length of the line network's lines (P(line) > 0.5 at half size, thinned, x2), at least 15 px
                     inside the paper edge
  editor_per_line    editor_len_px / line_skel_len_px: how much of the line length the line network drew reaches the
                     line editor (both count each block side once)
  outline_kept_share editor_len_px / length of every side of every exported polygon (what step 4 keeps of the outlines)
  edge_lines         editor lines whose middle lies within 150 full px of the paper's edge (on a PDF sheet the paper's
                     edge is the scanner bed or the sheet margin, never a street); edge_lines_share of all editor lines
  rail_tracks_edge   rule tracks with any point within 400 full px of the paper's edge
"""
import json, os, re, csv
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__))
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = D + 'unet_data/'
GUIDED = {'43', '44', '45', '80', '82A'}


def order(n): m = re.match(r'(\d+)(.*)', n); return int(m.group(1)), m.group(2)


def geom(n, r):
    al = np.load(D + f'cufp/{n}/png_alpha_s4.npy').astype(np.uint8)
    pl = cv2.imread(U + f'{n}_lines_lines_ng1.png', 0); H, W = pl.shape
    half = cv2.resize(pl, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    mh = cv2.resize(al, (W // 2, H // 2), interpolation=cv2.INTER_NEAREST)
    inner = cv2.erode(mh, np.ones((15, 15), np.uint8)) > 0
    sk = cv2.ximgproc.thinning(((half > 110) & inner).astype(np.uint8) * 255) > 0
    out = dict(line_skel_len_px=int(sk.sum()) * 2)
    dist = cv2.distanceTransform(cv2.copyMakeBorder(al, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0), cv2.DIST_L2, 5)[1:-1, 1:-1] * 4   # full px to the paper's edge
    if n in GUIDED:
        polys = json.load(open(HERE + f'/guided_ol/{n}_outlines_poly.json', encoding='utf8'))
        edges = [dict(a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange') for p in polys for s in p if not (s['state'] == 'short' or s.get('paper_edge'))]
    else:
        polys = json.load(open(D + f'picks22_guided/22-{n}/outlines.json', encoding='utf8')); edges = json.load(open(U + f'{n}_edges.json', encoding='utf8'))
    L = lambda a, b: float(np.hypot(b[0] - a[0], b[1] - a[1]))
    allen = sum(L(s['a'], s['b']) for p in polys for s in p)
    out['outline_len_px'] = round(allen); out['outline_kept_share'] = round(r['editor_len_px'] / allen, 3) if allen else None
    def d_at(x, y):
        yi = int(np.clip(y / 4, 0, dist.shape[0] - 1)); xi = int(np.clip(x / 4, 0, dist.shape[1] - 1)); return float(dist[yi, xi])
    e_near = [e for e in edges if d_at((e['a'][0] + e['b'][0]) / 2, (e['a'][1] + e['b'][1]) / 2) < 150]
    out['edge_lines'] = len(e_near); out['edge_lines_share'] = round(len(e_near) / len(edges), 3) if edges else None
    rr = json.load(open(U + f'{n}_rail_rule.json', encoding='utf8'))['tracks']
    out['rail_tracks_edge'] = sum(any(d_at(x, y) < 400 for x, y in t['pts']) for t in rr)
    return out


if __name__ == '__main__':
    raw = json.load(open(HERE + '/census_raw.json')); sc = json.load(open(HERE + '/scale/scale_table.json'))
    rows = []
    for n in sorted(raw, key=order):
        r = dict(raw[n]); s = sc[n]
        r['ft_per_inch'] = s['ft_per_inch']; r['scale_status'] = s['status']; r['scale_inset'] = s['inset']; r['measured_ft_per_inch'] = s['measured_ft_per_inch']
        r['training_scale'] = {100: 'yes: 100 ft (43; 44 held out)', 200: 'yes: 200 ft (45, 80, 82A)', 400: 'no: nothing at 400 ft'}[s['ft_per_inch']]
        ppf = 300.0 / s['ft_per_inch']; r['px_per_ft'] = round(ppf, 3)
        acres = r['paper_mpx'] * 1e6 / ppf ** 2 / 43560; r['ground_acres'] = round(acres, 1)
        r['blocks_per_100_acres'] = round(r['blocks_exported'] / acres * 100, 2); r['editor_ft_per_acre'] = round(r['editor_len_px'] / ppf / acres, 1)
        r.update(geom(n, r))
        r['editor_per_line'] = round(r['editor_len_px'] / r['line_skel_len_px'], 3) if r['line_skel_len_px'] else None
        rows.append(r); print(n, r['ft_per_inch'], r['ground_acres'], r['editor_per_line'], r['outline_kept_share'], r['edge_lines'], r['rail_tracks_edge'], flush=True)
    json.dump(rows, open(HERE + '/census_base.json', 'w'), indent=1)
