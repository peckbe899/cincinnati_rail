"""Selection agent (23 Nov 2026): how much ground a pseudo label would teach on each plate, and how much the 4 labelled
plates teach today. Read-only on the repo; system Python.

    python -B pseudo_area.py     -> pseudo_area.json in this folder

Labelled plates (43, 45, 80, 82A): unet_data/N_label.png (half size; 0 street, 1 block, 255 not taught). Taught px,
taught acres (scale from the census px_per_ft, full-size px per foot), and the sizes of the label's block pieces
(connected pieces of label == 1), in acres: the yardstick for how big a real block is at each scale.

Pseudo plates: a sketch of the confidence filter (the integrator's own filter decides the real one):
  block  = area_ng1 p >= 0.95, inside a merged-step block (picks22_guided/22-N/outlines.json, holes removed)
           whose area is at most BIGMAX x the 99th percentile of the labelled plates' block pieces at that scale;
  street = area_ng1 p <= 0.05, outside every merged block;
  not taught: everything else, off the map ground (PDF sheets: unet_data/N_mapground.png), the KEY box
           (census/rail_key.json key_box) and a 12 px (half size) band at the paper's edge.
Reported: taught px and acres, the share of the ground taught, and the share of the merged blocks' area dropped as
too big (open land, river, rail yards, merges across streets).
"""
import csv, json, os
import numpy as np
import cv2

SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
OUT = os.path.dirname(os.path.abspath(__file__)); BIGMAX = 1.5; PCT = 99
import sys
if '--strict' in sys.argv: BIGMAX, PCT = 1.0, 98     # the cap: BIGMAX x the PCT percentile of the labelled block pieces
LABELLED = ['43', '45', '80', '82A']


def ground_of(N, hw, hh):
    a4 = np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.uint8)
    paper = cv2.resize(a4, (hw, hh), interpolation=cv2.INTER_NEAREST) > 0
    mg = U + f'{N}_mapground.png'
    g = paper & (cv2.resize(cv2.imread(mg, 0), (hw, hh), interpolation=cv2.INTER_NEAREST) > 127) if os.path.exists(mg) else paper
    return paper, g


def main():
    census = {r['plate']: r for r in csv.DictReader(open(SP + 'bench_2026-11-21/census/census.csv', encoding='utf8'))}
    keys = json.load(open(SP + 'bench_2026-11-21/census/rail_key.json', encoding='utf8'))
    scale = json.load(open(SP + 'scale_table.json', encoding='utf8'))
    res = dict(how=__doc__, bigmax=BIGMAX, percentile=PCT, labelled={}, pseudo={})
    sizes = {100: [], 200: []}
    for N in LABELLED:
        lab = cv2.imread(U + f'{N}_label.png', 0); hh, hw = lab.shape
        ppf = float(census[N]['px_per_ft']); acre_per_halfpx = (2.0 / ppf) ** 2 / 43560.0
        taught = lab != 255; n, cc, st, _ = cv2.connectedComponentsWithStats((lab == 1).astype(np.uint8), connectivity=4)
        ac = [float(st[i, cv2.CC_STAT_AREA]) * acre_per_halfpx for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 200]
        sizes[scale[N]['ft_per_inch']] += ac
        res['labelled'][N] = dict(ft_per_inch=scale[N]['ft_per_inch'], half_px=hw * hh, taught_half_mpx=round(taught.sum() / 1e6, 2), taught_acres=round(taught.sum() * acre_per_halfpx, 1),
                                  street_share_of_taught=round(float((lab == 0).sum() / taught.sum()), 3), block_pieces=len(ac), block_piece_acres_median=round(float(np.median(ac)), 2),
                                  block_piece_acres_p90=round(float(np.percentile(ac, 90)), 2), block_piece_acres_max=round(max(ac), 1))
    cap = {s: float(np.percentile(v, PCT)) * BIGMAX for s, v in sizes.items()}
    res['block_size_cap_acres'] = {str(k): round(v, 2) for k, v in cap.items()}
    res['labelled_total'] = dict(taught_half_mpx=round(sum(v['taught_half_mpx'] for v in res['labelled'].values()), 2), taught_acres=round(sum(v['taught_acres'] for v in res['labelled'].values()), 1))
    for N, c in census.items():
        if N in LABELLED or N == '44': continue
        ft = scale[N]['ft_per_inch']
        pa = cv2.imread(U + f'{N}_pred_area_ng1.png', 0); hh, hw = pa.shape
        paper, g = ground_of(N, hw, hh)
        g &= cv2.erode(paper.astype(np.uint8), np.ones((25, 25), np.uint8)) > 0
        kb = keys.get(N, {}).get('key_box')
        if kb: x0, y0, x1, y1 = [int(v / 2) for v in kb]; g[max(0, y0 - 10):y1 + 10, max(0, x0 - 10):x1 + 10] = False
        ppf = float(c['px_per_ft']); acre_per_halfpx = (2.0 / ppf) ** 2 / 43560.0
        polys = json.load(open(SP + f'picks22_guided/22-{N}/outlines.json', encoding='utf8'))
        inst = np.zeros((hh, hw), np.int32); k = 0
        for poly in polys:
            if poly[0].get('hole'): continue
            k += 1; cv2.fillPoly(inst, [(np.array([s['a'] for s in poly], float) * 0.5).round().astype(np.int32)], k)
        for poly in polys:
            if poly[0].get('hole'): cv2.fillPoly(inst, [(np.array([s['a'] for s in poly], float) * 0.5).round().astype(np.int32)], 0)
        area = np.bincount(inst.ravel(), minlength=k + 1).astype(float) * acre_per_halfpx
        capx = cap.get(ft, cap[200] * 4 if ft == 400 else cap[200])
        ok_block = (area <= capx); ok_block[0] = False
        inb = inst > 0; okb = ok_block[inst]
        blk = (pa >= 243) & okb & g; st_ = (pa <= 12) & ~inb & g
        taught = blk | st_
        big = inb & ~okb & g
        res['pseudo'][N] = dict(ft_per_inch=ft, source=c['source'], ground_half_mpx=round(g.sum() / 1e6, 2), ground_acres=round(g.sum() * acre_per_halfpx, 1),
                                taught_half_mpx=round(taught.sum() / 1e6, 2), taught_acres=round(taught.sum() * acre_per_halfpx, 1), taught_share_of_ground=round(float(taught.sum() / max(1, g.sum())), 3),
                                taught_street_share=round(float(st_.sum() / max(1, taught.sum())), 3), merged_blocks=k, blocks_kept=int(ok_block.sum()),
                                big_block_share_of_ground=round(float(big.sum() / max(1, g.sum())), 3), block_cap_acres=round(capx, 2),
                                largest_block_acres=round(float(area[1:].max()), 1) if k else 0.0, key_masked=bool(kb))
        print(N, res['pseudo'][N], flush=True)
    print('labelled', json.dumps(res['labelled'], indent=1), res['labelled_total'], res['block_size_cap_acres'])
    json.dump(res, open(os.path.join(OUT, 'pseudo_area_strict.json' if '--strict' in sys.argv else 'pseudo_area.json'), 'w', encoding='utf8', newline='\n'), indent=1)


if __name__ == '__main__':
    main()
