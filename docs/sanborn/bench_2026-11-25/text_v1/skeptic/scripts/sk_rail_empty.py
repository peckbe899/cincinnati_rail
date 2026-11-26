"""Skeptic (26 Nov 2026): score the empty-mask runs (skeptic/runs/empty) beside the hand-off's before / afterstrict / after,
with the gate's track scorer (gate/scripts/my_rail.py score()). Also the bin sizes. Reads only; writes skeptic/out/rail_empty.json.
    cd data/sanborn; python -B .../sk_rail_empty.py"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
src = open('bench_2026-11-25/text_v1/gate/scripts/my_rail.py', encoding='utf8').read().split('\nout = {}')[0]
ns = {}; exec(compile(src, 'my_rail_head', 'exec'), ns); score = ns['score']
H = 'bench_2026-11-25/text_v1/handoff/runs/bins/'; E = 'bench_2026-11-25/text_v1/skeptic/runs/empty/'; out = {}
for run in ('44_map', '5_now', '5_none'):
    N = run.split('_')[0]; ben = json.load(open(f'picks22_guided/22-{N}/rail_ben.json', encoding='utf8'))['tracks']
    for tag, tf, bf in (('before', H + f'{run}_before_tracks.json', H + f'{run}_before.png'), ('rules off, empty mask', E + f'{run}_empty_tracks.json', E + f'{run}_empty.png'),
                        ('mask, no bridge/join', H + f'{run}_afterstrict_tracks.json', H + f'{run}_afterstrict.png'), ('mask + bridge + join', H + f'{run}_after_tracks.json', H + f'{run}_after.png')):
        if not os.path.exists(tf): print(run, tag, 'missing'); continue
        r = score(json.load(open(tf))['tracks'], ben); b = cv2.imread(bf, 0)
        r['bins_px'] = {k: int((b == v).sum()) for k, v in (('railroad', 4), ('streetcar', 5), ('text', 8))}
        out[f'{run} | {tag}'] = r
        print(f'{run:7s} {tag:24s} ' + ' | '.join(f"{k} R10 {v['recall10']} P10 {v['precision10']} f/p/m {v['found']}/{v['partial']}/{v['missed']} false {v['false']} ({v['false_len']} px)" for k, v in r.items() if k != 'bins_px') + f" | bins {r['bins_px']}")
json.dump(out, open('bench_2026-11-25/text_v1/skeptic/out/rail_empty.json', 'w'), indent=1)
