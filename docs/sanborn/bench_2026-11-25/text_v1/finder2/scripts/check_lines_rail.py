"""finder2 checks on Ben's checked plates (25 Nov 2026). CHECKS ONLY: nothing here feeds back into the finder.

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/finder2/scripts/check_lines_rail.py MASK_PATTERN CODES OUT.json [N ...]

MASK_PATTERN holds {plate}, e.g. bench_2026-11-25/text_v1/finder2/out/full/{plate}_text.png; CODES the values that count as
text (finder2: 2,3; finder v1 N_finder.png: 2,3,4). Plates default to 44 1A 5.

(a) Ben's line ink called text, with finder v1's own measure (text/finder/scripts/measure.py and benlines.py, imported
    read-only): ink within 1 and 3 px of Ben's printed, drawn and sheet-edge lines (44: streetmap/22-44.json; 1A and 5:
    the line editor's lines with picks22_guided/22-N/edges_ben.json), and the share called text; and his lines sampled
    every 2 px where there is ink within 2 px but all of it is text (the line would be cut there).
(b) Rail (44 and 5 only; Ben's picks22_guided/22-N/rail_ben.json, complete on both): text ink within 14 px of his railroad
    tracks and within 12 px of his streetcar tracks, as pixels and as pieces (8-connected text pieces with any pixel in the
    band). Each such piece is written to a contact sheet (OUT without .json + _rail_N.jpg) to be looked at by eye: a rail
    tick or a streetcar dash must never be text. Reads only; writes only OUT and the sheets."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
SP = os.getcwd(); V1 = os.path.join(SP, 'bench_2026-11-25', 'text', 'finder', 'scripts'); sys.path.insert(0, V1)
import measure, benlines


def samp(p, step=2.0):
    p = np.asarray(p, float); S = [p[:1]]
    for a, b in zip(p[:-1], p[1:]):
        n = max(1, int(np.ceil(np.hypot(*(b - a)) / step))); S.append(a + np.linspace(0, 1, n + 1)[1:, None] * (b - a))
    return np.vstack(S)


def rail(N, code, text, out_stem):
    H, W = code.shape; B = json.load(open(f'picks22_guided/22-{N}/rail_ben.json', encoding='utf8'))
    r = dict(complete=B.get('complete'))
    im = cv2.imread(f'cufp/22-{N}.jpg'); tiles = []
    for kind, tol in (('railroad', 14), ('streetcar', 12)):
        m = np.zeros((H, W), np.uint8)
        for t in B['tracks']:
            if t['kind'] != kind or len(t['pts']) < 2: continue
            cv2.polylines(m, [np.round(np.array(t['pts'])).astype(np.int32)], False, 1, 1)
        band = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * tol + 1, 2 * tol + 1))) > 0
        ink = code > 0; tb = text & band
        n, lb, st, _ = cv2.connectedComponentsWithStats(text.astype(np.uint8), connectivity=8)
        ids = np.unique(lb[tb]); ids = ids[ids > 0]
        r[kind] = dict(band_ink_px=int((ink & band).sum()), text_px_in_band=int(tb.sum()), share=round(float(tb.sum()) / max(1, (ink & band).sum()), 5),
                       text_pieces_touching_band=int(len(ids)), pieces=[dict(x=int(st[i, 0]), y=int(st[i, 1]), w=int(st[i, 2]), h=int(st[i, 3]), px=int(st[i, 4]),
                                                                              in_band=int((tb & (lb == i))[st[i, 1]:st[i, 1] + st[i, 3], st[i, 0]:st[i, 0] + st[i, 2]].sum())) for i in ids])
        for p in r[kind]['pieces']:
            cx, cy = p['x'] + p['w'] // 2, p['y'] + p['h'] // 2; s = max(60, p['w'], p['h']) // 2 + 20
            X0, Y0, X1, Y1 = max(0, cx - s), max(0, cy - s), min(W, cx + s), min(H, cy + s)
            a = im[Y0:Y1, X0:X1]; o = (a * 0.35 + 255 * 0.65).astype(np.uint8); o[band[Y0:Y1, X0:X1]] = (o[band[Y0:Y1, X0:X1]] * 0.8 + np.array([60, 60, 0]) * 0.2).astype(np.uint8)
            o[code[Y0:Y1, X0:X1] == 1] = (150, 150, 150); o[text[Y0:Y1, X0:X1]] = (220, 0, 220); o[(text & band)[Y0:Y1, X0:X1]] = (0, 0, 255)
            t_ = np.concatenate([a, o], 1); t_ = cv2.resize(t_, (240, 120)); cv2.putText(t_, f'{kind[0]} {p["x"]},{p["y"]}', (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)
            tiles.append(t_)
    if tiles:
        cols = 6; rows = (len(tiles) + cols - 1) // cols; sheet = np.full((rows * 122, cols * 242, 3), 255, np.uint8)
        for i, t_ in enumerate(tiles): rr, cc = divmod(i, cols); sheet[rr * 122:rr * 122 + 120, cc * 242:cc * 242 + 240] = t_
        cv2.imwrite(f'{out_stem}_rail_{N}.jpg', sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return r


if __name__ == '__main__':
    pat, codes, outp = sys.argv[1], [int(v) for v in sys.argv[2].split(',')], sys.argv[3]; plates = sys.argv[4:] or ['44', '1A', '5']
    res = {}
    for N in plates:
        code = cv2.imread(pat.replace('{plate}', N), 0); text = np.isin(code, codes)
        mapped = np.where(text, 2, np.where(code > 0, 1, 0)).astype(np.uint8)   # measure.py counts 2,3,4 as text
        r, _ = measure.measure(N, mapped, None)
        r = {k: v for k, v in r.items() if k in ('ben_lines', 'ink_px', 'text_px', 'a_line_ink_1px', 'a_line_ink_3px', 'a_by_kind_3px', 'a_length')}
        for k in ('a_line_ink_1px', 'a_line_ink_3px'): r[k].pop('by_code', None)
        if N in ('44', '5'): r['rail'] = rail(N, code, text, outp[:-5] if outp.endswith('.json') else outp)
        res[N] = r
        a1, a3, L = r['a_line_ink_1px'], r['a_line_ink_3px'], r['a_length']
        print(f"{N}: Ben line ink called text: 1 px {a1['called_text_px']}/{a1['line_ink_px']} = {a1['share']:.4%}; 3 px {a3['called_text_px']}/{a3['line_ink_px']} = {a3['share']:.4%}; "
              f"line cut at {L['finder_cut']}/{L['inked']} samples = {L['finder_cut_share']:.4%}", flush=True)
        if 'rail' in r:
            for kd in ('railroad', 'streetcar'):
                q = r['rail'][kd]; print(f"   {kd}: text px in band {q['text_px_in_band']} ({q['share']:.4%} of band ink), text pieces touching band {q['text_pieces_touching_band']}")
    json.dump(res, open(outp, 'w', encoding='utf8', newline='\n'), indent=1)
