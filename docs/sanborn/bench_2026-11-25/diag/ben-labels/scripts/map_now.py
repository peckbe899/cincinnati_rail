"""Diagnosis only (ben-labels, 25 Nov 2026): the map labels make_labels_v2.map_labels would give plates 5 and 44 TODAY
from Ben's checked lines, computed in memory and written ONLY into this diag folder (never train_v2/). 44 is the
benchmark: these files are for studying how the current recipe would teach it, never for training.
    cd data/sanborn; python -B bench_2026-11-25/diag/ben-labels/scripts/map_now.py 5 44
"""
import os, sys, json, time
import numpy as np, cv2
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'sanborn', 'unet'))
import make_labels_v2 as M  # noqa
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'map_now')
os.makedirs(OUT, exist_ok=True)
for N in sys.argv[1:]:
    t0 = time.time()
    img, lab, edge, t, val, sm, counts = M.map_labels(N, verbose=False)
    cv2.imwrite(os.path.join(OUT, f'{N}_label.png'), lab); cv2.imwrite(os.path.join(OUT, f'{N}_lines.png'), t); cv2.imwrite(os.path.join(OUT, f'{N}_edge.png'), edge)
    json.dump(sm, open(os.path.join(OUT, f'{N}_streetmap.json'), 'w', encoding='utf8'), separators=(',', ':'))
    json.dump(dict(plate=N, counts=counts, note='diagnosis only: make_labels_v2.map_labels in memory; never training data', seconds=round(time.time() - t0, 1)), open(os.path.join(OUT, f'{N}_counts.json'), 'w'), indent=1)
    print(N, json.dumps({k: v for k, v in counts.items() if k != 'rays'}), round(time.time() - t0, 1), 's', flush=True)
