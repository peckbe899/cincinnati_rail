"""v-44: what the merged step's new side states are worth on plate 44, per side, with the harness's own line matching
(5 px, 20 degrees; LineSet / near from v-44/harness/bench44.py) against Ben's street map. Also PQ with the street holes
cut out of the block raster (the harness fills polygons in list order, so it paints each block over its holes and its
PQ cannot see them).

    python -B sides44.py  -> v-44/sides44.json

For each run (merged__GRID, railrule__GRID): every side of outlines.json by state (and hole / bridge / paper_edge):
count, length, share of length on Ben's lines; the 'on rail' sides by their 'was' state; and the sides step 4 keeps."""
import importlib.util, json, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'hooks'))
from common import V, GRIDS  # noqa: E402
R = V + 'harness/runs/'
spec = importlib.util.spec_from_file_location('b44', V + 'harness/bench44.py'); b44 = importlib.util.module_from_spec(spec); spec.loader.exec_module(b44)
T = b44.load_truth(); BEN = b44.LineSet(T['lines'], 20.0); TOL = 5.0


def on_ben(sides):
    """per side: share of its length within TOL of Ben's lines (direction within 20 degrees)"""
    if not sides: return np.zeros(0), np.zeros(0)
    ls = b44.LineSet([(s['a'], s['b'], 'x') for s in sides], 20.0); d = ls.dist_to(BEN)
    n = np.bincount(ls.ix, minlength=len(sides)); ok = np.bincount(ls.ix, (d <= TOL).astype(float), minlength=len(sides))
    L = np.array([np.hypot(s['b'][0] - s['a'][0], s['b'][1] - s['a'][1]) for s in sides])
    return ok / np.maximum(n, 1), L


def group(sides, key):
    sh, L = on_ben(sides); G = {}
    for s, f, l in zip(sides, sh, L):
        g = G.setdefault(key(s), [0, 0.0, 0.0]); g[0] += 1; g[1] += l; g[2] += f * l
    return {k: dict(n=v[0], len=round(v[1]), on_ben=round(v[2] / v[1], 4) if v[1] else None) for k, v in sorted(G.items())}


def pq_holes_cut(polys):
    """block raster with the street holes cut out (and a block inside a hole filled again, as ink_bins.block_ground)"""
    blk = [(k, p) for k, p in enumerate(polys) if not p[0].get('hole')]; hol = [p for p in polys if p[0].get('hole')]
    inst = np.zeros((b44.h2, b44.w2), np.int32); Hm = np.zeros((b44.h2, b44.w2), np.uint8)
    rr = lambda p: (np.array([s['a'] for s in p], float) * b44.S).round().astype(np.int32)
    for i, (k, p) in enumerate(blk): cv2.fillPoly(inst, [rr(p)], i + 1)
    for p in hol: cv2.fillPoly(Hm, [rr(p)], 1)
    inst[Hm > 0] = 0
    for i, (k, p) in enumerate(blk):
        c = np.clip(rr(p), 0, [b44.w2 - 1, b44.h2 - 1])
        if Hm[c[:, 1], c[:, 0]].mean() > 0.5: cv2.fillPoly(inst, [rr(p)], i + 1)
    r, _ = b44.pq(T, inst, len(blk)); return {f: r[f]['PQ'] for f in r}, {f: r[f]['matched'] for f in r}


if __name__ == '__main__':
    out = {}
    for tag in [f'merged__{g}' for g in GRIDS] + ['railrule__batch', 'merged__guided']:
        if not os.path.exists(R + tag + '/outlines.json'): continue
        polys = json.load(open(R + tag + '/outlines.json', encoding='utf8')); S = [s for p in polys for s in p]
        rail = [s for s in S if s['state'] == 'on rail']; nonedge = [s for s in S if not s.get('paper_edge') and s['state'] != 'short']
        keep = [s for s in nonedge if s['state'] not in ('not on a line', 'on rail')]
        hole_sides = [s for s in nonedge if s.get('hole')]
        pqc, mc = pq_holes_cut(polys)
        out[tag] = dict(by_state=group([s for s in S if not s.get('paper_edge')], lambda s: s['state']),
                        on_rail_by_was=group(rail, lambda s: s['was'] + (' (paper_edge)' if s.get('paper_edge') else '')),
                        on_rail_total=group(rail, lambda s: 'all'),
                        hole_sides_by_state=group(hole_sides, lambda s: s['state']),
                        bridges_by_state=group([s for s in nonedge if 'bridge' in s], lambda s: s['state']),
                        kept_by_step4=group(keep, lambda s: 'green' if s['state'] == 'on print' else 'orange'),
                        holes=sum(1 for p in polys if p[0].get('hole')), blocks=sum(1 for p in polys if not p[0].get('hole')),
                        PQ_holes_cut=pqc, matched_holes_cut=mc, PQ_harness=json.load(open(R + tag + '/bench44.json'))['headline']['all']['PQ'])
        print(tag, json.dumps(dict(on_rail=out[tag]['on_rail_total'], by_was=out[tag]['on_rail_by_was'], holes=out[tag]['hole_sides_by_state'], PQ_cut=pqc, PQ=out[tag]['PQ_harness'])), flush=True)
    json.dump(out, open(V + 'sides44.json', 'w'), indent=1)
