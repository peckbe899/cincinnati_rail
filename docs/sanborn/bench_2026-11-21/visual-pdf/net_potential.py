"""What the two network maps got right on the uncut PDF sheets, underneath the batch's broken outlines.

    python net_potential.py [N ...]       (default: every sheet with cufp/N/source.json)

Reads (never writes) the batch's outputs in unet_data/: N_pred_area_ng1.png (half-size P(block)), N_lines_lines_ng1.png
(full-size P(line)), N_blockmask.png (half-size: outlines.py's watershed block ground, before findContours drops the
nested regions), N_edges.json (what reached the editor).
Writes, into this folder only:
  potential/N.jpg        1/8 size, two panels: top = scan + P(block)>0.5 (green tint) + P(line)>0.5 (red);
                         bottom = what the batch exported to the editor (N_edges.json: green / orange)
  potential/N_mapmask.jpg same top panel restricted to map_area.py's map ground (off-map greyed), from maparea_check/N_mask8.png
  potential.json         per sheet: block regions in the network's own area map and in the watershed block mask,
                         counted with nesting (RETR_TREE, even depth) and inside map_area's map ground, against what was exported
"""
import glob, json, os, sys
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = D + 'unet_data/'
OUT = os.path.join(HERE, 'potential'); os.makedirs(OUT, exist_ok=True)
MIN_AREA = 6000          # outlines.py's MIN_AREA, full-size px


def pdf_plates():
    ps = [os.path.basename(os.path.dirname(p)) for p in glob.glob(D + 'cufp/*/source.json')]
    return sorted(ps, key=lambda s: (int(''.join(c for c in s if c.isdigit())), s))


def regions(b, min_area_px):
    """block regions of a binary map, nested ones included (even depth of RETR_TREE), area >= min_area_px"""
    cs, hier = cv2.findContours(b.astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if hier is None: return [], 0
    hier = hier[0]
    def depth(i):
        d = 0
        while hier[i][3] >= 0: i = hier[i][3]; d += 1
        return d
    outer = [i for i in range(len(cs)) if depth(i) % 2 == 0 and cv2.contourArea(cs[i]) >= min_area_px]
    ext = [i for i in outer if depth(i) == 0]
    return outer, len(ext)


def main(pl):
    res = {}
    if os.path.exists(os.path.join(HERE, 'potential.json')):
        res = json.load(open(os.path.join(HERE, 'potential.json')))
    for n in pl:
        full = cv2.imread(D + f'cufp/22-{n}.jpg', cv2.IMREAD_REDUCED_COLOR_2)       # half size
        h, w = full.shape[:2]
        pa = cv2.imread(U + f'{n}_pred_area_ng1.png', 0)
        pa = cv2.resize(pa, (w, h), interpolation=cv2.INTER_LINEAR)
        pl_ = cv2.imread(U + f'{n}_lines_lines_ng1.png', cv2.IMREAD_REDUCED_GRAYSCALE_2)
        pl_ = cv2.resize(pl_, (w, h), interpolation=cv2.INTER_AREA)
        bm = cv2.imread(U + f'{n}_blockmask.png', 0)
        bm = cv2.resize(bm, (w, h), interpolation=cv2.INTER_NEAREST) > 0 if bm is not None else np.zeros((h, w), bool)
        alpha = cv2.resize(np.load(D + f'cufp/{n}/png_alpha_s4.npy').astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0
        blk = (pa > 127) & alpha
        mm = None; mp = os.path.join(HERE, 'maparea_check', f'{n}_mask8.png')       # map_area.py's map ground (test_map_area.py)
        if os.path.exists(mp):
            mm = cv2.resize(cv2.imread(mp, 0), (w, h), interpolation=cv2.INTER_NEAREST) > 127
        ma = MIN_AREA / 4.0                                                       # half-size px
        o_all, e_all = regions(blk, ma)
        o_bm, e_bm = regions(bm, ma)
        row = dict(paper_px_half=int(alpha.sum()), block_share_of_paper=round(float(blk.sum() / max(1, alpha.sum())), 3),
                   area_regions_nested=len(o_all), area_regions_outermost=e_all, ws_regions_nested=len(o_bm), ws_regions_outermost=e_bm)
        if mm is not None:
            o_mm, _ = regions(blk & mm, ma)
            o_bmm, _ = regions(bm & mm, ma)
            cs = cv2.findContours((blk & mm).astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[0]
            big = max([cv2.contourArea(c) for c in cs] or [0]) / max(1, mm.sum())
            row.update(map_share_of_paper=round(float(mm.sum() / max(1, alpha.sum())), 3), block_share_of_map=round(float((blk & mm).sum() / max(1, mm.sum())), 3),
                       block_share_off_map=round(float((blk & ~mm).sum() / max(1, (alpha & ~mm).sum())), 3),
                       area_regions_in_map=len(o_mm), ws_regions_in_map=len(o_bmm), largest_area_region_share_of_map=round(float(big), 3))
        ed = json.load(open(U + f'{n}_edges.json')) if os.path.exists(U + f'{n}_edges.json') else []
        bj = json.load(open(U + f'{n}_blocks_ng.json')) if os.path.exists(U + f'{n}_blocks_ng.json') else {}
        row.update(exported_blocks=bj.get('blocks'), exported_sides=len(ed), exported_green=sum(e['state'] == 'green' for e in ed),
                   line_share_of_paper=round(float(((pl_ > 127) & alpha).sum() / max(1, alpha.sum())), 4))
        if mm is not None:
            row['line_share_off_map'] = round(float(((pl_ > 127) & alpha & ~mm).sum() / max(1, ((pl_ > 127) & alpha).sum())), 3)
        res[n] = row; print(n, row, flush=True)
        # pictures at 1/8 size
        s = 0.25
        sm = lambda a, it=cv2.INTER_AREA: cv2.resize(a, None, fx=s, fy=s, interpolation=it)
        g = cv2.cvtColor(cv2.cvtColor(sm(full), cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR).astype(np.float32) * 0.75 + 50
        top = g.copy(); bb = sm(blk.astype(np.uint8), cv2.INTER_NEAREST) > 0; ll = sm(pl_) > 110
        top[bb] = top[bb] * 0.55 + np.array([60, 200, 60]) * 0.45
        top[ll] = (0, 0, 220)
        bot = g.copy()
        for e in ed:
            a = (np.array(e['a']) * s / 2).round().astype(int); b = (np.array(e['b']) * s / 2).round().astype(int)
            cv2.line(bot, tuple(a), tuple(b), (0, 160, 0) if e['state'] == 'green' else (0, 140, 255), 2, cv2.LINE_AA)
        cv2.putText(top, f'{n}  networks: P(block)>0.5 green, P(line)>0.5 red', (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 200), 2)
        cv2.putText(bot, f'{n}  batch export: {bj.get("blocks")} blocks, {len(ed)} sides', (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 200), 2)
        cv2.imwrite(os.path.join(OUT, f'{n}.jpg'), np.vstack([top, bot]).clip(0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 80])
        if mm is not None:
            t2 = top.copy(); off = sm(mm.astype(np.uint8), cv2.INTER_NEAREST) == 0
            t2[off] = t2[off] * 0.3 + 150
            cv2.imwrite(os.path.join(OUT, f'{n}_mapmask.jpg'), t2.clip(0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 80])
    json.dump(res, open(os.path.join(HERE, 'potential.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1:] or pdf_plates())
