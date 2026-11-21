"""merge/v-batch: count the merged outline step against the batch and against outline-nesting (B) on the 104 plates.

    python -B measure104.py      -> v-batch/measure104.json (per plate), v-batch/summary104.json (per group), printed table

Per plate and run (counts, not scores: there is no truth outside 44):
  blocks, holes     block polygons and street-hole polygons (hole=True) of outlines.json
  exported          the lines step 4 gives the editor (N_edges.json); exported_len their length (px)
  editor_lines      what the line editor shows of them: the repo's edit_server.clean() (read only); editor_len its length
  green_cnt/len     green share of the exported lines, by count and by length (batch and B: green = on ink; merged:
                    on ink AND on the detected line, the new gate, so the shares are not like for like)
  edge_lines        exported lines whose middle is within 150 px of the paper's edge (B's measure.py definition)
  suspect, why      batch: the census's QA flag (the batch itself had none); B and merged: their own N_outlines.json
  seconds           batch: the block step's time in run_plates.json (networks + outline step + step 4) and the whole
                    plate's; B: its outlines.py 'seconds'; merged: outlines.py 'seconds' and blocks_noguide.py wall
Sources: batch = unet_data/N_outlines.json, unet_data/N_edges.json, picks22_guided/22-N/outlines.json and
run_plates.json; B = outline-nesting/runs_plates/final/N/ (recounted here) and outline-nesting/measure.csv (checked
against); merged = v-batch/plates/N/ (run104.py). Also for merged: the sides step 4 leaves out, by reason, and the
editor lines it would show with them kept (keep_unlined=True, rail_drop=False), to split a loss of lines into reasons.
"""
import csv, json, os, re
import numpy as np
import cv2
import common as C
BN = C.step4_mod(); ES = C.edit_server()
ST = json.load(open(C.U + 'run_plates.json', encoding='utf8'))
CEN = {r['plate']: r for r in json.load(open(C.BENCH + 'census/census.json'))}
BCSV = {r['plate']: r for r in csv.DictReader(open(C.BENCH + 'outline-nesting/measure.csv', encoding='utf8'))}
BDIR = C.BENCH + 'outline-nesting/runs_plates/final/'


def L(e): return float(np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1]))


def step4_B(polys):   # B's and the batch's step 4: drops short and paper_edge only
    return [dict(src='read', name='', a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange') for p in polys for s in p if not (s['state'] == 'short' or s.get('paper_edge'))]


_paper = {}
def dist_paper(n):
    if n not in _paper:
        al = np.load(C.DATA + f'cufp/{n}/png_alpha_s4.npy').astype(np.uint8)
        _paper[n] = cv2.distanceTransform(cv2.copyMakeBorder(al, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0), cv2.DIST_L2, 5)[1:-1, 1:-1] * 4
    return _paper[n]


def ind(n, polys, edges):
    dist = dist_paper(n)
    def d_at(x, y): return float(dist[int(np.clip(y / 4, 0, dist.shape[0] - 1)), int(np.clip(x / 4, 0, dist.shape[1] - 1))])
    shown = ES.clean(edges) if edges else []; g = [e for e in edges if e['state'] == 'green']; tl = sum(L(e) for e in edges)
    return dict(blocks=sum(1 for p in polys if p and not p[0].get('hole')), holes=sum(1 for p in polys if p and p[0].get('hole')),
                exported=len(edges), exported_len=round(tl), editor_lines=len(shown), editor_len=round(sum(L(e) for e in shown)),
                editor_green=sum(e['state'] == 'green' for e in shown),
                green_cnt=round(len(g) / len(edges), 3) if edges else None, green_len=round(sum(L(e) for e in g) / tl, 3) if tl else None,
                edge_lines=sum(d_at((e['a'][0] + e['b'][0]) / 2, (e['a'][1] + e['b'][1]) / 2) < 150 for e in edges))


def codes(why): return ' '.join(w.split(' ')[0] for w in why) if isinstance(why, list) else (why or '').replace(';', ' ').strip()


def batch_secs(s):
    m = re.search(r'\|\s*(\d+)\s*s\s*$', s.get('blocks', '') or ''); return int(m.group(1)) if m else None


rows = {}
for n in C.plates104():
    r = dict(plate=n, group=C.group(n))
    # batch
    bp = json.load(open(C.G + f'22-{n}/outlines.json', encoding='utf8')); be = json.load(open(C.U + f'{n}_edges.json', encoding='utf8'))
    brep = json.load(open(C.U + f'{n}_outlines.json', encoding='utf8'))
    b = ind(n, bp, be); b.update(blocks_rep=brep.get('blocks'), suspect=bool(CEN[n]['qa_suspect']), why=CEN[n]['qa_why'], block_step_s=batch_secs(ST[n]), plate_s=ST[n].get('seconds'),
                                 step4_same=(step4_B(bp) == [dict(src='read', name='', a=e['a'], b=e['b'], state=e['state']) for e in be]),
                                 edges_mtime=os.path.getmtime(C.U + f'{n}_edges.json'), outlines_mtime=os.path.getmtime(C.G + f'22-{n}/outlines.json'))
    r['batch'] = b
    # B (outline-nesting final)
    Bp = json.load(open(BDIR + f'{n}/outlines.json', encoding='utf8')); Brep = json.load(open(BDIR + f'{n}/{n}_outlines.json', encoding='utf8'))
    x = ind(n, Bp, step4_B(Bp)); x.update(suspect=bool(Brep.get('suspect')), why=codes(Brep.get('suspect_why', [])), seconds=Brep.get('seconds'))
    c = BCSV[n]; x['csv_check'] = {k: (c[f'final_{k}'], x[k]) for k in ('blocks', 'holes', 'exported', 'editor_lines', 'edge_lines') if str(x[k]) != c[f'final_{k}']}
    r['B'] = x
    r['batch']['csv_check'] = {k: (c[f'batch_{k}'], b[k]) for k in ('blocks', 'exported', 'editor_lines', 'edge_lines') if str(b[k]) != c[f'batch_{k}']}
    # merged (v-batch run)
    d = C.ME + f'plates/{n}/'; run = json.load(open(d + 'run.json'))
    if run['exit'] != 0: r['merged'] = dict(failed=run['last']); rows[n] = r; continue
    mp = json.load(open(d + 'outlines.json', encoding='utf8')); me = json.load(open(d + f'{n}_edges.json', encoding='utf8'))
    mrep = json.load(open(d + f'{n}_outlines.json', encoding='utf8')); mng = json.load(open(d + f'{n}_blocks_ng.json', encoding='utf8'))
    m = ind(n, mp, me)
    assert me == BN.step4(mp), n
    sides = [s for p in mp for s in p]
    drop = {}
    for s in sides:
        k = 'paper_edge' if s.get('paper_edge') else (s['state'] if s['state'] in ('not on a line', 'on rail', 'short') else None)
        if k: drop.setdefault(k, [0, 0.0]); drop[k][0] += 1; drop[k][1] += L(s)
    allk = BN.step4(mp, keep_unlined=True, rail_drop=False); sh_all = ES.clean(allk)
    m.update(dropped={k: [v[0], round(v[1])] for k, v in drop.items()}, editor_lines_kept_all=len(sh_all), editor_len_kept_all=round(sum(L(e) for e in sh_all)),
             bridges=mrep.get('bridges'), on_rail=mrep.get('on_rail'), short_pieces=mrep.get('short_pieces'), holes_found=mrep.get('holes_found'), holes_in_open_land=mrep.get('holes_in_open_land'),
             suspect=bool(mrep.get('suspect')), why=codes(mrep.get('suspect_why', [])), why_full=mrep.get('suspect_why', []), qa=mrep.get('qa'), rail=mrep.get('rail'), map_ground=mrep.get('map_ground'),
             seconds=mrep.get('seconds'), wall_seconds=run['wall_seconds'], version=mrep.get('version'), blocks_ng_sides=mng.get('sides'))
    r['merged'] = m; rows[n] = r

json.dump(rows, open(C.mine(C.ME + 'measure104.json'), 'w'), indent=1)
GR = ('cut 100 ft', 'cut 200 ft', 'PDF 200 ft', '400 ft'); S = {}
for gname in GR + ('all 104',):
    R = [r for r in rows.values() if gname == 'all 104' or r['group'] == gname]; out = dict(plates=len(R), list=' '.join(r['plate'] for r in R))
    for src in ('batch', 'B', 'merged'):
        X = [r[src] for r in R if 'failed' not in r[src]]
        tot = lambda k: sum(x[k] or 0 for x in X)
        med = lambda k: round(float(np.median([x[k] for x in X if x.get(k) is not None])), 3) if any(x.get(k) is not None for x in X) else None
        o = dict(blocks=tot('blocks'), holes=tot('holes'), exported=tot('exported'), exported_len=tot('exported_len'), editor_lines=tot('editor_lines'), editor_len=tot('editor_len'),
                 green_cnt_pooled=round(sum(x['green_cnt'] * x['exported'] for x in X if x['exported']) / max(1, tot('exported')), 3), green_cnt_median=med('green_cnt'), green_len_median=med('green_len'),
                 edge_lines=tot('edge_lines'), le5_blocks=sum(x['blocks'] <= 5 for x in X),
                 suspect=[r['plate'] for r in R if r[src].get('suspect')], suspect_why={r['plate']: r[src].get('why') for r in R if r[src].get('suspect')})
        if src == 'batch': o.update(block_step_s_median=med('block_step_s'), block_step_s_total=tot('block_step_s'), plate_s_median=med('plate_s'))
        if src == 'B': o.update(seconds_median=med('seconds'), seconds_total=round(tot('seconds'), 1))
        if src == 'merged': o.update(seconds_median=med('seconds'), seconds_total=round(tot('seconds'), 1), seconds_max=max(x['seconds'] for x in X), wall_median=med('wall_seconds'), wall_total=round(tot('wall_seconds'), 1),
                                     on_rail=tot('on_rail'), bridges=tot('bridges'), failed=[r['plate'] for r in R if 'failed' in r['merged']])
        out[src] = o
    S[gname] = out
json.dump(S, open(C.mine(C.ME + 'summary104.json'), 'w'), indent=1)
for gname, o in S.items():
    print(f"== {gname} ({o['plates']} plates)")
    for src in ('batch', 'B', 'merged'):
        x = o[src]; print(f"  {src:6s} blocks {x['blocks']:5d} holes {x['holes']:4d} exported {x['exported']:6d} ({x['exported_len'] / 1e6:.2f}M px) editor {x['editor_lines']:6d} ({x['editor_len'] / 1e6:.2f}M px) "
                          f"green cnt pooled {x['green_cnt_pooled']} med {x['green_cnt_median']} len med {x['green_len_median']} edge {x['edge_lines']} <=5 blocks {x['le5_blocks']} suspect {len(x['suspect'])}: {x['suspect_why']}")
chk = {n: (r['batch']['csv_check'], r['B']['csv_check']) for n, r in rows.items() if r['batch']['csv_check'] or r['B']['csv_check']}
print('csv mismatches (csv value, recount):', chk)
print('batch N_edges.json not equal to step 4 of its outlines.json:', [n for n, r in rows.items() if not r['batch']['step4_same']])
