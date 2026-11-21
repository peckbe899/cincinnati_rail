"""Census of the batch's cut (non-PDF) plates, to choose the plates for the visual audit (visual-cut, 21 Nov 2026).

    python census_cut.py            (system python; reads only)

Reads run_plates.json, N_edges.json, N_outlines.json, cufp/N/source.json, the review's tint census
(ml_review_2026-11-21/research-training/b_colour.json) and the critic's hole census. Writes census_cut.json here.
"""
import json, os, re
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
U = D + 'unet_data/'; OUT = os.path.dirname(os.path.abspath(__file__))
rp = json.load(open(U + 'run_plates.json', encoding='utf8'))
tint = {r['plate']: r['tinted_share'] for r in json.load(open(D + 'ml_review_2026-11-21/research-training/b_colour.json'))}
holes = json.load(open(D + 'ml_review_2026-11-21/critic/holes.json'))
rows = []
for n, r in rp.items():
    pdf = os.path.exists(D + f'cufp/{n}/source.json')
    guide = os.path.exists(U + f'{n}_guide.png')
    e = U + f'{n}_edges.json'
    ed = json.load(open(e, encoding='utf8')) if os.path.exists(e) and not guide else []
    import math
    L = lambda s: math.hypot(s['b'][0] - s['a'][0], s['b'][1] - s['a'][1])
    g = [s for s in ed if s['state'] == 'green']; o = [s for s in ed if s['state'] == 'orange']
    ol = U + f'{n}_outlines.json'
    oj = json.load(open(ol)) if os.path.exists(ol) and not guide else {}
    rows.append(dict(n=n, pdf=pdf, guide=guide, tint=tint.get(n), rail=r.get('railroad_px'), street=r.get('streetcar_px'),
                     blocks=oj.get('blocks'), green=len(g), orange=len(o), green_len=round(sum(map(L, g))), orange_len=round(sum(map(L, o))),
                     hole_share=holes.get(n, {}).get('hole_share'), summary=r.get('blocks', '')))
key = lambda r: (int(re.match(r'\d+', r['n']).group()), r['n'])
rows.sort(key=key)
json.dump(rows, open(os.path.join(OUT, 'census_cut.json'), 'w'), indent=1)
for r in rows:
    if r['pdf'] or r['guide']: continue
    print(f"{r['n']:4s} tint {r['tint'] if r['tint'] is not None else '  - '}  rail {r['rail']:>8}  street {r['street']:>7}  blocks {r['blocks']}  green {r['green']:4d} ({r['green_len']:>7})  orange {r['orange']:3d}  holes {r['hole_share']}")
print('cut plates:', sum(not r['pdf'] and not r['guide'] for r in rows), ' pdf:', sum(r['pdf'] for r in rows), ' guided:', sum(r['guide'] for r in rows))
