try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 44 (Ben, 17 October): the APEx straight off its bridge through Ludlow (no reverse curve), the CS line on its own Kentucky approach
# (CS Bridge KY Approach.kmz), the CVG Express 15.75 m beside the APEx off the bridge, bridge spans from Bridge Spans.kmz, the CUT plaza and
# west park on the street grid. Chain: ... patch_v43.py && patch_v44.py
import sys
SP = _ws.DATA
src = open(SP + 'deckpage/index.html').read()
def rep(old, new, n=1):
    global src
    c = src.count(old)
    if c != n: sys.exit('count %d != %d for: %s' % (c, n, old[:110]))
    src = src.replace(old, new)
rep("    else if (p.layer === 'bridge') { ctx.strokeStyle = C.apex;",
    "    else if (p.layer === 'bridge' && p.kind === 'other') { ctx.strokeStyle = C.muted; ctx.lineWidth = Math.max(3, 7 * v.s); ctx.setLineDash([]); ctx.globalAlpha = 0.8; ctx.beginPath(); pathLine(f.geometry.coordinates); ctx.stroke(); ctx.strokeStyle = C.paper; ctx.lineWidth = Math.max(1, 3 * v.s); }\n"
    "    else if (p.layer === 'bridge') { ctx.strokeStyle = C.apex;")
rep("it crosses the Ohio on its own double-track span beside the APEx bridge, about 6 m clear of it, and goes through Ludlow and the hills beside the APEx in its own bores (drawn 24.75 m east of the APEx centre), level with it,",
    "it crosses the Ohio on its own double-track span beside the APEx bridge, about 6 m clear of it (span ends from Ben&rsquo;s Bridge Spans.kmz), then within 250 m of the Kentucky bank comes in to 15.75 m from the APEx centre (Ben, 17 October: the APEx&rsquo;s outer track 6.75 m, the CVG Express&rsquo;s inner track 13.5 m, group spacing) and goes through Ludlow and the hills beside the APEx in its own bores, level with it,")
rep("the APEx runs 15.75 m east of them (centres), goes 2% down from the bank into a tunnel about 340 m from it and stays in tunnel through the hills on the KMZ line toward Erlanger",
    "the CS pair follows the CS line&rsquo;s own Kentucky approach (Ben&rsquo;s CS Bridge KY Approach.kmz), bending west off its bridge, and the APEx runs straight off its bridge on the KMZ bearing (204&deg;) with no curve until the hills (Ben, 17 October). Drawn exactly on the KMZ line the APEx would pass 8.4 m from the CS line at N 4,330,200, where both are at about 161-165 m, so the APEx line (bridge and straight together) is drawn 7.5 m east of the KMZ line, the least that keeps 15.75 m to the CS pair. It goes 2% down from the end of its span into a tunnel about 360 m from it and stays in tunnel through the hills toward Erlanger")
open(SP + 'deckpage/index.html', 'w').write(src)
print('ok v44', len(src))
