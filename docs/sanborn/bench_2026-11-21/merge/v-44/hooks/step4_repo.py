"""v-44 hook for bench44.py --step4: the REPO's step 4 (tools/sanborn/unet/blocks_noguide.py, drop short and paper_edge;
green = 'on print'). The filter line is checked against the repo file so this cannot drift from it."""
F = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/blocks_noguide.py'
LINE = "            if s['state'] == 'short' or s.get('paper_edge'): continue\n"
assert open(F, encoding='utf8').read().count(LINE) == 1


def step4(polys):
    out = []
    for poly in polys:
        for s in poly:
            if s['state'] == 'short' or s.get('paper_edge'): continue
            out.append(dict(src='read', name='', a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange'))
    return out
