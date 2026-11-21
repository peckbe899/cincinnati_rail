"""merge/impl: the repo's step 4 before the merge (blocks_noguide.py lines 49-52 at sha 3700ff13), for the bench44 port's faithfulness check."""
def step4(polys):
    out = []
    for poly in polys:
        for s in poly:
            if s['state'] == 'short' or s.get('paper_edge'): continue
            out.append(dict(src='read', name='', a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange'))
    return out
