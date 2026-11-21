"""Crops of the rule's streetcar stretches lying more than 30 px from every checked truth track (rail-rules, 21 Nov 2026),
for a given streetcar reach, to see by eye whether they are false or only undrawn. Read-only; writes into explore/.
    cd data/sanborn
    python bench_2026-11-21/rail-rules/false_stretches.py N BINS.png TRUTH.json REACH [REACH ...]
Tile colours: bins streetcar ink orange, rule streetcar tracks blue, the far stretch green, Ben's checked tracks magenta,
truth tracks marked src:'rule' (unchecked) grey."""
import sys, os, json, importlib.util
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from score_rail_bench import samples, draw, dist, clip
spec = importlib.util.spec_from_file_location('rt_prop', os.path.join(HERE, 'proposed', 'rail_tracks.py')); rt = importlib.util.module_from_spec(spec); spec.loader.exec_module(rt)
N, bp, tp = sys.argv[1:4]; reaches = [int(v) for v in sys.argv[4:]]
B = cv2.imread(bp, 0); H, W = B.shape; im = cv2.imread(f'cufp/22-{N}.jpg'); TJ = json.load(open(tp, encoding='utf8'))
ben = [np.asarray(t['pts'], float) for t in TJ['tracks'] if t['kind'] == 'streetcar' and t.get('src') != 'rule']
unk = [np.asarray(t['pts'], float) for t in TJ['tracks'] if t.get('src') == 'rule']
Db = dist(draw(ben, H, W)); ign = dist(draw(unk, H, W)) <= 30 if unk else np.zeros((H, W), bool)
os.makedirs(os.path.join(HERE, 'explore'), exist_ok=True)
for r in reaches:
    car = rt.streetcar_tracks((B == 5).astype(np.uint8), reach=r); tiles = []; tot = 0
    for p in car:
        S = samples(p); q = clip(S, H, W); far = (Db[q[:, 1], q[:, 0]] > 30) & ~ign[q[:, 1], q[:, 0]]
        if far.sum() < 10: continue
        idx = np.nonzero(far)[0]; runs = np.split(idx, np.nonzero(np.diff(idx) > 1)[0] + 1)
        for run in runs:
            if len(run) < 10: continue
            a, b = S[run[0]], S[run[-1]]; tot += 2 * len(run); c = (a + b) / 2; h = max(250, int(np.hypot(*(a - b)) / 2) + 80)
            x0, y0, x1, y1 = int(max(0, c[0] - h)), int(max(0, c[1] - h)), int(min(W, c[0] + h)), int(min(H, c[1] + h))
            t = im[y0:y1, x0:x1].copy(); t[B[y0:y1, x0:x1] == 5] = (0, 150, 255); off = np.array([x0, y0])
            for u in unk: cv2.polylines(t, [np.round(u - off).astype(np.int32)], False, (150, 150, 150), 9)
            for u in ben: cv2.polylines(t, [np.round(u - off).astype(np.int32)], False, (200, 0, 200), 3)
            for u in car: cv2.polylines(t, [np.round(u - off).astype(np.int32)], False, (200, 60, 0), 2)
            cv2.polylines(t, [np.round(S[run] - off).astype(np.int32)], False, (0, 200, 0), 2)
            s = 320 / max(t.shape[:2]); t = cv2.resize(t, (int(t.shape[1] * s), int(t.shape[0] * s)), interpolation=cv2.INTER_AREA)
            t = cv2.copyMakeBorder(t, 0, 320 - t.shape[0], 0, 320 - t.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255))
            cv2.putText(t, f'{N} r{r} {2 * len(run)}px ({int(c[0])},{int(c[1])})', (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1); tiles.append(t)
    print(f'reach {r}: {len(tiles)} stretches, {tot} px far from checked tracks')
    if tiles:
        while len(tiles) % 4: tiles.append(np.full((320, 320, 3), 255, np.uint8))
        cv2.imwrite(os.path.join(HERE, 'explore', f'far_{N}_r{r}.jpg'), np.vstack([np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]), [cv2.IMWRITE_JPEG_QUALITY, 88])
