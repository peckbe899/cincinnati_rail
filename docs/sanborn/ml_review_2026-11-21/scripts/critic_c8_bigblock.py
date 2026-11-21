import json, os, numpy as np, cv2
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = D + 'unet_data/'
cen = {r['n']: r for r in json.load(open(os.path.dirname(os.path.abspath(__file__)) + '/census.json'))}
res = {}
for n, r in cen.items():
    f = U + f'{n}_blockmask.png'
    if r['blocks'] is None or not os.path.exists(f): continue
    if os.path.getmtime(f) < os.path.getmtime(U + 'models/lines_ng1.done'): continue   # only this batch's masks
    b = cv2.imread(f, 0) > 0; al = np.load(D + f'cufp/{n}/png_alpha_s4.npy').astype(np.uint8)
    m = cv2.resize(al, (b.shape[1], b.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    k, cc, st, _ = cv2.connectedComponentsWithStats(b.astype(np.uint8), connectivity=4)
    big = st[1:, cv2.CC_STAT_AREA].max() if k > 1 else 0
    # paper share inside the poly outlines: number of polygons and the largest as share of paper
    # touches the margin: largest component within 60 half-px of the paper edge along > 30% of the paper edge
    edge = m & ~(cv2.erode(m.astype(np.uint8), np.ones((121, 121), np.uint8)) > 0)
    lab_big = (cc == (1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])))) if k > 1 else np.zeros_like(b)
    res[n] = dict(kind=r['kind'], blocks=r['blocks'], block_px_share=round(float(b[m].mean()), 3), largest_share_of_paper=round(float(big / m.sum()), 3), largest_on_edge_band=round(float(lab_big[edge].mean()), 3), pred_block_share=r['block_share'])
json.dump(res, open(os.path.dirname(os.path.abspath(__file__)) + '/bigblock.json', 'w'), indent=1)
bad = {n: v for n, v in res.items() if v['largest_share_of_paper'] > 0.3}
for n, v in sorted(res.items(), key=lambda kv: -kv[1]['largest_share_of_paper']): print(n, v)
print('plates', len(res), 'with one outline covering >30% of the paper:', len(bad), sorted(bad), ' pdf among them', sum(v['kind'] == 'pdf' for v in bad.values()), 'of', sum(v['kind'] == 'pdf' for v in res.values()))
