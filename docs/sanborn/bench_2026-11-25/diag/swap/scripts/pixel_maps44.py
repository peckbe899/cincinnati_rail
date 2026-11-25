"""pixel_maps44.py (diag/swap, 25 Nov 2026): the networks' maps of plate 44 against Ben's street map, pixel by pixel.
System python (cv2, numpy). Reads only; writes diag/swap/pixel/pixel_maps44.json.

AREA maps (half size, P(block)*255), on the ground Ben decided (bench44's decided ground: his 55 blocks + the street
ground between them; the cache png made by bench44 for streetmap/22-44.json):
  accuracy       share of decided px where (P > 0.5) == (px in one of his blocks)
  iou_street     IoU of (P <= 0.5) with his street ground;  iou_block likewise for blocks
  meanP_street   mean P on his street ground (0 is perfect);  meanP_block  mean P on his blocks (1 is perfect)
  unsure         share of decided px with 0.2 < P < 0.8
  false_block_on_street / false_street_on_block   shares of his street / block px called the other way
  gross_*        the same, only px more than 5 half px (10 full px) from the nearest street/block boundary of his map
                 (so it is not the boundary's position but whole regions called wrong)
  void_block     share of the paper Ben did not decide (railway corridor, creek land) that is called block
LINE maps (full size, P(line)*255; drawn = P > 0.5, on the paper):
  recall_<kind>  share of Ben's line px (1 px wide, by kind: printed, drawn, sheet_edge) with a drawn px within 3 px
                 (square 7x7, as edgenet.score's TOL = 3)
  precision      share of drawn px within 3 px of any of Ben's lines;  precision_interior: of his printed + drawn only
  precision_decided  the same, drawn px on his decided ground only
  far_share      share of drawn px more than 10 px from any of his lines (lines where there is none)
  drawn_px       number of drawn px
    python -B pixel_maps44.py [--grids 0,1,2,3,4,5] [--only NAME,...]
"""
import argparse, glob, json, os, time
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
D = SP + 'bench_2026-11-25/diag/swap/'
W, H = 10768, 7219; S = 0.5; h2, w2 = int(H * S), int(W * S)
STEPS = ('V1S1', 'V1S2', 'V2S1', 'V2S2')


def configs():
    """name -> (kind, file pattern with {g}); 'lines:X|ch7=Y' = line net X fed area net Y's map as its 7th input"""
    C = {}
    C['area:ng1'] = ('area', SP + 'bench44_maps/grid{g}/44_area.png')
    C['lines:ng1|ch7=ng1'] = ('lines', SP + 'bench44_maps/grid{g}/44_lines.png')
    for s in STEPS:
        C[f'area:{s}best'] = ('area', SP + f'train_v2_runs/eval/{s}/maps44/grid{{g}}/44_area.png')
        C[f'lines:{s}best|ch7={s}best'] = ('lines', SP + f'train_v2_runs/eval/{s}/maps44/grid{{g}}/44_lines.png')
        C[f'lines:{s}best|ch7=ng1'] = ('lines', D + f'eval/a__ng1+L_{s}/maps44/grid{{g}}/44_lines.png')
        C[f'lines:ng1|ch7={s}best'] = ('lines', D + f'eval/b__A_{s}+ng1/maps44/grid{{g}}/44_lines.png')
        C[f'area:{s}last'] = ('area', D + f'eval/c__{s}_last/maps44/grid{{g}}/44_area.png')
        C[f'lines:{s}last|ch7={s}last'] = ('lines', D + f'eval/c__{s}_last/maps44/grid{{g}}/44_lines.png')
        C[f'lines:{s}last|ch7=ng1'] = ('lines', D + f'eval/c__ng1+L_{s}_last/maps44/grid{{g}}/44_lines.png')
    return C


def truth():
    sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
    gt = np.zeros((h2, w2), np.int32)
    for k, b in enumerate(sm['blocks']): cv2.fillPoly(gt, [(np.array(b['ring']) * S).round().astype(np.int32)], k + 1)
    dec = cv2.imread(glob.glob(D + 'runs_baseline44/cache/decided_half_*_260.png')[0], 0) > 0
    a4 = np.load(SP + 'cufp/44/png_alpha_s4.npy').astype(np.float32)
    alpha2 = cv2.resize(a4, (w2, h2)) > 0.5; alphaF = cv2.resize(a4, (W, H)) > 0.5
    block = gt > 0
    bd = np.where(block, cv2.distanceTransform(block.astype(np.uint8), cv2.DIST_L2, 5), cv2.distanceTransform((~block).astype(np.uint8), cv2.DIST_L2, 5))   # half px to Ben's nearest block/street boundary
    L = {k: np.zeros((H, W), np.uint8) for k in ('printed', 'drawn', 'sheet_edge')}
    for l in sm['lines']:
        cv2.line(L[l['kind']], tuple(int(round(v)) for v in l['a']), tuple(int(round(v)) for v in l['b']), 1, 1)
    K = np.ones((7, 7), np.uint8)
    anyl = (L['printed'] | L['drawn'] | L['sheet_edge']); inter = (L['printed'] | L['drawn'])
    near_any = cv2.dilate(anyl, K) > 0; near_int = cv2.dilate(inter, K) > 0
    far_any = cv2.distanceTransform((1 - anyl).astype(np.uint8), cv2.DIST_L2, 5) > 10
    decF = cv2.resize(dec.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    return dict(gt=gt, block=block, dec=dec, alpha2=alpha2, alphaF=alphaF, bd=bd, L={k: v > 0 for k, v in L.items()}, near_any=near_any, near_int=near_int, far_any=far_any, decF=decF)


def area_metrics(T, p8):
    P = p8.astype(np.float32) / 255; dec = T['dec']; blk = T['block'] & dec; st = dec & ~T['block']; pb = P > 0.5
    gross = T['bd'] > 5
    r = dict(accuracy=float((pb == T['block'])[dec].mean()),
             iou_street=float((~pb & st).sum() / max(1, ((~pb & dec) | st).sum())), iou_block=float((pb & blk).sum() / max(1, ((pb & dec) | blk).sum())),
             meanP_street=float(P[st].mean()), meanP_block=float(P[blk].mean()), unsure=float(((P > 0.2) & (P < 0.8))[dec].mean()),
             unsure_street=float(((P > 0.2) & (P < 0.8))[st].mean()), unsure_block=float(((P > 0.2) & (P < 0.8))[blk].mean()),
             false_block_on_street=float(pb[st].mean()), false_street_on_block=float((~pb)[blk].mean()),
             gross_false_block_on_street=float(pb[st & gross].mean()), gross_false_street_on_block=float((~pb)[blk & gross].mean()),
             void_block=float(pb[T['alpha2'] & ~dec].mean()), block_share_decided=float(pb[dec].mean()))
    return {k: round(v, 4) for k, v in r.items()}


def line_metrics(T, p8):
    pr = (p8 > 127) & T['alphaF']; n = int(pr.sum())
    near_pr = cv2.dilate(pr.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    r = {f'recall_{k}': float((m & near_pr).sum() / max(1, m.sum())) for k, m in T['L'].items()}
    ib = T['L']['printed'] | T['L']['drawn']; r['recall_interior'] = float((ib & near_pr).sum() / max(1, ib.sum()))
    r['precision'] = float((pr & T['near_any']).sum() / max(1, n)); r['precision_interior'] = float((pr & T['near_int']).sum() / max(1, n))
    pd = pr & T['decF']; r['precision_decided'] = float((pd & T['near_any']).sum() / max(1, pd.sum()))
    r['far_share'] = float((pr & T['far_any']).sum() / max(1, n))
    r['f1_interior'] = 2 * r['precision'] * r['recall_interior'] / max(1e-9, r['precision'] + r['recall_interior'])
    out = {k: round(v, 4) for k, v in r.items()}; out['drawn_px'] = n
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--grids', default='0,1,2,3,4,5'); ap.add_argument('--only', default=''); ap.add_argument('--out', default=D + 'pixel/pixel_maps44.json')
    a = ap.parse_args(); grids = [int(g) for g in a.grids.split(',')]; only = set(x for x in a.only.split(',') if x)
    t0 = time.time(); T = truth(); print('truth', round(time.time() - t0, 1), 's', flush=True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    res = json.load(open(a.out)) if os.path.exists(a.out) else {}
    res.setdefault('_meta', {})['made'] = time.strftime('%Y-%m-%d %H:%M:%S'); res['_meta']['doc'] = __doc__
    for name, (kind, pat) in configs().items():
        if only and name not in only: continue
        per = {}
        for g in grids:
            f = pat.format(g=g)
            if not os.path.exists(f): continue
            m = cv2.imread(f, 0); per[f'grid{g}'] = (area_metrics if kind == 'area' else line_metrics)(T, m)
        if not per: print('missing', name, flush=True); continue
        keys = per[next(iter(per))].keys()
        mean = {k: round(float(np.mean([per[g][k] for g in per])), 4) for k in keys}
        res[name] = dict(kind=kind, files=pat, grids=sorted(per), mean=mean, per_grid=per)
        print(name, json.dumps(mean), flush=True)
        tmp = a.out + '.tmp'; json.dump(res, open(tmp, 'w'), indent=1); os.replace(tmp, a.out)


if __name__ == '__main__':
    main()
