"""crops_rail.py (text/effect, 25 Nov 2026): full-size crops of the places that matter for the rail, plain above the
overlay. Overlay: the text mask's ink in magenta (S1 runs) or the mask named, the baseline rule railroad track in blue,
the run's railroad track in green, Ben's tracks in yellow (thin). Writes crops/rail_*.png.
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/crops_rail.py"""
import json, os
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); RU = os.path.join(ROOT, 'runs'); MK = os.path.join(ROOT, 'masks'); OUT = os.path.join(ROOT, 'crops')
G5 = {g['group']: g for g in json.load(open(os.path.join(ROOT, '..', '..', 'diag', 'rail5', 'crops', 'groups.json')))}


def tracks(f, kind='railroad'): return [np.array(t['pts'], float) for t in json.load(open(f, encoding='utf8'))['tracks'] if t['kind'] == kind]


def crop(N, G, box, masks, run, name, scale=1.0):
    im = cv2.imread(f'cufp/22-{N}.jpg'); x0, y0, x1, y1 = box; raw = im[y0:y1, x0:x1].copy(); del im
    base = tracks(os.path.join(RU, f'{N}_{G}_base_tracks.json')); rt = tracks(os.path.join(RU, f'{N}_{G}_{run}_tracks.json'))
    ben = tracks(os.path.join(ROOT, 'inputs', f'rail_ben_{N}_copy.json')) + tracks(os.path.join(ROOT, 'inputs', f'rail_ben_{N}_copy.json'), 'streetcar')
    panels = [raw]
    for mk in masks:
        m = cv2.imread(os.path.join(MK, f'{N}_{G}_{mk}.png'), 0)[y0:y1, x0:x1] > 0
        L = cv2.cvtColor(raw, cv2.COLOR_BGR2LAB)[..., 0] < 140
        ov = raw.copy(); ov[m & L] = (255, 0, 255)
        for p in ben: cv2.polylines(ov, [np.round(p - [x0, y0]).astype(np.int32)], False, (0, 220, 255), 1)
        for p in base: cv2.polylines(ov, [np.round(p - [x0, y0]).astype(np.int32)], False, (255, 120, 0), 2)
        for p in tracks(os.path.join(RU, f'{N}_{G}_t{mk}_tracks.json')) if os.path.exists(os.path.join(RU, f'{N}_{G}_t{mk}_tracks.json')) else []:
            cv2.polylines(ov, [np.round(p - [x0, y0]).astype(np.int32) + [0, 3]], False, (0, 170, 0), 2)
        cv2.putText(ov, mk, (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
        panels.append(ov)
    sep = lambda a: np.full((6, a.shape[1], 3), 255, np.uint8)
    pic = panels[0]
    for p in panels[1:]: pic = np.vstack([pic, sep(p), p])
    if scale != 1.0: pic = cv2.resize(pic, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(OUT, f'rail_{name}.png'), pic); print(name, box, pic.shape, flush=True)


for g, nm in ((3, 'house_numbers_g3'), (4, 'house_numbers_g4'), (0, 'lot_numbers_g0'), (2, 'hook_g2'), (8, 'hook_g8')):
    x0, y0, x1, y1 = G5[g]['box']
    if x1 - x0 > 900: xm = (x0 + x1) // 2; x0, x1 = xm - 450, xm + 450
    crop('5', 'nets', (x0, y0, x1, y1), ['S0', 'S1', 'I'], 'tI', f'5_{nm}')
# plate 44: where S0 loses the junction near (2490, 3457), where I loses track 16, and a stretch of the main line S1 loses
crop('44', 'map', (2380, 3150, 3000, 3560), ['S0', 'S1', 'I'], 'tI', '44_junction_S0_loss')
crop('44', 'map', (4900, 5650, 5700, 6250), ['S0', 'S1', 'I'], 'tI', '44_track16_I_loss')
# (a third crop at (6400, 4200, 7100, 4700) was dropped: no railroad there; rail_44_junction_S0_loss.png shows the S1 loss too)
