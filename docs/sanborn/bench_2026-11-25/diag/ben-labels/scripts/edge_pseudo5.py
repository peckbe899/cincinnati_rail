"""Q3 add-on: how train_v2/5 (pseudo, V2) and the map recipe teach 5's inkless sheet-edge lines; also the area label beside them.
    python -B bench_2026-11-25/diag/ben-labels/scripts/edge_pseudo5.py"""
import sys, os, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa
rows = [r for r in json.load(open(DIAG + '/sheet_edge_rows_5.json')) if r['kind'] == 'drawn' and r['along_edge'] and r['ink'] < 0.3]
H, W = 7150, 10076; af = alpha_full('5', W, H); m = (raster([(r['a'], r['b']) for r in rows], (H, W), 1.0, LINE) > 0) & af
out = {'lines': len(rows), 'length_px': sum(r['length'] for r in rows), 'median_length': float(np.median([r['length'] for r in rows])), 'px': int(m.sum())}
for k, f in (('pseudo (train_v2/5)', SP + 'train_v2/5/lines.png'), ('map recipe now', DIAG + '/map_now/5_lines.png')):
    t = cv2.imread(f, 0); out[k] = {str(v): round(float((t[m] == v).mean()), 4) for v in (1, 0, 255)}
tpos = (cv2.imread(DIAG + '/map_now/5_lines.png', 0) == 1).sum(); out['share_of_map_positive_px'] = round(float(m.sum() / tpos), 4)
print(json.dumps(out)); wj(os.path.join(DIAG, 'edge_pseudo5.json'), out)
