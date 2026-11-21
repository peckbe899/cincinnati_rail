"""Share of Ben's checked street-side lines (streetmap/22-44.json) that each line map draws within 4 px. Read-only."""
import json, sys
import numpy as np, cv2
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
sm = json.load(open(D + 'streetmap/22-44.json', encoding='utf8'))
print('line record example', json.dumps(sm['lines'][0])[:300])
maps = {'lines_v2': cv2.imread(D + 'unet_data/44_lines_lines_v2.png', 0), 'lines_ng1 (cpu rerun)': cv2.imread(sys.argv[1], 0)}
H, W = maps['lines_v2'].shape
ben = np.zeros((H, W), np.uint8)
for l in sm['lines']:
    pts = l.get('pts') or l.get('points') or ([l['a'], l['b']] if 'a' in l else None)
    if pts is None: continue
    cv2.polylines(ben, [np.round(np.array(pts)).astype(np.int32)], False, 1, 1)
print('Ben line px', int(ben.sum()))
for nm, m in maps.items():
    near = cv2.dilate((m > 127).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    print(nm, 'drawn share', round(float((m > 127).mean()), 4), 'recall of Ben lines within 4 px', round(float(near[ben > 0].mean()), 3))
