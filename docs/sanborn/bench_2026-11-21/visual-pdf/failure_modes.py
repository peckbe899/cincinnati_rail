"""Failure modes that remain on the uncut PDF sheets after the two outline fixes (RETR_CCOMP + map_area mask).

    python failure_modes.py          -> failure_modes.json, printed table

For every sheet, from the batch's own network maps (unet_data/N_pred_area_ng1.png, N_lines_lines_ng1.png), map_area's
map ground (maparea_check/N_mask8.png) and the fixed outline run (variants/ccomp_mask/N_outlines_poly.json):
- scale (scale_table.json, read by eye), px per ft (200 ft/in = 1.52 px/ft measured on 19's bar; 400 ft/in = 0.74 on 47's)
- street share of map ground (area net P(block) <= 0.5) and the street corridors' median width in ft (2 x distance
  transform on the street skeleton, half-size px -> ft): do the networks still see streets at 400 ft to the inch?
- line share of map ground (line net P > 0.5)
- blocks of the fixed run; blocks of more than OPEN_ACRES acres and their share of block ground (open land called block)
- the paper seam: the vertical fold at the sheet's middle; line-net share in a 60-px band on the seam against the sheet
- inset regions (map_area regions other than the largest) and their scale against the main map
All numbers are measured on the batch's outputs; none is ground truth (only plate 44 has that, and it is not a PDF sheet).
"""
import glob, json, os
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = D + 'unet_data/'
SCALE = json.load(open(os.path.join(HERE, 'scale_table.json')))
PX_PER_FT = {200: 1.52, 400: 0.74}
OPEN_ACRES = 20.0


def skel_width(street):
    """median corridor width (px) of a binary street mask: 2 x distance transform sampled on its ridge"""
    dt = cv2.distanceTransform(street.astype(np.uint8), cv2.DIST_L2, 5)
    ridge = (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8)) - 1e-6) & (dt >= 2)
    v = dt[ridge]
    return float(2 * np.median(v)) if v.size else 0.0, v


def main():
    pl = sorted([os.path.basename(os.path.dirname(p)) for p in glob.glob(D + 'cufp/*/source.json')], key=lambda s: int(''.join(c for c in s if c.isdigit())))
    res = {}
    for n in pl:
        sc = SCALE[n]['ft_per_inch']; ppf = PX_PER_FT[sc]
        pa = cv2.imread(U + f'{n}_pred_area_ng1.png', 0); h, w = pa.shape                      # half size
        pl_ = cv2.resize(cv2.imread(U + f'{n}_lines_lines_ng1.png', cv2.IMREAD_REDUCED_GRAYSCALE_2), (w, h), interpolation=cv2.INTER_AREA)
        mm = cv2.resize(cv2.imread(os.path.join(HERE, 'maparea_check', f'{n}_mask8.png'), 0), (w, h), interpolation=cv2.INTER_NEAREST) > 127
        street = (pa <= 127) & mm; mapn = max(1, mm.sum())
        wpx, _ = skel_width(street)
        row = dict(ft_per_inch=sc, map_px_half=int(mapn), street_share_of_map=round(float(street.sum() / mapn), 3),
                   street_width_median_half_px=round(wpx, 1), street_width_median_ft=round(wpx * 2 / ppf, 1),
                   line_share_of_map=round(float(((pl_ > 127) & mm).sum() / mapn), 4))
        # paper seam (the fold between the two half-sheets): column of the brightest/most uniform vertical band near W/2
        W2 = w // 2; band = 30
        col = ((pl_ > 127) & mm)[:, W2 - 400:W2 + 400].mean(0)
        row['seam_line_share'] = round(float(col[400 - band:400 + band].mean()), 4)
        row['offseam_line_share'] = round(float(np.r_[col[:400 - band], col[400 + band:]].mean()), 4)
        # the fixed outline run
        fp = os.path.join(HERE, 'variants', 'ccomp_mask', f'{n}_outlines_poly.json')
        if os.path.exists(fp):
            polys = json.load(open(fp)); bm = cv2.imread(os.path.join(HERE, 'variants', 'ccomp_mask', f'{n}_blockmask.png'), 0) > 0
            ncc, cc, st, _ = cv2.connectedComponentsWithStats(bm.astype(np.uint8), connectivity=4)
            areas_ac = st[1:, cv2.CC_STAT_AREA] * 4 / (ppf * ppf) / 43560.0                       # half-size px -> full px -> acres
            big = areas_ac >= OPEN_ACRES
            rep = json.load(open(os.path.join(HERE, 'variants', 'ccomp_mask', f'{n}_outlines.json')))
            row.update(fixed_blocks=rep['blocks'], fixed_holes=rep['holes'], fixed_exported_sides=rep['exported_sides'], fixed_green=rep['exported_green'],
                       block_regions=int(ncc - 1), block_acres_median=round(float(np.median(areas_ac)), 1) if areas_ac.size else None,
                       regions_over_open_acres=int(big.sum()), share_of_block_ground_in_them=round(float(areas_ac[big].sum() / max(1e-9, areas_ac.sum())), 3),
                       largest_block_acres=round(float(areas_ac.max()), 1) if areas_ac.size else None)
        ins = [x for x in SCALE[n]['insets'] if isinstance(x.get('ft_per_inch'), int) and x['ft_per_inch'] != sc]
        row['insets_at_other_scale'] = [f"{x['where']}: {x['ft_per_inch']} ft/in" for x in ins]
        res[n] = row; print(n, row, flush=True)
    json.dump(res, open(os.path.join(HERE, 'failure_modes.json'), 'w'), indent=1)
    for sc in (200, 400):
        g = [v for v in res.values() if v['ft_per_inch'] == sc]
        med = lambda k: round(float(np.median([v[k] for v in g if v.get(k) is not None])), 3)
        print(f'{sc} ft/in: {len(g)} sheets | street share of map {med("street_share_of_map")} | street width {med("street_width_median_ft")} ft '
              f'({med("street_width_median_half_px")} half px) | line share {med("line_share_of_map")} | blocks {med("fixed_blocks") if g and "fixed_blocks" in g[0] else "-"} '
              f'| block ground in >{OPEN_ACRES:.0f}-acre regions {med("share_of_block_ground_in_them") if g and "share_of_block_ground_in_them" in g[0] else "-"}')


if __name__ == '__main__':
    main()
