"""Analysis (finder2, 25 Nov 2026): v1 line ink on the truth v2 crops T1-T7, split by truth class, by the longest straight
run through the pixel and by local stroke width. Development only; tells how far run length and width separate big
lettering from lines.

    cd data/sanborn; python -B bench_2026-11-25/text_v1/finder2/scripts/anal_runs.py"""
import json, os, sys, time
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
TRUTH = os.path.normpath(os.path.join(HERE, '..', '..', 'truth'))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', '..', 'code')))
import finder2 as F

M = 200
crops = json.load(open(os.path.join(TRUTH, 'crops.json')))
LS = (81, 101, 121, 151, 201)
tot = {}
for tid in ('T1', 'T2', 'T3', 'T4', 'T6', 'T7'):
    c = crops[tid]; x0, y0, x1, y1 = c['win']; t0 = time.time()
    im, ink, paper, _ = F.load(c['plate'], (x0 - M, y0 - M, x1 + M, y1 + M))
    line, ori = F.line_ink(ink)
    fat = cv2.dilate(ink, np.ones((3, 3), np.uint8)); run = np.where(line > 0, 61, 0).astype(np.int16)
    for L in LS:
        o = np.zeros_like(ink)
        for i in range(F.P['angles']): o |= cv2.morphologyEx(fat, cv2.MORPH_OPEN, F.line_kernel(L, np.pi * i / F.P['angles'])) & ink
        run[(o > 0) & (line > 0)] = L
    dt = cv2.distanceTransform(ink, cv2.DIST_L2, 3); sw = 2 * cv2.dilate(dt, np.ones((5, 5), np.uint8))
    sl = (slice(M, M + y1 - y0), slice(M, M + x1 - x0))
    tr = cv2.imread(os.path.join(TRUTH, f'{tid}_mask.png'), 0)
    ln = line[sl] > 0; rr = run[sl]; ww = sw[sl]
    for cls, nm in ((2, 'text'), (1, 'nontext')):
        m = ln & (tr == cls)
        d = tot.setdefault(nm, {})
        for L in (61,) + LS:
            for wlo, whi in ((0, 4), (4, 5.5), (5.5, 7), (7, 99)):
                k = f'run{L}_w{wlo}-{whi}'; d[k] = d.get(k, 0) + int((m & (rr == L) & (ww >= wlo) & (ww < whi)).sum())
    print(tid, round(time.time() - t0, 1), 's', flush=True)
print('v1 line ink on truth crops (px), by longest straight run (61 = fits 61 but not 81, ...) and local stroke width')
for L in (61,) + LS:
    print(f'run {L:3d}: ' + '  '.join(f"w{w}: text {tot['text'][f'run{L}_w{w}']:6d} / non {tot['nontext'][f'run{L}_w{w}']:7d}" for w in ('0-4', '4-5.5', '5.5-7', '7-99')))
