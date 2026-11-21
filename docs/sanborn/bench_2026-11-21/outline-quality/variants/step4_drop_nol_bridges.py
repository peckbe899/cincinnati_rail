"""outline-quality --step4 hook: blocks_noguide.py step 4, but a bridging side (outlines with rings) that is not on any
line (state 'not on a line') is not exported. Green = 'on print', everything else orange, as now."""


def step4(polys):
    return [dict(src='read', name='', a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange') for p in polys for s in p
            if s['state'] != 'short' and not s.get('paper_edge') and not (s.get('bridge') and s['state'] == 'not on a line')]
