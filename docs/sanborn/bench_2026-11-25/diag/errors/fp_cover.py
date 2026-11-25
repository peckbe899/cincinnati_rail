"""false blocks of each pair against the baseline's false ground (same grid): share of each false block's area that the
baseline also had inside one of its false blocks. 'split piece' = >= 50% covered (the same false ground, cut up
differently); 'new ground' otherwise. Also total false area in void and on decided ground, and the decided-ground
scores of bench44.json (precision_decided, recall_interior_decided, PQ_decided), paired by grid.
    python -B fp_cover.py  -> fp_cover.json"""
import json, numpy as np, cv2
HERE = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/diag/errors/'
EV = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/train_v2_runs/eval/'
d = json.load(open(HERE + 'census.json')); dec = cv2.imread(HERE + 'runs/decided_half.png', 0) > 0
out = {}
for s in ['baseline', 'V1S1', 'V2S1', 'V1S2', 'V2S2']:
    rows = []
    for g in range(6):
        js = json.load(open(HERE + f'runs/{s}_g{g}.json')); inst = cv2.imread(HERE + f'runs/{s}_g{g}_inst.png', cv2.IMREAD_UNCHANGED).astype(np.int32)
        bjs = json.load(open(HERE + f'runs/baseline_g{g}.json')); binst = cv2.imread(HERE + f'runs/baseline_g{g}_inst.png', cv2.IMREAD_UNCHANGED).astype(np.int32)
        bfpm = np.isin(binst, bjs['blocks']['fp_p'])
        mp = set(js['blocks']['merge_p'])
        fpm = np.isin(inst, js['blocks']['fp_p'])
        nonmerge = [j for j in js['blocks']['fp_p'] if j not in mp]
        cov = []
        for j in nonmerge:
            m = inst == j; cov.append(float(bfpm[m].mean()))
        b = json.load(open(EV + f'{s}/runs44/v2__grid{g}/bench44.json'))
        rows.append(dict(fp=len(js['blocks']['fp_p']), merges_fp=len([j for j in js['blocks']['fp_p'] if j in mp]), nonmerge_fp=len(nonmerge),
                         nonmerge_split_piece=sum(c >= 0.5 for c in cov), nonmerge_new_ground=sum(c < 0.5 for c in cov),
                         fp_area_void_M=float((fpm & ~dec).sum() * 4 / 1e6), fp_area_decided_M=float((fpm & dec).sum() * 4 / 1e6),
                         nonmerge_fp_area_M=float(np.isin(inst, nonmerge).sum() * 4 / 1e6),
                         PQ=b['headline']['all']['PQ'], PQ_decided=b['headline']['all']['PQ_decided'], fp_decided=b['headline']['all']['fp_decided'],
                         precision=b['lines_shown']['all']['precision'], precision_decided=b['lines_shown']['all']['precision_decided'],
                         recall_interior=b['lines_shown']['all']['recall_interior'], recall_interior_decided=b['lines_shown']['all']['recall_interior_decided']))
    out[s] = rows
json.dump(out, open(HERE + 'fp_cover.json', 'w'), indent=1)
keys = list(out['baseline'][0].keys())
print('mean of 6 grids:', ' '.join(keys))
for s, rows in out.items():
    print(s, ' '.join(f"{np.mean([r[k] for r in rows]):.3f}" for k in keys))
print('paired gains over baseline, by grid (PQ_decided, precision_decided, recall_interior_decided):')
for s in ['V1S1', 'V2S1', 'V1S2', 'V2S2']:
    for k in ('PQ', 'PQ_decided', 'precision_decided', 'recall_interior_decided'):
        gains = [out[s][g][k] - out['baseline'][g][k] for g in range(6)]
        print(s, k, f"mean {np.mean(gains):+.4f}", 'up on', sum(x > 0 for x in gains), 'of 6', [round(x, 3) for x in gains])
