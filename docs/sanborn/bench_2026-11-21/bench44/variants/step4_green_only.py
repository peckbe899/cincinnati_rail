"""bench44 example of the --step4 hook: blocks_noguide.py step 4, but orange sides are dropped too (green only).
    python bench44.py --step4 variants/step4_green_only.py --tag batch+step4_green_only"""


def step4(polys):
    out = []
    for poly in polys:
        for s in poly:
            if s['state'] != 'on print' or s.get('paper_edge'): continue
            out.append(dict(src='read', name='', a=s['a'], b=s['b'], state='green'))
    return out
