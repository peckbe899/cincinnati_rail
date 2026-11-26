"""Analysis (finder2): stroke width (2 x distance to paper on the ridge, L2 5x5 mask) of truth v2 text by word kind and
height, and of the truth's non-text ink. Development only. cd data/sanborn; python -B <this>"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); TRUTH = os.path.normpath(os.path.join(HERE, '..', '..', 'truth'))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', '..', 'code')))
from score_text import poly_fill
crops = json.load(open(os.path.join(TRUTH, 'crops.json'))); agg = {}
for tid in ('T1', 'T2', 'T3', 'T4', 'T6', 'T7'):
    c = crops[tid]; x0, y0, x1, y1 = c['win']; tr = cv2.imread(os.path.join(TRUTH, f'{tid}_mask.png'), 0)
    for cls in (1, 2):
        m = (tr == cls).astype(np.uint8); dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
        ridge = (dt > 0) & (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8)))
        if cls == 1: agg.setdefault('NONTEXT', []).extend((2 * dt[ridge]).tolist()); continue
        for w in json.load(open(os.path.join(TRUTH, f'{tid}_words.json'), encoding='utf8'))['words']:
            if not w.get('poly'): continue
            pm = poly_fill(tr.shape, w['poly'], np.array([x0, y0])) & ridge
            h = w.get('height') or 0; hb = 'h<35' if h < 35 else ('h35-55' if h < 55 else 'h55+')
            agg.setdefault(f"{w['kind']} {hb}", []).extend((2 * dt[pm]).tolist())
for k in sorted(agg):
    v = np.array(agg[k]);
    if len(v) < 50: continue
    print(f'{k:18s} n {len(v):7d}  p10 {np.percentile(v,10):.1f}  p25 {np.percentile(v,25):.1f}  med {np.median(v):.1f}  p75 {np.percentile(v,75):.1f}  p90 {np.percentile(v,90):.1f}')
