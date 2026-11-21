"""v-44 hook for bench44.py --step4: step 4 of outline-quality's proposal (A alone), outline-quality/proposed/
blocks_noguide.py: drop short, 'not on a line' and paper_edge sides; green = 'on print'. The filter line is checked
against that file so this cannot drift from it."""
import os
F = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/outline-quality/proposed/blocks_noguide.py'
LINE = "            if s['state'] in ('short', 'not on a line') or s.get('paper_edge'): continue\n"
assert open(F, encoding='utf8').read().count(LINE) == 1


def step4(polys):
    out = []
    for poly in polys:
        for s in poly:
            if s['state'] in ('short', 'not on a line') or s.get('paper_edge'): continue
            out.append(dict(src='read', name='', a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange'))
    return out
