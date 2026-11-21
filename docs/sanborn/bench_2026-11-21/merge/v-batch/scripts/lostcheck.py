"""merge/v-batch: for each block of the batch (or B) the merged step lost (fewer.json), is it in the merged step's block
instances (N_blockinst.png, the blocks before tracing) or not? In: its polygon was dropped when traced (straighten() gave
under 3 sides). Not in: the block was never formed (no marker, or given to the street by the watershed / opening).
    python -B lostcheck.py   -> v-batch/lostcheck.json
"""
import json
import numpy as np
import cv2
import common as C
F = json.load(open(C.ME + 'fewer.json')); out = {}
for n, x in F.items():
    ks = [k for k in ('vs batch', 'vs B') if k in x['blocks']]
    if not ks: continue
    inst = cv2.imread(C.ME + f'plates/{n}/{n}_blockinst.png', cv2.IMREAD_UNCHANGED)
    mp = json.load(open(C.ME + f'plates/{n}/outlines.json', encoding='utf8'))
    K = len(np.unique(inst)) - 1; nb = sum(1 for p in mp if p and not p[0].get('hole'))
    res = dict(instances=int(K), block_polygons=nb)
    for k in ks:
        src = C.G + f'22-{n}/outlines.json' if k == 'vs batch' else C.BENCH + f'outline-nesting/runs_plates/final/{n}/outlines.json'
        op = [p for p in json.load(open(src, encoding='utf8')) if p and not p[0].get('hole') and len(p) >= 3]
        L = []
        for i, w in zip(x['blocks'][k]['lost_ids'], x['blocks'][k]['lost_why']):
            r = np.round(np.array([q['a'] for q in op[i]], float) / 2).astype(np.int32); m = np.zeros(inst.shape, np.uint8); cv2.fillPoly(m, [r], 1)
            lab = inst[m > 0]; cov = float((lab > 0).mean()); u, c = np.unique(lab[lab > 0], return_counts=True)
            top = int(u[c.argmax()]) if len(u) else 0
            # how much of that instance lies in the lost block (an instance of its own, or a piece of a bigger one?)
            own = float(c.max() / max(1, (inst == top).sum())) if top else 0.0
            L.append(dict(at=w['at'], area_px=w['block_area_px'], inst_cover=round(cov, 2), inst_own_share=round(own, 2), seed_px=w['largest_seed_px'],
                          verdict=('instance traced to under 3 sides (dropped)' if cov >= 0.5 and own >= 0.5 else ('part of a bigger instance' if cov >= 0.5 else 'no instance (no marker, or lost to the watershed or the opening)'))))
        res[k] = L
    out[n] = res
json.dump(out, open(C.mine(C.ME + 'lostcheck.json'), 'w'), indent=1)
for n, r in out.items():
    print(n, 'instances', r['instances'], 'polygons', r['block_polygons'])
    for k in ('vs batch', 'vs B'):
        if k in r: print('   ', k, [(l['at'], l['area_px'], l['inst_cover'], l['inst_own_share'], l['seed_px'], l['verdict'][:20]) for l in r[k]])
