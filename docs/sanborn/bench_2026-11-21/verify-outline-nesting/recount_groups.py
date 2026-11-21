"""verify-outline-nesting: independent recount of the agent's per-group totals (21 Nov 2026).

    python recount_groups.py   -> recount_groups.json + printed table

Own code (not measure.py / summarize.py). Groups from outline-nesting/summary.json. 'batch' = the batch's own files
(picks22_guided/22-N/outlines.json polygons, unet_data/N_edges.json lines); the five placed plates are left out of
'batch' here (the batch wrote no outlines for them). 'final' = outline-nesting/runs_plates/final/N (byte-identical to my
rerun of the diff on 8 of them, check_plates_rerun.json). Counted: blocks (polygons without hole sides), exported sides
(not short, not paper_edge), plates with <= 5 blocks, suspect plates (final N_outlines.json).
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
AG = D + 'bench_2026-11-21/outline-nesting/'
G = json.load(open(AG + 'summary.json'))['groups']
GUIDED = {'43', '44', '45', '80', '82A'}
out = {}
for g, plates in G.items():
    t = dict(n=len(plates), batch_blocks=0, batch_exported=0, batch_le5=0, final_blocks=0, final_exported=0, final_le5=0, final_holes=0, final_suspect=[], plates_missing=[])
    for n in plates:
        fp = AG + f'runs_plates/final/{n}/'
        if not os.path.exists(fp + 'outlines.json'): t['plates_missing'].append(n); continue
        P = json.load(open(fp + 'outlines.json', encoding='utf8')); R = json.load(open(fp + f'{n}_outlines.json'))
        fb = sum(1 for p in P if not (p and p[0].get('hole'))); t['final_blocks'] += fb; t['final_le5'] += fb <= 5
        t['final_holes'] += sum(1 for p in P if p and p[0].get('hole'))
        t['final_exported'] += sum(1 for p in P for s in p if not (s['state'] == 'short' or s.get('paper_edge')))
        if R.get('suspect'): t['final_suspect'].append(n)
        if n not in GUIDED:
            B = json.load(open(D + f'picks22_guided/22-{n}/outlines.json', encoding='utf8')); E = json.load(open(D + f'unet_data/{n}_edges.json', encoding='utf8'))
            t['batch_blocks'] += len(B); t['batch_le5'] += len(B) <= 5; t['batch_exported'] += len(E)
    out[g] = t
json.dump(out, open(HERE + 'recount_groups.json', 'w'), indent=1)
for g, t in out.items(): print(g, {k: (len(v) if isinstance(v, list) and k == 'final_suspect' else v) for k, v in t.items()}, 'suspect:', t['final_suspect'])
print('all suspect (final):', sum(len(t['final_suspect']) for t in out.values()))
