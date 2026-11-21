"""Pictures to check the scale setting by eye: for each plate, one panel per setting (top to bottom).

    python overlay_plates.py N SETTING[,SETTING...] [--crop x0,y0,x1,y1] [--scale 0.125] [--tag NAME]

Each panel: the scan, P(block) > 0.5 tinted green, P(line) > 0.5 in red, and the sides the outline step exported
(qa/SETTING/N/N_edges.json: green = on print, orange = not settled) drawn in dark green / orange. The setting's name is
written in the corner. --crop is in full-size px (default: the whole plate). Writes overlays/N_TAG.jpg.
"""
import json, os, sys
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
a = sys.argv[1:]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
n, settings = a[0], a[1].split(','); sc = float(opt('--scale', 0.125)); crop = opt('--crop', None); tag = opt('--tag', '_'.join(settings))
full = cv2.imread(SP + f'cufp/22-{n}.jpg'); H, W = full.shape[:2]
x0, y0, x1, y1 = [int(v) for v in crop.split(',')] if crop else (0, 0, W, H)
base = cv2.resize(full[y0:y1, x0:x1], None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA); h, w = base.shape[:2]
panels = []
for s in settings:
    am, lm = (U + f'{n}_pred_area_ng1.png', U + f'{n}_lines_lines_ng1.png') if s == 'batch' else (HERE + f'maps_plates/{s}/{n}_area.png', HERE + f'maps_plates/{s}/{n}_lines.png')
    pa = cv2.resize(cv2.imread(am, 0), (W, H), interpolation=cv2.INTER_LINEAR)[y0:y1, x0:x1]; pl = cv2.imread(lm, 0)[y0:y1, x0:x1]
    pa = cv2.resize(pa, (w, h), interpolation=cv2.INTER_LINEAR) > 127
    pl = cv2.resize(pl, (w, h), interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_LINEAR) > (60 if sc < 0.3 else 127)
    v = base.astype(np.float32) * 0.75 + 60
    v[pa] = v[pa] * 0.7 + np.array([60, 200, 60], np.float32) * 0.3
    v[pl] = (40, 40, 230)
    v = v.clip(0, 255).astype(np.uint8)
    ef = HERE + f'qa/{s}/{n}/{n}_edges.json'
    for e in (json.load(open(ef, encoding='utf8')) if os.path.exists(ef) else []):
        p = lambda q: (int(round((q[0] - x0) * sc)), int(round((q[1] - y0) * sc)))
        cv2.line(v, p(e['a']), p(e['b']), (0, 110, 0) if e['state'] == 'green' else (0, 140, 255), max(1, int(round(3 * sc / 0.25))), cv2.LINE_AA)
    cv2.rectangle(v, (0, 0), (min(w, 16 + 13 * len(s)), 26), (255, 255, 255), -1)
    cv2.putText(v, s, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2, cv2.LINE_AA)
    panels.append(v); panels.append(np.full((6, w, 3), 255, np.uint8))
os.makedirs(HERE + 'overlays', exist_ok=True)
cv2.imwrite(HERE + f'overlays/{n}_{tag}.jpg', np.vstack(panels[:-1]), [cv2.IMWRITE_JPEG_QUALITY, 88]); print(HERE + f'overlays/{n}_{tag}.jpg')
