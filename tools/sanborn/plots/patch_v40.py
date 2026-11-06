try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 40 (Ben, 16 October): CVG airport from CVG Layout.kmz (runways 150 ft wide on their centre lines, terminals and hubs as
# buildings, general areas); CVG Express on its CVG Express New.kmz route (with the APEx through the hills, then its own line to CVG;
# the terminal end not set); the region box widened west to take in all of CVG.
# Chain: ... patch_v39.py && patch_v40.py
import sys
SP = _ws.DATA
src = open(SP + 'deckpage/index.html').read()
def rep(old, new, n=1):
    global src
    c = src.count(old)
    if c != n: sys.exit('count %d != %d for: %s' % (c, n, old[:110]))
    src = src.replace(old, new)

# ---- data and layer
rep("  try { S.tracks = await fetch('tracks.json').then(r => r.json()); } catch (e) { S.tracks = null; }",
    "  try { S.tracks = await fetch('tracks.json').then(r => r.json()); } catch (e) { S.tracks = null; }\n"
    "  try { S.airport = await fetch('airport.json').then(r => r.json()); for (const f of S.airport.features) f._bb = featBB(f); } catch (e) { S.airport = null; }")
rep('        <label><input type="checkbox" id="lLab" checked> Labels</label>',
    '        <label><input type="checkbox" id="lApt" checked> CVG airport</label>\n        <label><input type="checkbox" id="lLab" checked> Labels</label>')
rep("cutA: true, cutL: true },", "cutA: true, cutL: true, apt: true },")
rep("['lCA', 'cutA'], ['lCL', 'cutL']]) $(id).addEventListener", "['lCA', 'cutA'], ['lCL', 'cutL'], ['lApt', 'apt']]) $(id).addEventListener")
# ---- zoom
rep('    <button class="btn" id="zReg" title="Erlanger, CVG Terminal 1, Eastgate and Aviation">Region</button>',
    '    <button class="btn" id="zReg" title="Erlanger, CVG, Eastgate and Aviation">Region</button>\n    <button class="btn" id="zCvg" title="CVG airport">CVG</button>')
rep("$('zReg').onclick = () => fit(701000, 4320300, 737500, 4347500);",
    "$('zReg').onclick = () => fit(698500, 4320300, 737500, 4347500);\n$('zCvg').onclick = () => fit(699200, 4321900, 706000, 4327700);")
# ---- drawing
rep("  if (S.layers.trk && S.tracks) drawTracks(v);",
    "  if (S.layers.apt && S.airport) drawAirport(v);\n  if (S.layers.trk && S.tracks) drawTracks(v);")
rep("function featBB(f) {",
    "function drawAirport(v) {   // CVG Layout.kmz: areas, runways (150 ft on their centre lines), buildings\n"
    "  const r0 = cv.getBoundingClientRect(), [qx0, qy1] = S2W(0, 0), [qx1, qy0] = S2W(r0.width, r0.height), vb = [qx0 - 50, qy0 - 50, qx1 + 50, qy1 + 50];\n"
    "  const AF = S.airport.features.filter(f => bbHit(f._bb, vb)); ctx.save();\n"
    "  for (const f of AF) if (f.properties.layer === 'cvg_area') { ctx.setLineDash([6, 4]); fillPoly(f.geometry, C.precinct, C.muted, 1.2, 0.35); ctx.setLineDash([]); }\n"
    "  for (const f of AF) if (f.properties.layer === 'cvg_runway') fillPoly(f.geometry, C['apex-plat'], C.ink, 0.8, 0.95);\n"
    "  if (v.s > 0.06) { ctx.strokeStyle = C.paper; ctx.lineWidth = Math.max(1, 0.9 * v.s); ctx.setLineDash([Math.max(4, 36 * v.s), Math.max(4, 24 * v.s)]);\n"
    "    for (const f of AF) if (f.properties.layer === 'cvg_runway_cl') { ctx.beginPath(); pathLine(f.geometry.coordinates); ctx.stroke(); } ctx.setLineDash([]); }\n"
    "  for (const f of AF) if (f.properties.layer === 'cvg_building') fillPoly(f.geometry, C.civic, C.ink, 1, 0.9);\n"
    "  if (S.layers.lab && v.s > 0.045) { ctx.textBaseline = 'middle';\n"
    "    for (const f of AF) { const p = f.properties; if (p.layer === 'cvg_runway_cl') continue; const big = p.layer === 'cvg_building';\n"
    "      if (p.layer === 'cvg_area' && v.s < 0.1) continue;\n"
    "      let cx, cy; if (p.layer === 'cvg_runway') { const c = S.airport.features.find(g => g.properties.layer === 'cvg_runway_cl' && g.properties.name === p.name).geometry.coordinates; cx = (c[0][0] + c[1][0]) / 2; cy = (c[0][1] + c[1][1]) / 2; } else [cx, cy] = ringCentroid(f.geometry.coordinates[0]);\n"
    "      const [x, y] = W2S(cx, cy), t = p.layer === 'cvg_runway' ? p.name.replace('Runway ', '') : p.name; ctx.font = (big ? '700 12px ' : '600 11px ') + css('--font-ui');\n"
    "      const tw = ctx.measureText(t).width; ctx.globalAlpha = 0.88; ctx.fillStyle = C.panel; ctx.fillRect(x - tw / 2 - 3, y - 8, tw + 6, 16); ctx.globalAlpha = 1; ctx.fillStyle = p.layer === 'cvg_area' ? C.muted : C.ink; ctx.fillText(t, x - tw / 2, y); } }\n"
    "  ctx.restore(); }\n"
    "function featBB(f) {")
# ---- picking and panel
rep("  if (!area) for (const f of feats('rail_open')) if (polysOf(f.geometry).some(q => inPoly(p, q))) { area = f; break; }",
    "  if (!area) for (const f of feats('rail_open')) if (polysOf(f.geometry).some(q => inPoly(p, q))) { area = f; break; }\n"
    "  if (!area && S.layers.apt && S.airport) for (const L of ['cvg_building', 'cvg_runway', 'cvg_area']) { for (const f of S.airport.features) if (f.properties.layer === L && bbHit(f._bb, [p[0], p[1], p[0], p[1]]) && inPoly(p, f.geometry.coordinates)) { area = f; break; } if (area) break; }")
rep("    if (L === 'cut_road') sub.textContent =",
    "    if (L === 'cvg_runway') { kv('Length', fmt(p.length_m) + ' m (' + fmt(p.length_ft) + ' ft)'); kv('Width', '150 ft (45.7 m)'); kv('Heading', fmt(p.bearing, 1) + '\\u00b0'); sub.textContent = 'CVG runway, from its centre line in CVG Layout.kmz, drawn 150 ft wide'; }\n"
    "    if (L === 'cvg_building') sub.textContent = 'CVG building (CVG Layout.kmz)';\n"
    "    if (L === 'cvg_area') sub.textContent = 'CVG general area (CVG Layout.kmz)';\n"
    "    if (L === 'cut_road') sub.textContent =")
# ---- CUT approaches panel and notes
old = src[src.index("  if (T.cvg) kv('CVG Express (M, 15-16)'"):]; old = old[:old.index('\n') + 1]
rep(old, "  if (T.cvg) { const V = T.cvg; kv('CVG Express (M, 15-16)', 'east of the APEx approach; at grade only across the Cardinal pair; own span beside the APEx bridge (' + fmt(V.span_gap, 1) + ' m between); beside the APEx through the hills, ' + fmt(V.g, 2) + '% up from ' + fmt(V.climb_from) + ' m past the bank, ' + fmt(V.over_apex.clear, 0) + ' m over the APEx before Erlanger, under the CS line, then to CVG (' + fmt(V.length_km, 1) + ' km from the bank); the terminals not set'); }\n")
rep("The CVG Express (16 October, Ben: its own span) leaves M and stays on the east side of the APEx approach, crossing only the Cardinal pair at grade south of W 8th (the Cardinal runs about 1.4 trains an hour each way); it crosses the Ohio on its own double-track span beside the APEx bridge, about 6 m clear of it, and in Ludlow swings west over the APEx where the APEx is already below ground (about 10 m clear), joining the CS line about 650 m from the bank by a flat junction (southbound CVG trains cross the northbound CS track). The intercity pair (A-D) has the CS bridge to itself.",
    "The CVG Express (16 October, Ben: its own span, and CVG Express New.kmz) leaves M and stays on the east side of the APEx approach, crossing only the Cardinal pair at grade south of W 8th (the Cardinal runs about 1.4 trains an hour each way); it crosses the Ohio on its own double-track span beside the APEx bridge, about 6 m clear of it, and goes through Ludlow and the hills beside the APEx in its own bores (drawn 24.75 m east of the APEx centre), level with it, then climbs 1.7% from about 3.5 km past the bank, crosses over the APEx (15 m, a working value for bore over bore) just north of Erlanger, where it turns west, passes about 25 m under the CS line and runs on to CVG, the last 3.8 km on the TRIMET CVG line&rsquo;s levels. Where it goes from the end of the KMZ line to the terminals is not set: it is an airside train (the RER serves the terminals landside). The intercity pair (A-D) has the CS bridge to itself.")
rep("In Ludlow (Ben: 4 APEx tracks, at least 2 intercity, 6 to 8 in all) the two CS tracks carry the intercity trains across the 1922 bridge and on at grade along the TRIMET CS line, with the CVG Express from the Ludlow junction;",
    "In Ludlow (Ben: 4 APEx tracks, at least 2 intercity, 6 to 8 in all) the two CS tracks carry the intercity trains across the 1922 bridge and on at grade along the TRIMET CS line, with the APEx and the CVG Express east of them;")
rep(" Six tracks are drawn: the CVG Express (6 an hour at the peak) and the intercity placeholder (4) make 10 an hour each way on the CS pair, about half of a double track at 3 minutes, so a spare pair is not needed yet; the band leaves room for one on the west side. The CVG Express leaves the CS line for CVG at Erlanger, as on the TRIMET line.",
    " The CS pair carries only the intercity trains (4 an hour each way, a placeholder), so a spare pair is not needed yet; the band leaves room for one on the west side.")
rep("RER and APEx are drawn out to Erlanger, CVG Terminal 1, Eastgate and Aviation (E 701,600-736,900,",
    "RER and APEx are drawn out to Erlanger, CVG, Eastgate and Aviation (E 699,000-736,900 since 16 October, to take in all of CVG;")
rep("<p>Locks (16 October):",
    "<p>CVG airport (16 October): from Ben&rsquo;s CVG Layout.kmz. The five runways are drawn 150 ft wide on their centre lines (18L/36R and 9L/27R 12,000 ft, 18C/36C 11,000 ft, 9R/27L 10,000 ft, 18R/36L 9,000 ft); Terminals 1A, 1B, 2, 3 and 4 and the Amazon and DHL hubs are buildings; cargo plane parking, the hangar and cargo areas and parking are general areas. The RER stops at CVG Terminal 1 and CVG Terminal 2/3/4, landside.</p>\n      <p>Locks (16 October):")

# ---- CVG Express in its own colour
rep("  --bst: #fbf7ee;", "  --bst: #fbf7ee;\n  --cvg: #1f78b4;")
rep("--we: #8fb4d4; --bst: #2b3c40;", "--we: #8fb4d4; --bst: #2b3c40; --cvg: #5fb0ee;", 2)
rep("function readColors() { for (const k of ['paper',", "function readColors() { for (const k of ['cvg','paper',")
rep("    if (p.layer === 'apex') { ctx.strokeStyle = C.apex;", "    if (p.layer === 'apex') { ctx.strokeStyle = (p.kind === 'cvg' || /^CVG Express/.test(p.name || '')) ? C.cvg : C.apex;")
open(SP + 'deckpage/index.html', 'w').write(src)
print('ok v40', len(src))
