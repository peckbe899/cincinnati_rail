"""errors census, stage 2 (25 Nov 2026): what lies under the errors on plate 44, each new pair against the baseline.
Reads runs/ (collect.py), unet_data/44_bins.png, cufp/22-44.jpg, the eval maps (train_v2_runs/eval/STEP/maps44/gridG/).
Writes census.json and layers.npz here. Measured, no estimates; every length is in full-size px (1 sample = 1 px).

Definitions
  false line     a sample of a shown line (44_shown.json minus the sheet outline) more than 5 px from Ben's lines
                 (with the 20 deg direction test), as bench44 scores precision
  new false      a false sample of the pair with no false sample of the baseline (same grid) within 5 px / 20 deg
  fixed false    a false sample of the baseline with no false sample of the pair within 5 px / 20 deg
  lost line      a sample of Ben's line found by the baseline (<= 5 px) and not by the pair; gained: the reverse
  false block    bench44's fp (no Ben block matched at IoU > 0.5); new false block: IoU <= 0.5 with every false block
                 of the baseline on the same grid
  ink under      the bins of 44_bins.png in a 7 x 7 px window round the sample: the most common bin, 0 = no ink
  on text        any bin-8 px in that window; 'near-street text' = bin-8 px within 40 px of one of Ben's lines
  street dist    distance to the nearest of Ben's lines, any direction
  tint           share of the 31 x 31 px square round the sample with HSV saturation > 60 (census definition)
  region         fold A/B (bench44), Ben's block ground or street ground, decided ground or void, a 3 x 3 cell
  partner        for Ben's samples: distance to the nearest sample of another of his lines within 20 deg (the far
                 side of the street, or of the block): < 75 px is an alley or narrow street (3 px per ft)
"""
import json, os, sys, time
import numpy as np, cv2
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
TOOLS = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/'
EV = SP + 'train_v2_runs/eval/'
PAIRS = ['V1S1', 'V2S1', 'V1S2', 'V2S2']
sys.dont_write_bytecode = True; sys.path.insert(0, TOOLS); sys.path.insert(0, TOOLS + '..')
import bench44 as B  # noqa: E402
B.RUNS = HERE + 'b44cache/'
W, H = 10768, 7219; FX, FY, FX2 = 2950, 3560, 5400
BIN_NAMES = {0: 'no ink', 1: 'block line', 2: 'lot line', 3: 'building', 4: 'railroad', 5: 'streetcar', 6: 'pipe', 7: 'sewer', 8: 'text/numbers', 9: 'not sorted'}
R = 3          # window half size for 'ink under'
TEXT_NEAR = 40.0


def win(A, P, r):
    x = np.clip(np.round(P[:, 0]).astype(int), r, A.shape[1] - 1 - r); y = np.clip(np.round(P[:, 1]).astype(int), r, A.shape[0] - 1 - r)
    out = np.empty((len(P), (2 * r + 1) ** 2), A.dtype); k = 0
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out[:, k] = A[y + dy, x + dx]; k += 1
    return out


def at(A, P, s=1.0):
    x = np.clip((P[:, 0] * s).astype(int), 0, A.shape[1] - 1); y = np.clip((P[:, 1] * s).astype(int), 0, A.shape[0] - 1)
    return A[y, x]


def load_layers():
    f = HERE + 'layers.npz'
    bins = cv2.imread(SP + 'unet_data/44_bins.png', cv2.IMREAD_UNCHANGED)
    ben = dict(np.load(HERE + 'runs/ben.npz'))
    if os.path.exists(f):
        L = dict(np.load(f)); L['bins'] = bins; L['ben'] = ben; return L
    img = cv2.imread(SP + 'cufp/22-44.jpg')
    sat = (cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[..., 1] > 60).astype(np.float32)
    del img
    sat2 = cv2.resize(sat, (W // 2, H // 2), interpolation=cv2.INTER_AREA); del sat
    tint2 = cv2.blur(sat2, (15, 15)).astype(np.float16)
    # distance of every text px to Ben's lines
    tree = cKDTree(ben['P'])
    ys, xs = np.nonzero(bins == 8)
    d, _ = tree.query(np.c_[xs, ys].astype(np.float32), k=1, distance_upper_bound=TEXT_NEAR + 1, workers=-1)
    nst = np.zeros((H, W), np.uint8); sel = d <= TEXT_NEAR; nst[ys[sel], xs[sel]] = 1
    np.savez_compressed(f, tint2=tint2, nst=nst)
    L = dict(tint2=tint2, nst=nst, bins=bins, ben=ben)
    return L


def partner(ben):
    """distance from each of Ben's samples to the nearest sample of another of his lines within 20 deg"""
    P, Pd, ix = ben['P'], ben['Pd'], ben['ix']; out = np.full(len(P), np.inf, np.float32); c = np.cos(np.radians(20))
    tree = cKDTree(P)
    for i in np.unique(ix):
        s = np.nonzero(ix == i)[0]
        d, j = tree.query(P[s], k=400, distance_upper_bound=300, workers=-1)
        ok = np.isfinite(d); jj = np.where(ok, j, 0)
        ok &= (ix[jj] != i) & (np.abs((Pd[jj] * Pd[s][:, None, :]).sum(2)) >= c)
        out[s] = np.where(ok, d, np.inf).min(1)
    return out


def classify(P, L, gt, dec, extra=None):
    """per-sample classes; returns a dict of arrays"""
    if len(P) == 0: return None
    wb = win(L['bins'], P, R)
    cnt = np.stack([(wb == k).sum(1) for k in range(1, 10)], 1)
    dom = np.where(cnt.max(1) > 0, cnt.argmax(1) + 1, 0)
    text = cnt[:, 7] > 0
    nst = win(L['nst'], P, R).max(1) > 0
    tree = L['ben_tree']; dstreet, _ = tree.query(P, k=1, workers=-1)
    tint = at(L['tint2'], P, 0.5).astype(np.float32)
    inblk = at(gt, P, 0.5) > 0; decd = at(dec, P, 0.5) > 0
    foldA = ((P[:, 0] < FX) & (P[:, 1] < FY)) | (P[:, 0] >= FX2)
    cell = np.clip((P[:, 0] // (W / 3)).astype(int), 0, 2) + 3 * np.clip((P[:, 1] // (H / 3)).astype(int), 0, 2)
    return dict(dom=dom, text=text, nst=nst, dstreet=dstreet.astype(np.float32), tint=tint, inblk=inblk, dec=decd, foldA=foldA, cell=cell)


CELLS = ['NW', 'N', 'NE', 'W', 'C', 'E', 'SW', 'S', 'SE']
DBINS = [(0, 5), (5, 10), (10, 20), (20, 40), (40, 80), (80, 1e9)]
TBINS = [(0, 0.1), (0.1, 0.4), (0.4, 1.01)]


def table(c, sel=None):
    """length (px) by every class of a set of samples"""
    if c is None: return dict(n=0)
    s = np.ones(len(c['dom']), bool) if sel is None else sel
    n = int(s.sum())
    if n == 0: return dict(n=0)
    t = dict(n=n)
    t['ink'] = {BIN_NAMES[k]: int(((c['dom'] == k) & s).sum()) for k in range(10)}
    t['any_text_in_window'] = int((c['text'] & s).sum()); t['near_street_text_in_window'] = int((c['nst'] & s).sum())
    t['street_dist'] = {f'{a:g}-{b:g}' if b < 1e8 else f'>{a:g}': int(((c['dstreet'] >= a) & (c['dstreet'] < b) & s).sum()) for a, b in DBINS}
    t['tint'] = {f'{a:g}-{min(b, 1):g}': int(((c['tint'] >= a) & (c['tint'] < b) & s).sum()) for a, b in TBINS}
    t['ground'] = dict(ben_block=int((c['inblk'] & s).sum()), street=int((~c['inblk'] & s).sum()))
    t['decided'] = dict(decided=int((c['dec'] & s).sum()), void=int((~c['dec'] & s).sum()))
    t['fold'] = dict(A=int((c['foldA'] & s).sum()), B=int((~c['foldA'] & s).sum()))
    t['cell'] = {CELLS[k]: int(((c['cell'] == k) & s).sum()) for k in range(9)}
    return t


def side_samples(polys, js):
    """samples of the sides of polygons js (1-based raster ids = index + 1)"""
    segs = [(s['a'], s['b']) for j in js for s in polys[j - 1]]
    P, Pd, ix = B.sample(segs)
    owner = np.array([j for j in js for _ in polys[j - 1]])[ix] if len(ix) else np.zeros(0, int)
    return P, Pd, owner


def main():
    t0 = time.time()
    L = load_layers(); ben = L['ben']; L['ben_tree'] = cKDTree(ben['P'])
    gt = cv2.imread(HERE + 'runs/gt_half.png', cv2.IMREAD_UNCHANGED).astype(np.int32); dec = cv2.imread(HERE + 'runs/decided_half.png', 0) > 0
    print('layers', round(time.time() - t0, 1), flush=True)
    if os.path.exists(HERE + 'runs/ben_partner.npy'): part = np.load(HERE + 'runs/ben_partner.npy')
    else: part = partner(ben); np.save(HERE + 'runs/ben_partner.npy', part)
    print('partner', round(time.time() - t0, 1), flush=True)
    bc = classify(ben['P'], L, gt, dec)
    interior = np.isin(ben['lab'], ('printed', 'drawn'))
    res = dict(definitions=__doc__, ben=dict(all_interior=table(bc, interior), partner_lt75_interior=int((interior & (part < 75)).sum())), runs={})
    # plate-wide reference: the 5-40 px band beside Ben's lines (where house numbers sit), share with near-street text in window
    ys, xs = np.mgrid[0:H:4, 0:W:4]; G = np.c_[xs.ravel(), ys.ravel()].astype(np.float32)
    dG, _ = L['ben_tree'].query(G, k=1, workers=-1); band = (dG > 5) & (dG <= 40)
    alpha = np.load(SP + 'cufp/44/png_alpha_s4.npy'); al = cv2.resize(alpha.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)
    band &= at(al, G) > 0
    res['reference'] = dict(band_5_40_samples=int(band.sum()), band_share_near_street_text=round(float((win(L['nst'], G[band], R).max(1) > 0).mean()), 4),
                            band_share_any_text=round(float((win((L['bins'] == 8).astype(np.uint8), G[band], R).max(1) > 0).mean()), 4),
                            paper_share_near_street_text=round(float((win(L['nst'], G[at(al, G) > 0], R).max(1) > 0).mean()), 4))
    print('reference', res['reference'], round(time.time() - t0, 1), flush=True)
    base = {}
    for g in range(6):
        base[g] = dict(np.load(HERE + f'runs/baseline_g{g}.npz')); base[g]['js'] = json.load(open(HERE + f'runs/baseline_g{g}.json'))
        base[g]['inst'] = cv2.imread(HERE + f'runs/baseline_g{g}_inst.png', cv2.IMREAD_UNCHANGED).astype(np.int32)
    keep = {}
    for step in ['baseline'] + PAIRS:
        for g in range(6):
            r = dict(np.load(HERE + f'runs/{step}_g{g}.npz')); js = json.load(open(HERE + f'runs/{step}_g{g}.json'))
            inst = cv2.imread(HERE + f'runs/{step}_g{g}_inst.png', cv2.IMREAD_UNCHANGED).astype(np.int32)
            polys = json.load(open(js['run'] + 'outlines.json', encoding='utf8'))
            lmap = cv2.imread(EV + f'{step}/maps44/grid{g}/44_lines.png', 0); amap = cv2.imread(EV + f'{step}/maps44/grid{g}/44_area.png', 0)
            off = r['dp'] > 5
            cP = classify(r['P'], L, gt, dec)
            o = dict(false_all=table(cP, off), shown_len=int(len(off)), false_len=int(off.sum()),
                     false_by_state={s: int((off & (r['state'][r['ix']] == s)).sum()) for s in ('green', 'orange')})
            # the line net's own response to near-street text and other text
            tx = L['bins'] == 8; nst = L['nst'] > 0
            o['line_net_on_text'] = dict(near_street_mean_P=round(float(lmap[nst].mean()) / 255, 4), near_street_share_P_gt_half=round(float((lmap[nst] > 127).mean()), 4),
                                        far_text_mean_P=round(float(lmap[tx & ~nst].mean()) / 255, 4), far_text_share_P_gt_half=round(float((lmap[tx & ~nst] > 127).mean()), 4),
                                        block_line_ink_mean_P=round(float(lmap[L['bins'] == 1].mean()) / 255, 4), block_line_ink_share_P_gt_half=round(float((lmap[L['bins'] == 1] > 127).mean()), 4),
                                        lot_line_ink_mean_P=round(float(lmap[L['bins'] == 2].mean()) / 255, 4), lot_line_share_P_gt_half=round(float((lmap[L['bins'] == 2] > 127).mean()), 4))
            # false blocks: kind and the sides off Ben's lines
            fps = js['blocks']['fp_p']; pa = np.array(js['blocks']['pa'])
            fb = []
            for j in fps:
                m = inst == j; area = int(m.sum()) * 4
                ing = float((gt[m] > 0).mean()); ind = float(dec[m].mean()); nb = len(set(np.unique(gt[m]).tolist()) - {0})
                ys_, xs_ = np.nonzero(m); cen = [float(xs_.mean() * 2), float(ys_.mean() * 2)]
                fb.append(dict(id=j, area=area, share_in_ben_blocks=round(ing, 3), share_decided=round(ind, 3), ben_blocks_touched=nb, centroid=[round(cen[0]), round(cen[1])],
                               kind='piece of a Ben block' if ing >= 0.7 else ('street ground as block' if ing <= 0.3 else 'mixed'),
                               bbox=[int(xs_.min() * 2), int(ys_.min() * 2), int(xs_.max() * 2 + 2), int(ys_.max() * 2 + 2)]))
            if fps:
                SPp, SPd, own = side_samples(polys, fps)
                bl = B.LineSet([], 20.0, pts=(SPp, SPd, 'side')); dsb = bl.dist_to(B.LineSet([], 20.0, pts=(ben['P'], ben['Pd'], 'ben')))
                cS = classify(SPp, L, gt, dec); o['false_block_sides_off_ben'] = table(cS, dsb > 5); o['false_block_sides_len'] = int(len(dsb))
            else: o['false_block_sides_off_ben'] = dict(n=0); o['false_block_sides_len'] = 0
            o['false_blocks'] = fb
            o['blocks'] = {k: js['blocks'][k] for k in ('PQ', 'matched', 'fp', 'merges')}
            o['merged_gt'] = js['blocks']['merged_gt']
            # Ben's lines missed (all, not only lost)
            db = r['db']; miss = db > 5
            o['missed_interior'] = table(bc, miss & interior)
            o['missed_interior_partner_lt75'] = int((miss & interior & (part < 75)).sum())
            if step != 'baseline':
                b = base[g]; boff = b['dp'] > 5
                # new false: pair false samples far from every baseline false sample
                pf = B.LineSet([], 20.0, pts=(r['P'][off], r['Pd'][off], 'p')); bf = B.LineSet([], 20.0, pts=(b['P'][boff], b['Pd'][boff], 'b'))
                d1 = pf.dist_to(bf); d2 = bf.dist_to(pf)
                new = np.zeros(len(off), bool); new[np.nonzero(off)[0]] = d1 > 5
                fixed = np.zeros(len(boff), bool); fixed[np.nonzero(boff)[0]] = d2 > 5
                o['new_false'] = table(cP, new)
                o['new_false_by_state'] = {s: int((new & (r['state'][r['ix']] == s)).sum()) for s in ('green', 'orange')}
                cB = classify(b['P'], L, gt, dec); o['fixed_false'] = table(cB, fixed)
                # line net P at the new false samples: this pair's map against the baseline's
                bl_map = cv2.imread(EV + f'baseline/maps44/grid{g}/44_lines.png', 0)
                o['new_false_lineP'] = dict(pair_mean=round(float(win(lmap, r['P'][new], 2).max(1).mean()) / 255, 4) if new.any() else None,
                                            baseline_mean=round(float(win(bl_map, r['P'][new], 2).max(1).mean()) / 255, 4) if new.any() else None)
                lost = (b['db'] <= 5) & (r['db'] > 5); gained = (b['db'] > 5) & (r['db'] <= 5)
                o['lost'] = table(bc, lost & interior); o['gained'] = table(bc, gained & interior)
                o['lost_sheet_edge'] = int((lost & (ben['lab'] == 'sheet_edge')).sum()); o['gained_sheet_edge'] = int((gained & (ben['lab'] == 'sheet_edge')).sum())
                o['lost_by_kind'] = {k: int((lost & (ben['lab'] == k)).sum()) for k in ('printed', 'drawn', 'sheet_edge')}
                o['lost_partner_lt75'] = int((lost & interior & (part < 75)).sum()); o['gained_partner_lt75'] = int((gained & interior & (part < 75)).sum())
                Pl = ben['P'][lost & interior]
                bam = cv2.imread(EV + f'baseline/maps44/grid{g}/44_area.png', 0)
                if len(Pl):
                    nrm = np.c_[-ben['Pd'][lost & interior][:, 1], ben['Pd'][lost & interior][:, 0]]
                    def across(am):
                        a1 = at(am, Pl + 14 * nrm, 0.5).astype(int); a2 = at(am, Pl - 14 * nrm, 0.5).astype(int)
                        return dict(both_sides_block=round(float(((a1 > 127) & (a2 > 127)).mean()), 4), one_side_block=round(float(((a1 > 127) ^ (a2 > 127)).mean()), 4), both_street=round(float(((a1 <= 127) & (a2 <= 127)).mean()), 4))
                    o['lost_lineP'] = dict(pair_mean=round(float(win(lmap, Pl, 2).max(1).mean()) / 255, 4), baseline_mean=round(float(win(bl_map, Pl, 2).max(1).mean()) / 255, 4),
                                           pair_share_gt_half=round(float((win(lmap, Pl, 2).max(1) > 127).mean()), 4), baseline_share_gt_half=round(float((win(bl_map, Pl, 2).max(1) > 127).mean()), 4))
                    o['lost_area_across'] = dict(pair=across(amap), baseline=across(bam))
                # new false blocks
                bfp = b['js']['blocks']['fp_p']; binst = b['inst']
                for f in fb:
                    m = inst == f['id']; best = 0.0
                    for j in np.unique(binst[m]):
                        if j == 0 or j not in bfp: continue
                        mb = binst == j; iou = (m & mb).sum() / max(1, (m | mb).sum()); best = max(best, float(iou))
                    f['best_iou_with_baseline_fp'] = round(best, 3); f['new'] = best <= 0.5
                bm = {tuple(v) for v in b['js']['blocks']['merged_gt'].values()}; pm = {tuple(v) for v in js['blocks']['merged_gt'].values()}
                o['merges_new'] = [list(v) for v in pm - bm]; o['merges_gone'] = [list(v) for v in bm - pm]
                bt = set(int(k) for k in b['js']['blocks']['tp']); pt = set(int(k) for k in js['blocks']['tp'])
                o['ben_blocks_lost'] = sorted(bt - pt); o['ben_blocks_won'] = sorted(pt - bt)
                keep[(step, g)] = dict(new=new, lost=lost, fixed=fixed)
                np.savez_compressed(HERE + f'runs/{step}_g{g}_diff.npz', new=new, lost=lost, fixed=fixed, gained=gained)
            res['runs'][f'{step}_g{g}'] = o
            print(step, g, 'false', o['false_len'], 'new', o.get('new_false', {}).get('n'), 'lost', o.get('lost', {}).get('n'), round(time.time() - t0, 1), flush=True)
    json.dump(res, open(HERE + 'census.json', 'w'), indent=1)
    print('done', round(time.time() - t0, 1))


if __name__ == '__main__':
    main()
