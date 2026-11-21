"""v-final: lines of N_edges.json (step 4) whose middle lies within 40 px INSIDE the edge of the map ground, on the three
PDF sheets run here (90, 30, 47), with an exact full-size distance (not the 1/8-size one); and the same for the batch's
unet_data/N_edges.json. Against the implementer's merge/impl/r2/edge_pdf_final.json per sheet.
    python -B edge3.py -> v-final/edge3.json"""
import json
import numpy as np, cv2
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-final/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
IMP = json.load(open(V + '../impl/r2/edge_pdf_final.json'))['per_sheet']
L = lambda e: float(np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1]))
res = {}
for n in ('90', '30', '47'):
    H, W = cv2.imread(SP + f'cufp/22-{n}.jpg', 0).shape
    mg = cv2.resize(cv2.imread(V + f'plates/{n}/{n}_mapground.png', 0), (W // 2, H // 2), interpolation=cv2.INTER_NEAREST) > 0     # half size is enough
    din = cv2.distanceTransform(mg.astype(np.uint8), cv2.DIST_L2, 5) * 2
    def inside40(e):
        x, y = int(np.clip((e['a'][0] + e['b'][0]) / 4, 0, W // 2 - 1)), int(np.clip((e['a'][1] + e['b'][1]) / 4, 0, H // 2 - 1)); return bool(mg[y, x] and din[y, x] <= 40)
    out = {}
    for v, f in (('merged', V + f'plates/{n}/{n}_edges.json'), ('batch', SP + f'unet_data/{n}_edges.json')):
        E = json.load(open(f)); w = [inside40(e) for e in E]
        out[v] = dict(lines=len(E), inside40=sum(w), inside40_len=round(sum(L(e) for e, k in zip(E, w) if k)), inside40_orange=sum(1 for e, k in zip(E, w) if k and e['state'] != 'green'),
                      off_map_ground=sum(1 for e in E if not mg[int(np.clip((e['a'][1] + e['b'][1]) / 4, 0, H // 2 - 1)), int(np.clip((e['a'][0] + e['b'][0]) / 4, 0, W // 2 - 1))]))
    out['implementer_r2'] = {k: IMP[n]['r2'][k] for k in ('lines', 'inside40', 'inside40_len', 'inside40_orange')}
    out['implementer_round1'] = {k: IMP[n]['round1'][k] for k in ('lines', 'inside40', 'inside40_len')}
    out['implementer_B'] = {k: IMP[n]['B'][k] for k in ('lines', 'inside40', 'inside40_len')}
    res[n] = out; print(n, json.dumps(out))
json.dump(res, open(V + 'edge3.json', 'w'), indent=1)
