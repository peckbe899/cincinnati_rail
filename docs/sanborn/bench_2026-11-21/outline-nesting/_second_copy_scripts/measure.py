"""Before/after indicators per plate for the outline-nesting change (no ground truth: these are counts, not scores).

    python measure.py [VARIANT ...]     (default: legacy new)  -> measure.json, measure.csv, printed table

'batch' = what the batch wrote (picks22_guided/22-N/outlines.json, unet_data/N_edges.json, unet_data/N_outlines.json);
for the five placed plates (43 44 45 80 82A), whose outline step the batch refused, 'batch' is the legacy run here.
Each VARIANT is runs_plates/VARIANT/N/ (run_variants.py). Per plate and run:
  blocks          block polygons (hole polygons not counted); holes = hole polygons
  sides_all       every side of every polygon, short pieces included
  exported        sides step 4 of blocks_noguide.py keeps (not short, not paper_edge) = lines in N_edges.json
  green_share     green share of those, by count (green_share_len: by length)
  editor_lines    what the line editor shows of them: edit_server.clean() (copied in bench44) joins collinear pieces
  largest_paper   area of the largest block polygon / paper area (png_alpha_s4)
  largest_map     the same / map ground (PDF sheets: map_area.py's mask; cut plates: paper)
  edge_lines      editor lines (N_edges) whose middle is within 150 px of the paper's edge (census definition)
  editor_per_line exported length / line network's thinned line length (census Q1; the batch value is census.json's)
  suspect, why    the QA flag (batch: census.json qa_suspect / qa_why, computed there from the batch)
Also: same_as_batch = the run's outlines.json is byte-identical to the batch's (only meaningful for 'legacy').
"""
import csv, json, os, re, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
sys.path.insert(0, HERE)
import bench44_copy as B  # noqa: E402  (clean(), as edit_server.py)
D = B.SP; U = B.U
GUIDED = {'43', '44', '45', '80', '82A'}
CEN = {r['plate']: r for r in json.load(open(HERE + '../census/census.json'))}
VIS = {k: v for k, v in json.load(open(HERE + '../census/visual.json')).items() if not k.startswith('_')}
MASKS = D + 'bench_2026-11-21/visual-pdf/maparea_check/'


def order(n): m = re.match(r'(\d+)(.*)', n); return int(m.group(1)), m.group(2)
def L(e): return float(np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1]))
def area(ring): r = np.asarray(ring, float); return abs((r[:, 0] * np.roll(r[:, 1], -1) - np.roll(r[:, 0], -1) * r[:, 1]).sum()) / 2 if len(r) >= 3 else 0.0


def step4(polys):
    return [dict(src='read', name='', a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange') for p in polys for s in p if not (s['state'] == 'short' or s.get('paper_edge'))]


_paper = {}
def paper_info(n):
    if n not in _paper:
        al = np.load(D + f'cufp/{n}/png_alpha_s4.npy').astype(np.uint8)
        dist = cv2.distanceTransform(cv2.copyMakeBorder(al, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0), cv2.DIST_L2, 5)[1:-1, 1:-1] * 4
        mp = MASKS + f'{n}_mask8.png'; mapx = float((cv2.imread(mp, 0) > 127).sum()) * 64 if os.path.exists(mp) else None
        _paper[n] = (float(al.sum()) * 16, dist, mapx)
    return _paper[n]


def indicators(n, polys, edges, rep=None):
    paper_px, dist, map_px = paper_info(n)
    blocks = [p for p in polys if not (p and p[0].get('hole'))]; holes = [p for p in polys if p and p[0].get('hole')]
    big = max((area([s['a'] for s in p]) for p in blocks), default=0.0)
    shown = B.clean(edges) if edges else []
    def d_at(x, y): return float(dist[int(np.clip(y / 4, 0, dist.shape[0] - 1)), int(np.clip(x / 4, 0, dist.shape[1] - 1))])
    g = [e for e in edges if e['state'] == 'green']; tl = sum(L(e) for e in edges)
    r = dict(blocks=len(blocks), holes=len(holes), sides_all=sum(len(p) for p in polys), exported=len(edges),
             green_share=round(len(g) / len(edges), 3) if edges else None, green_share_len=round(sum(L(e) for e in g) / tl, 3) if tl else None,
             exported_len=round(tl), editor_lines=len(shown), largest_paper=round(big / paper_px, 3), largest_map=round(big / (map_px or paper_px), 3),
             edge_lines=sum(d_at((e['a'][0] + e['b'][0]) / 2, (e['a'][1] + e['b'][1]) / 2) < 150 for e in edges),
             hole_sides_exported=sum(1 for p in holes for s in p if not (s['state'] == 'short' or s.get('paper_edge'))))
    if rep is not None:
        q = rep.get('qa', {}); r.update(editor_per_line=q.get('editor_per_line'), nested_regions=q.get('nested_regions'), suspect=rep.get('suspect'), why='; '.join(w.split(' ')[0] for w in rep.get('suspect_why', [])))
    return r


def main():
    variants = sys.argv[1:] or ['legacy', 'new']
    plates = sorted(CEN, key=order); out = {}
    for n in plates:
        c = CEN[n]; row = dict(plate=n, source=c['source'], ft_per_inch=c['ft_per_inch'], census_suspect=c['qa_suspect'], census_why=c['qa_why'], eye=VIS.get(n, '')[:4].strip(': '))
        if n in GUIDED: bdir = HERE + f'runs_plates/legacy/{n}/'; bp = bdir + 'outlines.json'
        else: bp = D + f'picks22_guided/22-{n}/outlines.json'
        if os.path.exists(bp):
            polys = json.load(open(bp, encoding='utf8'))
            edges = step4(polys) if n in GUIDED else json.load(open(U + f'{n}_edges.json', encoding='utf8'))
            row['batch'] = indicators(n, polys, edges); row['batch'].update(editor_per_line=c['editor_per_line'], nested_regions=c['nested_dropped'], suspect=c['qa_suspect'], why=c['qa_why'].replace(' ', ''))
        for v in variants:
            vd = HERE + f'runs_plates/{v}/{n}/'
            if not os.path.exists(vd + 'outlines.json'): continue
            polys = json.load(open(vd + 'outlines.json', encoding='utf8')); rep = json.load(open(vd + f'{n}_outlines.json'))
            row[v] = indicators(n, polys, step4(polys), rep)
            if n not in GUIDED and os.path.exists(bp): row[v]['same_as_batch'] = open(vd + 'outlines.json', 'rb').read() == open(bp, 'rb').read()
        out[n] = row
    json.dump(out, open(HERE + 'measure.json', 'w'), indent=1)
    keys = ['blocks', 'holes', 'sides_all', 'exported', 'green_share', 'editor_lines', 'largest_paper', 'largest_map', 'edge_lines', 'editor_per_line', 'nested_regions', 'suspect', 'why']
    with open(HERE + 'measure.csv', 'w', newline='', encoding='utf8') as f:
        w = csv.writer(f); w.writerow(['plate', 'source', 'ft_per_inch', 'eye'] + [f'{r}_{k}' for r in ['batch'] + variants for k in keys] + [f'{v}_same_as_batch' for v in variants])
        for n, row in out.items():
            w.writerow([n, row['source'], row['ft_per_inch'], row['eye']] + [row.get(r, {}).get(k) for r in ['batch'] + variants for k in keys] + [row.get(v, {}).get('same_as_batch') for v in variants])
    for n, row in out.items():
        if not any(v in row for v in variants): continue
        b = row.get('batch', {}); print(f"{n:4s} {row['source'][:3]} {row['ft_per_inch']:3d} {row['eye']:4s} | " + ' | '.join(
            f"{r[:6]:6s} {x.get('blocks', '-'):>3} b {x.get('holes', 0):>3} h {x.get('exported', '-'):>5} ex {x.get('editor_lines', '-'):>5} ed g{x.get('green_share')} L{x.get('largest_map')} e{x.get('edge_lines')} k{x.get('editor_per_line')} {'S:' + str(x.get('why')) if x.get('suspect') else 'ok'}"
            for r, x in [('batch', b)] + [(v, row[v]) for v in variants if v in row]))


if __name__ == '__main__':
    main()
