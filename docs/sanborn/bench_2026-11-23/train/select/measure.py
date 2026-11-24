"""Selection agent (23 Nov 2026): measure every plate for choosing the pseudo-label plates. Read-only on the repo.

    python -B measure.py            (system Python: cv2, numpy)   -> plates.json, plates.csv in this folder

Per plate:
- the scan's real pixel size, read from the JPEG header of cufp/22-N.jpg (full size), and the half size;
- paper share (cufp/N/png_alpha_s4.npy), map-ground share on the PDF sheets (unet_data/N_mapground.png);
- area_ng1's P(block) (unet_data/N_pred_area_ng1.png, half size) on the paper: confident share (p <= 0.05 or p >= 0.95),
  confident street / block shares, and the street share (p < 0.5);
- the merged step's blocks (unet_data/N_blockmask.png, half size): block share of the paper, and where it disagrees
  with a confident area pixel;
- lines_ng1 (unet_data/N_lines_lines_ng1.png, full size): share of paper drawn (p > 0.5) and the share of drawn line
  pixels that are unsure (0.3 < p < 0.7);
- the merged step's record (unet_data/N_blocks_ng.json): blocks, holes, suspect, share on a printed line, editor per line;
- census fields (data/sanborn/bench_2026-11-21/census/census.csv) and the scale table (data/sanborn/scale_table.json).
"""
import csv, json, os, struct, sys, time
import numpy as np
import cv2

SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
U = SP + 'unet_data/'
OUT = os.path.dirname(os.path.abspath(__file__))


def jpeg_size(path):
    with open(path, 'rb') as f:
        if f.read(2) != b'\xff\xd8': raise ValueError('not a jpeg')
        while True:
            m = f.read(2)
            while m[0] != 0xFF: m = m[1:] + f.read(1)
            while m[1] == 0xFF: m = m[:1] + f.read(1)
            code = m[1]; L = struct.unpack('>H', f.read(2))[0]
            if code in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                f.read(1); h, w = struct.unpack('>HH', f.read(4)); return w, h
            f.seek(L - 2, 1)


def main():
    census = {r['plate']: r for r in csv.DictReader(open(SP + 'bench_2026-11-21/census/census.csv', encoding='utf8'))}
    scale = json.load(open(SP + 'scale_table.json', encoding='utf8'))
    run = json.load(open(U + 'run_plates.json', encoding='utf8'))
    rows = []
    for N, c in census.items():
        t0 = time.time(); r = dict(plate=N)
        jp = SP + f'cufp/22-{N}.jpg'; W, H = jpeg_size(jp); r.update(W=W, H=H, full_mpx=round(W * H / 1e6, 2), half_W=W // 2, half_H=H // 2)
        r['source'] = c['source']; r['ft_per_inch'] = scale[N]['ft_per_inch']; r['inset'] = scale[N]['inset']
        for k in ('paper_share', 'tinted_share', 'area_unsure_share', 'ground_acres', 'railroad_ink_share', 'streetcar_ink_share', 'px_per_ft', 'eye_check', 'failure_modes', 'blocks_exported'):
            r['census_' + k] = c[k]
        rp = run.get(N, {}); r['run_blocks_msg'] = rp.get('blocks', '')
        bj = U + f'{N}_blocks_ng.json'
        if os.path.exists(bj):
            b = json.load(open(bj, encoding='utf8'))
            r.update(merged_blocks=b['blocks'], merged_holes=b['holes'], merged_sides=b['sides'], merged_green=b['green'], merged_bridges=b['bridges'],
                     merged_on_rail=b['on_rail'], merged_on_print_len=b['share_on_printed_line_by_length'], suspect=b['suspect'], suspect_why='; '.join(b['suspect_why']),
                     editor_per_line=b['qa'].get('editor_per_line'), nested_regions=b['qa'].get('nested_regions'), map_ground_share_of_paper=b['qa'].get('map_ground_share_of_paper'))
        else:
            r.update(merged_blocks=None, suspect=None)
        # paper, at half size
        a4 = np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.uint8)
        hw, hh = W // 2, H // 2
        pa = cv2.imread(U + f'{N}_pred_area_ng1.png', 0)
        if pa is None: rows.append(r); continue
        hh, hw = pa.shape
        paper = cv2.resize(a4, (hw, hh), interpolation=cv2.INTER_NEAREST) > 0
        mg = U + f'{N}_mapground.png'
        if os.path.exists(mg):
            m = cv2.resize(cv2.imread(mg, 0), (hw, hh), interpolation=cv2.INTER_NEAREST) > 127
            ground = paper & m; r['mapground_share_of_paper'] = round(float(ground.sum() / max(1, paper.sum())), 3)
        else:
            ground = paper; r['mapground_share_of_paper'] = None
        n = max(1, int(ground.sum())); p = pa[ground]
        r['paper_half_mpx'] = round(paper.sum() / 1e6, 3); r['ground_half_mpx'] = round(n / 1e6, 3)
        conf_b = p >= 243; conf_s = p <= 12
        r['area_conf_share'] = round(float((conf_b | conf_s).sum() / n), 3); r['area_conf_block'] = round(float(conf_b.sum() / n), 3); r['area_conf_street'] = round(float(conf_s.sum() / n), 3)
        r['area_street_share'] = round(float((p < 128).sum() / n), 3)
        r['area_conf_half_mpx'] = round(float((conf_b | conf_s).sum() / 1e6), 3)
        bm = cv2.imread(U + f'{N}_blockmask.png', 0)
        if bm is not None:
            bmb = bm[ground] > 127
            r['merged_block_share'] = round(float(bmb.mean()), 3)
            r['conf_street_in_merged_block'] = round(float((conf_s & bmb).sum() / max(1, conf_s.sum())), 3)   # confident street the merged blocks swallow
            r['conf_block_outside_merged'] = round(float((conf_b & ~bmb).sum() / max(1, conf_b.sum())), 3)     # confident block the merged blocks leave out
            r['agree_conf_and_merged'] = round(float(((conf_b & bmb) | (conf_s & ~bmb)).sum() / max(1, (conf_b | conf_s).sum())), 3)
        ln = cv2.imread(U + f'{N}_lines_lines_ng1.png', 0)
        if ln is not None:
            gl = cv2.resize(ground.astype(np.uint8), (ln.shape[1], ln.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
            q = ln[gl]; drawn = q > 127
            r['line_drawn_share'] = round(float(drawn.mean()), 4)
            r['line_unsure_of_drawn'] = round(float(((q > 76) & (q < 179)).sum() / max(1, ((q > 76)).sum())), 3)
        r['seconds'] = round(time.time() - t0, 1)
        rows.append(r); print(N, {k: r.get(k) for k in ('full_mpx', 'ft_per_inch', 'area_conf_share', 'merged_block_share', 'agree_conf_and_merged', 'line_drawn_share', 'suspect')}, flush=True)
    json.dump(rows, open(os.path.join(OUT, 'plates.json'), 'w', encoding='utf8', newline='\n'), indent=1)
    keys = []
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with open(os.path.join(OUT, 'plates.csv'), 'w', encoding='utf8', newline='') as f:
        w = csv.DictWriter(f, keys); w.writeheader(); [w.writerow(r) for r in rows]
    print('wrote', len(rows))


if __name__ == '__main__':
    main()
