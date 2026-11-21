"""Anchor the census indicators on plate 44, the one plate with ground truth (21 Nov 2026).

Scores the batch's outline step run on the batch's own 44 maps (census/guided_ol/44_*, made by outlines_copy.py) with
the review's PQ scorer (docs/sanborn/ml_review_2026-11-21/scripts/research-maps_pq44.py, imported, unchanged), so a
healthy-looking census row can be read against what it means on 44.
    python anchor44.py   -> anchor44.json
"""
import json, os, importlib.util
import cv2
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('pq44', 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/docs/sanborn/ml_review_2026-11-21/scripts/research-maps_pq44.py')
pq44 = importlib.util.module_from_spec(spec); spec.loader.exec_module(pq44)
gt, ng, shape = pq44.gt_instances()
pr, npr = pq44.pred_from_outlines(HERE + '/guided_ol/44_outlines_poly.json', shape)
a = pq44.pq(gt, ng, pr, npr, 'batch outline step on the batch ng1 maps of 44 (polygons)')
bm = cv2.resize(cv2.imread(HERE + '/guided_ol/44_blockmask.png', 0), (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
pr2, npr2 = pq44.pred_from_mask(bm)
b = pq44.pq(gt, ng, pr2, npr2, 'same, block mask before straightening')
json.dump([a, b], open(HERE + '/anchor44.json', 'w'), indent=1); print(json.dumps(a)); print(json.dumps(b))
