"""Small whole-plate overview with the batch's rule tracks (bench_2026-11-21/rail). Read-only on the repo.
    cd data/sanborn
    python bench_2026-11-21/rail/overview.py OUTDIR SCALE N [N ...] [--rules DIR]   (DIR/N_rail_rule.json instead of unet_data)
Railroad tracks red, streetcar tracks blue, drawn 3 px at the output scale; the KEY box (census/key_boxes.json) green."""
import sys, os, json
import numpy as np, cv2
od, sc = sys.argv[1], float(sys.argv[2]); os.makedirs(od, exist_ok=True)
rd = sys.argv[sys.argv.index('--rules') + 1] if '--rules' in sys.argv else 'unet_data'
plates = [a for a in sys.argv[3:] if not a.startswith('--') and a != rd]
kb = {k['plate']: k for k in json.load(open('bench_2026-11-21/rail/census/key_boxes.json')) if k.get('score') and k['score'] >= 0.5} if os.path.exists('bench_2026-11-21/rail/census/key_boxes.json') else {}
for N in plates:
    im = cv2.imread(f'cufp/22-{N}.jpg'); c = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA); c = (c * 0.6 + 255 * 0.4).astype(np.uint8)
    T = json.load(open(os.path.join(rd, f'{N}_rail_rule.json'), encoding='utf8'))['tracks']
    for t in T:
        p = np.round(np.asarray(t['pts']) * sc).astype(np.int32); cv2.polylines(c, [p], False, (0, 0, 230) if t['kind'] == 'railroad' else (230, 80, 0), 3)
    if N in kb:
        x0, y0, x1, y1 = (int(v * sc) for v in kb[N]['box']); cv2.rectangle(c, (x0, y0), (x1, y1), (0, 170, 0), 2)
    cv2.imwrite(os.path.join(od, f'{N}_overview.jpg'), c, [cv2.IMWRITE_JPEG_QUALITY, 85]); print('wrote', N, c.shape)
