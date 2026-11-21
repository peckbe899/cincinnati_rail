"""Census, rail: how much of the rules' rail lies inside the printed KEY box (its RAILROAD and TROLLEY samples) (21 Nov 2026).

The KEY header '-KEY-' is cut from plate 21 (cufp/22-21.jpg, full px x 9600-10070, y 950-1050) and matched at quarter
size; where it matches (score >= 0.6) the KEY box is taken as header x -220..+610, y -60..+1320 full px (plate 21's box).
Inside it: railroad (bin 4) and streetcar (bin 5) px of N_bins.png, and rule tracks (N_rail_rule.json) with their middle
point inside. Read-only.
    python rail_key.py   -> rail_key.json
"""
import json, os, re
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = D + 'unet_data/'
t = cv2.cvtColor(cv2.imread(D + 'cufp/22-21.jpg', cv2.IMREAD_REDUCED_COLOR_4), cv2.COLOR_BGR2GRAY)[950 // 4:1050 // 4, 9600 // 4:10070 // 4]


def order(n): m = re.match(r'(\d+)(.*)', n); return int(m.group(1)), m.group(2)


if __name__ == '__main__':
    C = {r['plate']: r for r in json.load(open(HERE + '/census_base.json'))}; out = {}
    for n in sorted(C, key=order):
        g = cv2.cvtColor(cv2.imread(D + f'cufp/22-{n}.jpg', cv2.IMREAD_REDUCED_COLOR_4), cv2.COLOR_BGR2GRAY)
        best = (0, None, None)
        for s in (0.85, 1.0, 1.15):
            tt = cv2.resize(t, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            if tt.shape[0] >= g.shape[0] or tt.shape[1] >= g.shape[1]: continue
            r = cv2.matchTemplate(g, tt, cv2.TM_CCOEFF_NORMED); _, v, _, p = cv2.minMaxLoc(r)
            if v > best[0]: best = (float(v), (p[0] * 4, p[1] * 4), s)
        rec = dict(key_score=round(best[0], 3), source=C[n]['source'])
        if best[0] >= 0.6:
            (x, y), s = best[1], best[2]
            x0, x1, y0, y1 = int(x - 220 * s), int(x + 610 * s), int(y - 60 * s), int(y + 1320 * s)
            b = cv2.imread(U + f'{n}_bins.png', cv2.IMREAD_GRAYSCALE)
            box = b[max(0, y0):y1, max(0, x0):x1]
            rr = json.load(open(U + f'{n}_rail_rule.json', encoding='utf8'))['tracks']
            inside = [tr for tr in rr if len(tr['pts']) and x0 <= np.mean([p[0] for p in tr['pts']]) <= x1 and y0 <= np.mean([p[1] for p in tr['pts']]) <= y1]
            rec.update(key_box=[x0, y0, x1, y1], railroad_px_in_key=int((box == 4).sum()), streetcar_px_in_key=int((box == 5).sum()),
                       rule_tracks_in_key=len(inside), rule_railroad_tracks_in_key=sum(tr['kind'] == 'railroad' for tr in inside),
                       railroad_px=C[n]['railroad_px'], streetcar_px=C[n]['streetcar_px'])
        out[n] = rec
        print(n, rec, flush=True)
    json.dump(out, open(HERE + '/rail_key.json', 'w'), indent=1)
    k = [v for v in out.values() if 'key_box' in v]
    print('KEY found on', len(k), 'plates (', sum(v['source'] == 'pdf sheet' for v in k), 'pdf sheets ); rule tracks inside a KEY:', sum(v['rule_tracks_in_key'] for v in k),
          'on', sum(v['rule_tracks_in_key'] > 0 for v in k), 'plates; railroad px in KEYs', sum(v['railroad_px_in_key'] for v in k), 'streetcar px', sum(v['streetcar_px_in_key'] for v in k))
