"""merge/impl: the merged outline step on the 104 unplaced plates of the batch, from the batch's saved maps (21 Nov 2026).

    python -B batch104.py run [--jobs 5] [N ...]     the staged outlines.py --out merge/impl/plates/N/ (venv, CPU)
    python -B batch104.py measure                     -> merge/impl/batch104.json (per plate) and batch104_summary.json

The outline step reads unet_data/N_pred_area_ng1.png, N_lines_lines_ng1.png and N_bins.png (the batch's ink bins,
made before any block step: on these plates their rail bins are the rules' with no blocks at all), exactly what a
plain run_plates.py redo would read. Nothing is written outside merge/impl.
Per plate (as outline-nesting/measure.py, so the 'batch' and 'final' (outline-nesting) columns of its measure.json
compare like with like): blocks, holes, sides_all, exported (= step 4 = N_edges.json), editor_lines (edit_server.clean
of those), green share (by count and length), edge_lines (editor lines with their middle within 150 px of the paper's
edge), on_rail, bridges, editor_per_line, suspect and why, seconds.
Groups: cut 100 ft, cut 200 ft, PDF 200 ft, 400 ft (cut 93A, 93B and the 8 PDF sheets), by data/sanborn/scale_table.json
and cufp/N/source.json.
"""
import concurrent.futures as cf, json, os, sys, time
import numpy as np
import cv2
import common as C
GUIDED = {'43', '44', '45', '80', '82A'}
ST = json.load(open(C.U + 'run_plates.json', encoding='utf8'))
PL = sorted((n for n in ST if n not in GUIDED), key=lambda n: (int(''.join(c for c in n if c.isdigit())), n))
SCALE = json.load(open(C.STAGED + 'data/sanborn/scale_table.json', encoding='utf8'))
MEAS = json.load(open(C.DATA + 'bench_2026-11-21/outline-nesting/measure.json', encoding='utf8'))
OUT = C.IMPL + 'plates/'


def is_pdf(n):
    f = C.DATA + f'cufp/{n}/source.json'; return os.path.exists(f) and json.load(open(f, encoding='utf8')).get('source') == 'pdf'


def group(n):
    ft = (SCALE.get(n) or {}).get('ft_per_inch')
    if ft == 400: return '400 ft'
    return f"{'PDF' if is_pdf(n) else 'cut'} {ft} ft"


def run_one(n):
    d = OUT + n + '/'
    if os.path.exists(d + 'outlines.json') and os.path.exists(d + f'{n}_outlines.json') and '--again' not in sys.argv: return n, 'had'
    t = time.time()
    try: rep = C.outlines(n, d)
    except Exception as e: return n, f'FAILED {e}'
    json.dump(dict(wall_seconds=round(time.time() - t, 1)), open(d + 'wall.json', 'w')); return n, f"{rep['blocks']} blocks, {round(time.time() - t)} s"


def measure():
    BN = C.step4_mod(); ES = C.edit_server(); rows = {}
    L = lambda e: float(np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1]))
    for n in PL:
        d = OUT + n + '/'; polys = json.load(open(d + 'outlines.json', encoding='utf8')); rep = json.load(open(d + f'{n}_outlines.json', encoding='utf8'))
        edges = BN.step4(polys); shown = ES.clean(edges) if edges else []
        al = np.load(C.DATA + f'cufp/{n}/png_alpha_s4.npy').astype(np.uint8)
        dist = cv2.distanceTransform(cv2.copyMakeBorder(al, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0), cv2.DIST_L2, 5)[1:-1, 1:-1] * 4
        d_at = lambda x, y: float(dist[int(np.clip(y / 4, 0, dist.shape[0] - 1)), int(np.clip(x / 4, 0, dist.shape[1] - 1))])
        g = [e for e in edges if e['state'] == 'green']; tl = sum(L(e) for e in edges)
        holes = [p for p in polys if p and p[0].get('hole')]
        rows[n] = dict(plate=n, group=group(n), editor_len=round(sum(L(e) for e in shown)), blocks=rep['blocks'], holes=rep['holes'], sides_all=sum(len(p) for p in polys), exported=len(edges), exported_len=round(tl),
                       editor_lines=len(shown), green_share=round(len(g) / len(edges), 3) if edges else None, green_share_len=round(sum(L(e) for e in g) / tl, 3) if tl else None,
                       edge_lines=sum(1 for e in edges if d_at((e['a'][0] + e['b'][0]) / 2, (e['a'][1] + e['b'][1]) / 2) <= 150),
                       hole_sides_exported=sum(1 for p in holes for s in p if s['state'] not in ('short', 'not on a line', 'on rail') and not s.get('paper_edge')),
                       on_rail=rep['on_rail'], on_rail_len=round(sum(L(s) for p in polys for s in p if s['state'] == 'on rail' and not s.get('paper_edge'))), bridges=rep['bridges'],
                       editor_per_line=rep['qa'].get('editor_per_line'), nested_regions=rep['qa'].get('nested_regions'), suspect=rep['suspect'], why='; '.join(rep['suspect_why']),
                       map_ground=rep['map_ground'], rail=rep['rail'], seconds=rep.get('seconds'), wall_seconds=json.load(open(d + 'wall.json'))['wall_seconds'] if os.path.exists(d + 'wall.json') else None,
                       batch={k: MEAS[n]['batch'].get(k) for k in ('blocks', 'holes', 'exported', 'exported_len', 'editor_lines', 'green_share', 'edge_lines', 'suspect', 'why')},
                       nesting={k: MEAS[n]['final'].get(k) for k in ('blocks', 'holes', 'exported', 'exported_len', 'editor_lines', 'green_share', 'edge_lines', 'suspect', 'why')})
    json.dump(rows, open(C.IMPL + 'batch104.json', 'w'), indent=1)
    S = {}
    for gname in ('cut 100 ft', 'cut 200 ft', 'PDF 200 ft', '400 ft'):
        R = [r for r in rows.values() if r['group'] == gname]
        tot = lambda k, src=None: sum((r[src][k] if src else r[k]) or 0 for r in R)
        med = lambda k, src=None: round(float(np.median([(r[src][k] if src else r[k]) for r in R if (r[src][k] if src else r[k]) is not None])), 3)
        S[gname] = dict(plates=len(R), list=' '.join(r['plate'] for r in R),
                        merged=dict(blocks=tot('blocks'), holes=tot('holes'), exported=tot('exported'), exported_len=tot('exported_len'), editor_lines=tot('editor_lines'), green_share_median=med('green_share'), edge_lines=tot('edge_lines'),
                                    on_rail=tot('on_rail'), on_rail_len=tot('on_rail_len'), bridges=tot('bridges'), le5_blocks=sum(r['blocks'] <= 5 for r in R),
                                    suspect=[r['plate'] for r in R if r['suspect']], seconds_median=med('seconds'), seconds_max=max(r['seconds'] for r in R), wall_median=med('wall_seconds')),
                        batch=dict(blocks=tot('blocks', 'batch'), exported=tot('exported', 'batch'), exported_len=tot('exported_len', 'batch'), editor_lines=tot('editor_lines', 'batch'), green_share_median=med('green_share', 'batch'), edge_lines=tot('edge_lines', 'batch'),
                                   le5_blocks=sum(r['batch']['blocks'] <= 5 for r in R), suspect=[r['plate'] for r in R if r['batch']['suspect']]),
                        nesting=dict(blocks=tot('blocks', 'nesting'), holes=tot('holes', 'nesting'), exported=tot('exported', 'nesting'), exported_len=tot('exported_len', 'nesting'), editor_lines=tot('editor_lines', 'nesting'), green_share_median=med('green_share', 'nesting'),
                                     edge_lines=tot('edge_lines', 'nesting'), le5_blocks=sum(r['nesting']['blocks'] <= 5 for r in R), suspect=[r['plate'] for r in R if r['nesting']['suspect']]))
    S['all 104'] = dict(suspect=[r['plate'] for r in rows.values() if r['suspect']], suspect_why={r['plate']: r['why'] for r in rows.values() if r['suspect']},
                        seconds_total=round(sum(r['seconds'] for r in rows.values())), seconds_median=round(float(np.median([r['seconds'] for r in rows.values()])), 1))
    json.dump(S, open(C.IMPL + 'batch104_summary.json', 'w'), indent=1); print(json.dumps(S, indent=1))


if __name__ == '__main__':
    if sys.argv[1] == 'run':
        jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 5
        want = [a for i, a in enumerate(sys.argv[2:], 2) if not a.startswith('--') and sys.argv[i - 1] != '--jobs'] or PL
        want = [n for n in want if n in PL]; t = time.time()
        with cf.ThreadPoolExecutor(jobs) as ex:
            for n, msg in ex.map(run_one, want): print(n, msg, flush=True)
        print('all', round(time.time() - t), 's')
    else: measure()
