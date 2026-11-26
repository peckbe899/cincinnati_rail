"""dev (finder2): per-word recall on truth v2 T1-T7 from crop-sized code images DIR/T#_text.png (text = codes 2,3).
    cd data/sanborn; python -B <this> DIR [kind,kind] [--max 0.9]"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); TV1 = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
TRUTH = os.path.join(TV1, 'truth'); sys.path.insert(0, os.path.join(TV1, 'code'))
from score_text import poly_fill
a = [x for i, x in enumerate(sys.argv[1:], 1) if not x.startswith('--') and sys.argv[i - 1] != '--max']
D = a[0]; kinds = a[1].split(',') if len(a) > 1 else None
mx = float(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 1.01
crops = json.load(open(os.path.join(TRUTH, 'crops.json')))
for tid in ('T1', 'T2', 'T3', 'T4', 'T6', 'T7'):
    c = crops[tid]; x0, y0 = c['win'][:2]; code = cv2.imread(os.path.join(D, f'{tid}_text.png'), 0)
    truth = cv2.imread(os.path.join(TRUTH, f'{tid}_mask.png'), 0); t2 = truth == 2
    for w in json.load(open(os.path.join(TRUTH, f'{tid}_words.json'), encoding='utf8'))['words']:
        if kinds and w['kind'] not in kinds or not w.get('poly'): continue
        pm = poly_fill(truth.shape, w['poly'], np.array([x0, y0])) & t2; n = int(pm.sum())
        if not n: continue
        f = int((pm & np.isin(code, (2, 3))).sum())
        if f / n < mx:
            miss = {int(v): int(((code == v) & pm).sum()) for v in (0, 1, 4, 5) if ((code == v) & pm).any()}
            print(f"{tid} {w['kind']:6s} {w['reading'][:22]:22s} h {w.get('height', 0):5.1f}  recall {f / n:.3f} ({f}/{n})  missed {miss}  aabb {w.get('aabb')}")
