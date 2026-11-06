try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 38 (Ben, 15 October): CVG Express across the south throat at grade (no flyover); the APEx in tunnel through the Kentucky
# hills under the ORR/intercity (CS) line, RER E over it, three levels where they meet; lower platforms centred under the APEx
# platforms; the west headhouse moved east; track 16 and platform M full length.
# Chain: patch_page.py && patch_v34.py && patch_v36.py && patch_v37.py && patch_v38.py
import sys
SP = _ws.DATA
src = open(SP + 'deckpage/index.html').read()
def rep(old, new, n=1):
    global src
    c = src.count(old)
    if c != n: sys.exit('count %d != %d for: %s' % (c, n, old[:110]))
    src = src.replace(old, new)

# tunnels dashed
rep("    if (p.layer === 'apex') { ctx.strokeStyle = C.apex; ctx.lineWidth = p.kind === 'region' && v.s < 0.2 ? 1.3 : lw; ctx.setLineDash([]); ctx.globalAlpha = 0.95; }",
    "    if (p.layer === 'apex') { ctx.strokeStyle = C.apex; ctx.lineWidth = p.kind === 'region' && v.s < 0.2 ? 1.3 : lw; ctx.setLineDash(p.state === 'tunnel' ? [7, 4] : []); ctx.globalAlpha = 0.95; }")
# panel
src_cvg_old = src[src.index("  if (T.cvg) kv('CVG Express (M, 15-16)'"):]
src_cvg_old = src_cvg_old[:src_cvg_old.index('\n') + 1]
rep(src_cvg_old, "  if (T.cvg) kv('CVG Express (M, 15-16)', 'across the south throat at grade (' + fmt(T.cvg.crossings) + ' crossings, N ' + fmt(T.cvg.cross_N[0]) + '-' + fmt(T.cvg.cross_N[1]) + '), then ' + fmt(T.cvg.g, 2) + '% up on the TRIMET CS viaduct to the bridge; tightest curve ' + fmt(T.cvg.r_min) + ' m');\n")
src_lud_old = src[src.index("  if (T.lud) kv('Ludlow (Kentucky)'"):]
src_lud_old = src_lud_old[:src_lud_old.index('\n') + 1]
rep(src_lud_old, "  if (T.lud) { kv('Ludlow (Kentucky)', 'CS line 2 at grade (ORR/intercity, CVG Express) + APEx 4, ' + fmt(T.lud.gap, 2) + ' m centre to centre; APEx ' + fmt(T.lud.g_down, 1) + '% down from the bank, tunnel from ' + fmt(T.lud.portal) + ' m, ' + fmt(T.lud.z_apex, 1) + ' m under the CS line (' + fmt(T.lud.under, 1) + ' m below), ' + fmt(T.lud.z_low, 0) + ' m under the valley, then ' + fmt(T.lud.g_up, 1) + '% up');\n"
    "    if (T.lud.stack) kv('Three levels (RER E over the APEx)', T.lud.stack.map(q => 'N ' + fmt(q.at[1]) + ': ' + fmt(q.z_cs, 1) + ' / ' + fmt(q.z_rer_e, 0) + ' / ' + fmt(q.z_apex, 1) + ' m').join('; ') + ' (ORR/intercity / RER E / APEx)'); }\n")
# notes
rep("The CVG Express leaves M on the east side and flies over the six APEx tracks just south of W 8th (6.8 m clear), then comes down onto the TRIMET CS viaduct and joins the intercity pair (A-D) at the CS bridge abutment.",
    "The CVG Express leaves M on the east side and crosses the six APEx approach tracks at grade just south of the throat, inside the throat interlocking (Ben: no flyover for a single line), then runs onto the TRIMET CS viaduct and joins the intercity pair (A-D) at the CS bridge abutment; at 6 trains an hour each way its 12 moves an hour fit between the APEx knots (:25-:50), when the Kentucky approach is quiet.")
rep("the APEx runs 15.75 m east of them (centres), climbs 2% on a viaduct and crosses over the CS line about 1 km from the bank, then takes the KMZ line toward Erlanger.",
    "the APEx runs 15.75 m east of them (centres), goes 2% down from the bank into a tunnel about 340 m from it and stays in tunnel through the hills on the KMZ line toward Erlanger, so it is grade-separated from the CS line throughout (Ben): 146 m where it passes under the CS line, about 1 km from the bank (22.6 m below), and under the valley at about N 4,329,000, then 1% up. RER E leaves the APEx tunnel corridor and passes over the APEx; the KMZ lines put the three on top of one another three times, each within 20 m of the CS line: ORR/intercity at grade on top, RER E between, the APEx below (RER E drawn midway, a working value).")
rep("The platforms keep the ruled length (the plan is cut off at its north end).",
    "The platforms keep the ruled length (the plan is cut off at its north end); track 16 and platform M run the full length (Ben). The eight lower platforms (A-H) are centred under the APEx platforms, from platform 7&rsquo;s west edge to platform M&rsquo;s east edge. The west headhouse has moved 30 m east to the freight passing track, and the west park runs on to it.")
open(SP + 'deckpage/index.html', 'w').write(src)
print('ok v38', len(src))
