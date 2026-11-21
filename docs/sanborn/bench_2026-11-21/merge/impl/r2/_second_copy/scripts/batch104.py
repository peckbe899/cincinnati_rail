"""merge/impl/r2: the round-2 staged block step on the 104 unplaced plates of the batch, from the batch's saved maps (21 Nov 2026).

    python -B batch104.py run TAG [--jobs 6] [--plain keep|drop] [N ...]
        TAG 'final': the staged blocks_noguide.py N --outlines-only --out r2/plates_final/N/ (venv, CPU): the path a
                     plain run_plates.py run takes (outlines.py, then step 4 -> N_edges.json)
        other TAG:   the staged outlines.py --out r2/plates_TAG/N/ with --plain (step 4 is applied by measure)
    python -B batch104.py measure TAG   -> r2/batch104_TAG.json (per plate) and r2/batch104_TAG_summary.json

The outline step reads unet_data/N_pred_area_ng1.png, N_lines_lines_ng1.png and N_bins.png (the batch's bins: never
trusted for the rail on these plates, so the rule runs in the step), as a plain run_plates.py rerun would.
Columns as merge/impl/scripts/batch104.py (round 1), so batch, outline-nesting (B), round 1 and round 2 compare like
with like: blocks, holes, exported (step 4 = N_edges.json), editor lines (edit_server.clean), green share by count,
lines within 150 px of the paper's edge, on rail, bridges, suspect and why, seconds; new: open_outlines (blocks kept
as plain outlines) and what step 4 exports of them.
"""
import concurrent.futures as cf, json, os, subprocess, sys, time
import numpy as np
import cv2
import common as C
GUIDED = {'43', '44', '45', '80', '82A'}
ST = json.load(open(C.U + 'run_plates.json', encoding='utf8'))
PL = sorted((n for n in ST if n not in GUIDED), key=lambda n: (int(''.join(c for c in n if c.isdigit())), n))
SCALE = json.load(open(C.STAGED + 'data/sanborn/scale_table.json', encoding='utf8'))
MEAS = json.load(open(C.DATA + 'bench_2026-11-21/outline-nesting/measure.json', encoding='utf8'))
R1 = json.load(open(C.IMPL1 + 'batch104.json', encoding='utf8'))
arg = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d


def is_pdf(n):
    f = C.DATA + f'cufp/{n}/source.json'; return os.path.exists(f) and json.load(open(f, encoding='utf8')).get('source') == 'pdf'


def group(n):
    ft = (SCALE.get(n) or {}).get('ft_per_inch')
    if ft == 400: return '400 ft'
    return f"{'PDF' if is_pdf(n) else 'cut'} {ft} ft"


def run_one(n, tag, plain):
    d = C.IMPL + f'plates_{tag}/{n}/'; C.must_be_mine(d)
    if os.path.exists(d + f'{n}_outlines.json') and '--again' not in sys.argv: return n, 'had'
    t = time.time(); os.makedirs(d, exist_ok=True)
    if tag == 'final':
        cmd = [C.VPY, '-B', C.SU + 'blocks_noguide.py', n, '--outlines-only', '--out', d]
    else:
        cmd = [C.VPY, '-B', C.SU + 'outlines.py', n, 'area_ng1', 'lines_ng1', '--out', d, '--area-png', C.U + f'{n}_pred_area_ng1.png', '--lines-png', C.U + f'{n}_lines_lines_ng1.png', '--plain', plain]
    r = subprocess.run(cmd, cwd=C.DATA, capture_output=True, text=True, encoding='utf8', errors='replace', env=C.env())
    open(d + 'stdout.txt', 'w', encoding='utf8').write(r.stdout); open(d + 'stderr.txt', 'w', encoding='utf8').write(r.stderr)
    json.dump(dict(wall_seconds=round(time.time() - t, 1), rc=r.returncode), open(d + 'wall.json', 'w'))
    return n, (f'rc {r.returncode} ' + (r.stdout.strip().splitlines() or [''])[-1][:160] if tag == 'final' else f'rc {r.returncode}') + f' {round(time.time() - t)} s'


def measure(tag):
    BN = C.step4_mod(); ES = C.edit_server(); rows = {}
    L = lambda e: float(np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1]))
    for n in PL:
        d = C.IMPL + f'plates_{tag}/{n}/'; polys = json.load(open(d + 'outlines.json', encoding='utf8')); rep = json.load(open(d + f'{n}_outlines.json', encoding='utf8'))
        edges = BN.step4(polys)
        if os.path.exists(d + f'{n}_edges.json'): assert json.load(open(d + f'{n}_edges.json', encoding='utf8')) == json.loads(json.dumps(edges)), n   # blocks_noguide's N_edges.json = step 4 of its outlines
        shown = ES.clean(edges) if edges else []
        al = np.load(C.DATA + f'cufp/{n}/png_alpha_s4.npy').astype(np.uint8)
        dist = cv2.distanceTransform(cv2.copyMakeBorder(al, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0), cv2.DIST_L2, 5)[1:-1, 1:-1] * 4
        d_at = lambda x, y: float(dist[int(np.clip(y / 4, 0, dist.shape[0] - 1)), int(np.clip(x / 4, 0, dist.shape[1] - 1))])
        g = [e for e in edges if e['state'] == 'green']; tl = sum(L(e) for e in edges)
        holes = [p for p in polys if p and p[0].get('hole')]
        openp = [p for p in polys if any(s['state'] == 'short' for s in p)]; open_e = BN.step4(openp)
        rows[n] = dict(plate=n, group=group(n), editor_len=round(sum(L(e) for e in shown)), blocks=rep['blocks'], holes=rep['holes'], open_outlines=rep.get('open_outlines'),
                       open_blocks=sum(1 for p in openp if not p[0].get('hole')), open_exported=len(open_e), open_exported_len=round(sum(L(e) for e in open_e)), open_exported_green=sum(e['state'] == 'green' for e in open_e),
                       sides_all=sum(len(p) for p in polys), exported=len(edges), exported_len=round(tl),
                       editor_lines=len(shown), green_share=round(len(g) / len(edges), 3) if edges else None, green_share_len=round(sum(L(e) for e in g) / tl, 3) if tl else None,
                       edge_lines=sum(1 for e in edges if d_at((e['a'][0] + e['b'][0]) / 2, (e['a'][1] + e['b'][1]) / 2) <= 150),
                       on_rail=rep['on_rail'], on_rail_len=round(sum(L(s) for p in polys for s in p if s['state'] == 'on rail' and not s.get('paper_edge'))), bridges=rep['bridges'],
                       not_on_line_dropped=sum(1 for p in polys for s in p if s['state'] == 'not on a line' and not s.get('paper_edge')),
                       paper_edge_sides=sum(1 for p in polys for s in p if s.get('paper_edge') and s['state'] != 'short'),
                       editor_per_line=rep['qa'].get('editor_per_line'), nested_regions=rep['qa'].get('nested_regions'), suspect=rep['suspect'], why='; '.join(rep['suspect_why']),
                       map_ground=rep['map_ground'], rail=rep['rail'], version=rep.get('version'), seconds=rep.get('seconds'),
                       wall_seconds=json.load(open(d + 'wall.json'))['wall_seconds'] if os.path.exists(d + 'wall.json') else None,
                       batch={k: MEAS[n]['batch'].get(k) for k in ('blocks', 'holes', 'exported', 'exported_len', 'editor_lines', 'green_share', 'edge_lines', 'suspect', 'why')},
                       nesting={k: MEAS[n]['final'].get(k) for k in ('blocks', 'holes', 'exported', 'exported_len', 'editor_lines', 'green_share', 'edge_lines', 'suspect', 'why')},
                       round1={k: R1[n].get(k) for k in ('blocks', 'holes', 'exported', 'exported_len', 'editor_lines', 'editor_len', 'green_share', 'edge_lines', 'on_rail', 'suspect', 'why')})
    json.dump(rows, open(C.IMPL + f'batch104_{tag}.json', 'w'), indent=1)
    S = {}
    for gname in ('cut 100 ft', 'cut 200 ft', 'PDF 200 ft', '400 ft', 'all'):
        R = [r for r in rows.values() if gname == 'all' or r['group'] == gname]
        tot = lambda k, src=None: sum((r[src][k] if src else r[k]) or 0 for r in R)
        med = lambda k, src=None: round(float(np.median([(r[src][k] if src else r[k]) for r in R if (r[src][k] if src else r[k]) is not None])), 3)
        S[gname] = dict(plates=len(R),
                        r2=dict(blocks=tot('blocks'), holes=tot('holes'), open_outlines=tot('open_outlines'), open_blocks=tot('open_blocks'), open_exported=tot('open_exported'), open_exported_len=tot('open_exported_len'),
                                open_exported_green=tot('open_exported_green'), exported=tot('exported'), exported_len=tot('exported_len'), editor_lines=tot('editor_lines'), editor_len=tot('editor_len'),
                                green_share_median=med('green_share'), edge_lines=tot('edge_lines'), on_rail=tot('on_rail'), on_rail_len=tot('on_rail_len'), bridges=tot('bridges'),
                                not_on_line_dropped=tot('not_on_line_dropped'), paper_edge_sides=tot('paper_edge_sides'),
                                suspect=[r['plate'] for r in R if r['suspect']], seconds_median=med('seconds'), seconds_max=max(r['seconds'] for r in R), wall_median=med('wall_seconds')),
                        round1=dict(blocks=tot('blocks', 'round1'), holes=tot('holes', 'round1'), exported=tot('exported', 'round1'), exported_len=tot('exported_len', 'round1'), editor_lines=tot('editor_lines', 'round1'),
                                    editor_len=tot('editor_len', 'round1'), green_share_median=med('green_share', 'round1'), edge_lines=tot('edge_lines', 'round1'), on_rail=tot('on_rail', 'round1'),
                                    suspect=[r['plate'] for r in R if r['round1']['suspect']]),
                        batch=dict(blocks=tot('blocks', 'batch'), exported=tot('exported', 'batch'), exported_len=tot('exported_len', 'batch'), editor_lines=tot('editor_lines', 'batch'), green_share_median=med('green_share', 'batch'),
                                   edge_lines=tot('edge_lines', 'batch'), suspect=[r['plate'] for r in R if r['batch']['suspect']]),
                        nesting=dict(blocks=tot('blocks', 'nesting'), holes=tot('holes', 'nesting'), exported=tot('exported', 'nesting'), exported_len=tot('exported_len', 'nesting'), editor_lines=tot('editor_lines', 'nesting'),
                                     green_share_median=med('green_share', 'nesting'), edge_lines=tot('edge_lines', 'nesting'), suspect=[r['plate'] for r in R if r['nesting']['suspect']]))
        S[gname]['fewer_blocks_than_batch'] = [r['plate'] for r in R if r['blocks'] < r['batch']['blocks']]
        S[gname]['fewer_blocks_than_round1'] = [r['plate'] for r in R if r['blocks'] < r['round1']['blocks']]
    S['versions'] = sorted({r['version'] for r in rows.values()})
    json.dump(S, open(C.IMPL + f'batch104_{tag}_summary.json', 'w'), indent=1); print(json.dumps(S, indent=1))


if __name__ == '__main__':
    if sys.argv[1] == 'run':
        tag = sys.argv[2]; plain = arg('--plain', 'keep'); jobs = int(arg('--jobs', '6'))
        want = [a for a in sys.argv[3:] if not a.startswith('--') and a not in (plain, str(jobs))] or PL
        t = time.time()
        with cf.ThreadPoolExecutor(jobs) as ex:
            for n, m in ex.map(lambda n: run_one(n, tag, plain), want): print(n, m, flush=True)
        print('wall', round(time.time() - t), 's')
    else: measure(sys.argv[2])
