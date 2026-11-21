"""verify-outline-quality: step 4 of the PATCHED blocks_noguide.py (patched/blocks_noguide.py, made by applying
outline-quality/diffs/blocks_noguide.py.diff to a copy of tools/sanborn/unet/blocks_noguide.py), for bench44 --step4.
The filter line is checked against the patched file so this cannot drift from the diff."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
LINE = "            if s['state'] in ('short', 'not on a line') or s.get('paper_edge'): continue\n"
assert open(os.path.join(HERE, 'patched', 'blocks_noguide.py'), encoding='utf8').read().count(LINE) == 1


def step4(polys):
    out = []
    for poly in polys:
        for s in poly:
            if s['state'] in ('short', 'not on a line') or s.get('paper_edge'): continue
            out.append(dict(src='read', name='', a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange'))
    return out
