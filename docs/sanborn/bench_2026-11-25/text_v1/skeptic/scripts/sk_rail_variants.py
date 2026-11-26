"""Skeptic (26 Nov 2026): score every hand-off rail run of plate 44 and 5, including the _nojoin tracks, with the gate's
track scorer (gate/scripts/my_rail.py score(), loaded without running its main part). Shows which 'after' rules were
on. Reads only; writes skeptic/out/rail_variants.json.   cd data/sanborn; python -B .../sk_rail_variants.py"""
import glob, json, os, sys
sys.dont_write_bytecode = True
src = open('bench_2026-11-25/text_v1/gate/scripts/my_rail.py', encoding='utf8').read().split('\nout = {}')[0]
ns = {}; exec(compile(src, 'my_rail_head', 'exec'), ns); score = ns['score']
R = 'bench_2026-11-25/text_v1/handoff/runs/bins/'; out = {}
for f in sorted(glob.glob(R + '*_tracks*.json')):
    run = os.path.basename(f).replace('_tracks', '').replace('.json', ''); N = run.split('_')[0]
    bf = f'picks22_guided/22-{N}/rail_ben.json'
    if not os.path.exists(bf): continue
    d = json.load(open(f)); r = score(d['tracks'], json.load(open(bf, encoding='utf8'))['tracks'])
    rules = 'before' if '_before' in run else ('bridge+join' if run.endswith('_after') else ('bridge only' if run.endswith('_nojoin') else 'neither'))
    out[run] = dict(rules=rules, **r)
    print(f'{run:30s} {rules:12s} ' + ' | '.join(f"{k} R10 {v['recall10']} f/p/m {v['found']}/{v['partial']}/{v['missed']} false {v['false']} ({v['false_len']} px)" for k, v in r.items()))
json.dump(out, open('bench_2026-11-25/text_v1/skeptic/out/rail_variants.json', 'w'), indent=1)
