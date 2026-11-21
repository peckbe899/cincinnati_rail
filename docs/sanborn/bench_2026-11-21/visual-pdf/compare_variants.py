"""Batch against the fixed outline step, sheet by sheet, on the uncut PDF sheets.

    python compare_variants.py     -> compare_variants.json, printed table, compare/N.jpg (batch export | ccomp+mask export)

Columns: the batch (unet_data/N_blocks_ng.json, N_edges.json), the copy run as the batch ran it (variants/external, a
reproduction check), RETR_CCOMP alone (variants/ccomp), RETR_CCOMP + map_area mask (variants/ccomp_mask).
For each: blocks, exported sides (what the line editor would get: no short, no paper-edge), green (on a printed line),
and the largest block's share of map ground (map_area's mask) as a 'one giant block' check.
These counts are not quality scores: there is no ground truth on any PDF sheet.
"""
import glob, json, os
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = D + 'unet_data/'
OUT = os.path.join(HERE, 'compare'); os.makedirs(OUT, exist_ok=True)


def largest_share(bm_path, mm):
    if not os.path.exists(bm_path): return None
    b = cv2.imread(bm_path, 0) > 0; h, w = b.shape
    m = cv2.resize(mm.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0
    n, cc, st, _ = cv2.connectedComponentsWithStats(b.astype(np.uint8), connectivity=4)
    return round(float(st[1:, cv2.CC_STAT_AREA].max() / max(1, m.sum())), 3) if n > 1 else 0.0


def draw(n, edges, s=0.125):
    im = cv2.imread(D + f'cufp/22-{n}.jpg', cv2.IMREAD_REDUCED_COLOR_8)
    g = cv2.cvtColor(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR).astype(np.float32) * 0.6 + 90
    g = g.astype(np.uint8)
    for e in edges:
        a = tuple((np.array(e['a']) * s).round().astype(int)); b = tuple((np.array(e['b']) * s).round().astype(int))
        cv2.line(g, a, b, (0, 160, 0) if e['state'] == 'green' else (0, 140, 255), 2, cv2.LINE_AA)
    return g


if __name__ == '__main__':
    pl = sorted([os.path.basename(os.path.dirname(p)) for p in glob.glob(D + 'cufp/*/source.json')], key=lambda s: int(''.join(c for c in s if c.isdigit())))
    sc = json.load(open(os.path.join(HERE, 'scale_table.json'))); res = {}
    for n in pl:
        mm = cv2.imread(os.path.join(HERE, 'maparea_check', f'{n}_mask8.png'), 0) > 127
        ed = json.load(open(U + f'{n}_edges.json')); bj = json.load(open(U + f'{n}_blocks_ng.json'))
        row = dict(ft_per_inch=sc[n]['ft_per_inch'], batch=dict(blocks=bj['blocks'], sides=len(ed), green=sum(e['state'] == 'green' for e in ed),
                                                             largest_block_share_of_map=largest_share(U + f'{n}_blockmask.png', mm)))
        for v in ('external', 'ccomp', 'ccomp_mask'):
            f = os.path.join(HERE, 'variants', v, f'{n}_outlines.json')
            if not os.path.exists(f): continue
            r = json.load(open(f))
            row[v] = dict(blocks=r['blocks'], holes=r.get('holes', 0), sides=r['exported_sides'], green=r['exported_green'],
                          largest_block_share_of_map=largest_share(os.path.join(HERE, 'variants', v, f'{n}_blockmask.png'), mm))
        if 'external' in row:
            ee = json.load(open(os.path.join(HERE, 'variants', 'external', f'{n}_edges.json')))
            row['external_reproduces_batch'] = (row['external']['blocks'] == row['batch']['blocks'] and len(ee) == len(ed) and
                                                all(np.allclose(a['a'], b['a']) and np.allclose(a['b'], b['b']) for a, b in zip(ee, ed)))
        if 'ccomp_mask' in row:
            em = json.load(open(os.path.join(HERE, 'variants', 'ccomp_mask', f'{n}_edges.json')))
            a, b = draw(n, ed), draw(n, em)
            cv2.putText(a, f'{n} batch: {row["batch"]["blocks"]} blocks, {len(ed)} sides', (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 200), 2)
            cv2.putText(b, f'{n} ccomp+mask: {row["ccomp_mask"]["blocks"]} blocks, {len(em)} sides', (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 200), 2)
            cv2.imwrite(os.path.join(OUT, f'{n}.jpg'), np.vstack([a, b]), [cv2.IMWRITE_JPEG_QUALITY, 80])
        res[n] = row
        print(n, row['ft_per_inch'], 'batch', row['batch'], '| ccomp', row.get('ccomp'), '| ccomp_mask', row.get('ccomp_mask'), '| repro', row.get('external_reproduces_batch'), flush=True)
    json.dump(res, open(os.path.join(HERE, 'compare_variants.json'), 'w'), indent=1)
    for k in ('batch', 'ccomp', 'ccomp_mask'):
        rows = [r[k] for r in res.values() if k in r]
        if not rows: continue
        print(f"{k:10s}: blocks total {sum(r['blocks'] for r in rows)}, sides {sum(r['sides'] for r in rows)}, green {sum(r['green'] for r in rows)}, "
              f"sheets with <= 5 blocks {sum(r['blocks'] <= 5 for r in rows)}, sheets whose largest block > 30% of map {sum((r['largest_block_share_of_map'] or 0) > 0.3 for r in rows)}")
