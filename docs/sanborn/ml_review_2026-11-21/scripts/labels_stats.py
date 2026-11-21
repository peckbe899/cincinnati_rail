"""Per-plate label statistics (read-only on the repo). Writes nothing to the repo."""
import json, os, sys
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
for N in ['43', '44', '45', '80', '82A']:
    lab = cv2.imread(U + f'{N}_label.png', 0); h, w = lab.shape
    alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > 0.5
    e = cv2.imread(U + f'{N}_edge.png', 0)
    ver = json.load(open(U + f'{N}_verified.json', encoding='utf8'))
    L = sum(np.hypot(b[0] - a[0], b[1] - a[1]) for a, b in ver)
    pa = alpha.sum()
    s = {k: round(float(((lab == k) & alpha).sum() / pa), 4) for k in (0, 1, 255)}
    # boundary contact without ignore band: 4-neighbour pairs 0|1
    c01 = int(((lab[:, 1:] == 0) & (lab[:, :-1] == 1)).sum() + ((lab[:, 1:] == 1) & (lab[:, :-1] == 0)).sum() + ((lab[1:] == 0) & (lab[:-1] == 1)).sum() + ((lab[1:] == 1) & (lab[:-1] == 0)).sum())
    # boundary length (0/255 or 1/255 or 0/1 contact) for scale
    # how much of the verified edge (half size) lies in the area label's ignore (255) pixels
    ev = e > 0
    onign = float((lab[ev] == 255).mean()) if ev.any() else 0
    # edge pixels that have both 0 and 1 within 3 px (i.e. a street/block boundary is actually taught around them)
    k = np.ones((7, 7), np.uint8)
    near0 = cv2.dilate((lab == 0).astype(np.uint8), k) > 0; near1 = cv2.dilate((lab == 1).astype(np.uint8), k) > 0
    both = float((near0 & near1)[ev].mean()) if ev.any() else 0
    only1 = float((near1 & ~near0)[ev].mean()) if ev.any() else 0
    only0 = float((near0 & ~near1)[ev].mean()) if ev.any() else 0
    neither = float((~near0 & ~near1)[ev].mean()) if ev.any() else 0
    # street components: number and size of taught street regions
    n0, cc0, st0, _ = cv2.connectedComponentsWithStats((lab == 0).astype(np.uint8), connectivity=4)
    sizes = np.sort(st0[1:, cv2.CC_STAT_AREA])[::-1]
    print(N, dict(paper_share_of_image=round(float(alpha.mean()), 4), within_paper=s, taught_within_paper=round(1 - s[255], 4),
                  verified_segments=len(ver), verified_len_fullpx=round(L), edge_png_px=int(ev.sum()),
                  edge_px_on_label255=round(onign, 3), edge_px_with_both_sides_taught=round(both, 3), edge_only_block_side=round(only1, 3), edge_only_street_side=round(only0, 3), edge_neither=round(neither, 3),
                  direct_0_1_contacts=c01, street_components=int(n0 - 1), street_comp_lt_2000px=int((sizes < 2000).sum())))
