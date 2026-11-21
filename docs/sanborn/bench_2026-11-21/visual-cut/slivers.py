"""Small and thin block pieces in the outline step's block mask (visual-cut, 21 Nov 2026). Reads only; prints a summary
and writes audit/N_slivers.json.

    python slivers.py N [N ...]

Every block-mask piece of 6000 px or more (outlines.py MIN_AREA) gets: area, its widest inscribed width (2 x the
largest distance to its edge), whether it touches the paper edge (within 40 px), and its share of the paper.
  small    area < 25 % of the plate's median piece
  thin     inscribed width < 90 px at full size (narrower than most streets at 200 ft to the inch): a sliver of street or
           paper margin called block, a parkway median, a strip along a rail line
  edge     touches the paper edge
  big      one piece over 15 % of the paper (several blocks, water or rail land run together)
"""
import json, os, sys
import numpy as np, cv2
from vlib import SP, U, HERE

for n in sys.argv[1:]:
    bm = cv2.imread(os.path.join(HERE, 'out44', '44_blockmask.png') if n == '44' else U + f'{n}_blockmask.png', 0) > 127   # half size
    a4 = np.load(SP + f'cufp/{n}/png_alpha_s4.npy').astype(np.uint8); al = cv2.resize(a4, (bm.shape[1], bm.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    edge = cv2.dilate((~al).astype(np.uint8), np.ones((41, 41), np.uint8)) > 0    # 20 px at half size = 40 px full
    ncc, cc, st, _ = cv2.connectedComponentsWithStats(bm.astype(np.uint8), connectivity=4)
    dt = cv2.distanceTransform(bm.astype(np.uint8), cv2.DIST_L2, 5)
    paper = float(al.sum()); rows = []
    for i in range(1, ncc):
        A = int(st[i, 4]) * 4
        if A < 6000: continue
        m = cc == i; w = float(dt[m].max()) * 2 * 2   # inscribed width, full-size px
        rows.append(dict(cc=i, bbox=[int(v) * 2 for v in st[i, :4]], area=A, width=round(w), edge=bool((m & edge).any()), share=round(A / (paper * 4), 4)))
    med = float(np.median([r['area'] for r in rows])) if rows else 0
    for r in rows: r.update(small=r['area'] < 0.25 * med, thin=r['width'] < 90, big=r['share'] > 0.15)
    s = dict(plate=n, pieces=len(rows), median_area=round(med), small=sum(r['small'] for r in rows), small_edge=sum(r['small'] and r['edge'] for r in rows),
             thin=sum(r['thin'] for r in rows), thin_edge=sum(r['thin'] and r['edge'] for r in rows), small_or_thin=sum(r['small'] or r['thin'] for r in rows),
             big=sum(r['big'] for r in rows), big_share=round(sum(r['share'] for r in rows if r['big']), 3))
    json.dump(dict(summary=s, pieces=rows), open(os.path.join(HERE, 'audit', f'{n}_slivers.json'), 'w'), indent=0)
    print(json.dumps(s), flush=True)
