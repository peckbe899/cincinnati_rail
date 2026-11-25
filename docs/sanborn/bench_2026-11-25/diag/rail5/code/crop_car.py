"""Full-size crop of plate 5 with Ben's streetcar (yellow), the rule's streetcar tracks (blue: orig, green: proposed)
and the streetcar bin ink (orange) over the scan beside the plain scan. diag/rail5, 25 Nov 2026.
    cd data/sanborn; python -B bench_2026-11-25/diag/rail5/code/crop_car.py X0 Y0 X1 Y1 NAME [RUN]"""
import json, os, sys
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
x0, y0, x1, y1 = map(int, sys.argv[1:5]); name = sys.argv[5]; run = sys.argv[6] if len(sys.argv) > 6 else 'orig_nets'
im = cv2.imread('cufp/22-5.jpg')[y0:y1, x0:x1].copy(); lay = im.copy()
b = cv2.imread(os.path.join(ROOT, 'runs', run + '_bins.png'), 0)[y0:y1, x0:x1]; lay[b == 5] = (0, 140, 255); lay[b == 4] = (0, 0, 230)
for f, col, wd in ((os.path.join(ROOT, 'inputs', 'rail_ben_5_copy.json'), (0, 220, 255), 3), (os.path.join(ROOT, 'runs', run + '_tracks.json'), (255, 100, 0), 2), (os.path.join(ROOT, 'runs', run.replace('orig', 'proposed') + '_tracks.json'), (0, 170, 0), 1)):
    for t in json.load(open(f, encoding='utf8'))['tracks']:
        cv2.polylines(lay, [np.round(np.array(t['pts'], float) - [x0, y0]).astype(np.int32)], False, col, wd)
ov = cv2.addWeighted(im, 0.4, lay, 0.6, 0)
pic = np.vstack([im, np.full((6, im.shape[1], 3), 255, np.uint8), ov]) if im.shape[1] > im.shape[0] * 1.2 else np.hstack([im, np.full((im.shape[0], 6, 3), 255, np.uint8), ov])
cv2.imwrite(os.path.join(ROOT, 'crops', name + '.png'), pic); print(name, pic.shape)
