"""outline-quality --step4 hook: blocks_noguide.py step 4, but no side or bridge with state 'not on a line' is exported
(review pp-7: those are 90-96% wrong). Green = 'on print', everything else orange, as now."""


def step4(polys):
    return [dict(src='read', name='', a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange') for p in polys for s in p
            if s['state'] not in ('short', 'not on a line') and not s.get('paper_edge')]
