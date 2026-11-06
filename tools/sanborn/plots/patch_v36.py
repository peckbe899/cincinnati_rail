try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 36: plots marked unfinished; Union Terminal, concourse, plaza and former Lincoln Park from the 1931 plot plan;
# the south approach on the General CUT Path KMZ; RER and APEx out to the region bounds (Erlanger, CVG Terminal 1, Eastgate, Aviation).
# Chain: python3 plots/patch_page.py && python3 plots/patch_v34.py && python3 plots/patch_v36.py
import sys
SP = _ws.DATA
src = open(SP + 'deckpage/index.html').read()
def rep(old, new, n=1):
    global src
    c = src.count(old)
    if c != n: sys.exit('count %d != %d for: %s' % (c, n, old[:100]))
    src = src.replace(old, new)

# ---- plots: unfinished (tabled)
rep('<label><input type="checkbox" id="lPlt" checked> Plots</label>', '<label><input type="checkbox" id="lPlt" checked> Plots (unfinished)</label>')
rep("function setPlotNote(t) { S.plNote = t; const el = $('plotNote'); if (el) el.textContent = t; }",
    "function setPlotNote(t) { S.plNote = t; const el = $('plotNote'); if (el) el.textContent = 'Plots, unfinished: ' + t.charAt(0).toLowerCase() + t.slice(1); }")
rep("<p>Plots (15 October): every block is divided into plots, measured and snapped.",
    "<p>Plots (15 October; unfinished, tabled): the lot lines were drawn without a check against the sheets and many do not follow them (Ben: Pleasant Court, and the block of Smith, Central, 2nd and 3rd, are the worst; angled lots where nothing is angled, as on Dalton between Sherman and Findlay); they are to be redrawn. As they stand: every block is divided into plots, measured and snapped.")
rep("    if (/~[a-z]$/.test(p.id)) kv('Cut off', 'by a street moved across the plot');\n    body.append(h, sub, dl);",
    "    if (/~[a-z]$/.test(p.id)) kv('Cut off', 'by a street moved across the plot');\n    body.append(h, sub, dl);\n    { const un = document.createElement('p'); un.className = 'notes'; un.textContent = 'Unfinished: the plot lines were drawn without a check against the sheets and are to be redrawn.'; body.append(un); }")
# ---- Union Terminal, concourse, plaza, former Lincoln Park (1931 plot plan)
rep("const OPEN_LAYERS = new Set(['boulevard', 'roundabout', 'forecourt', 'cut_square', 'we_forecourt',",
    "const OPEN_LAYERS = new Set(['cut_plaza', 'cut_lincoln', 'cut_concourse', 'boulevard', 'roundabout', 'forecourt', 'cut_square', 'we_forecourt',")
rep("  for (const f of feats('we_forecourt')) { ctx.save(); ctx.setLineDash([5, 4]); fillPoly(f.geometry, null, C.civic, 1.4, 0.9); ctx.restore(); }",
    "  for (const f of feats('we_forecourt')) { ctx.save(); ctx.setLineDash([5, 4]); fillPoly(f.geometry, null, C.civic, 1.4, 0.9); ctx.restore(); }\n"
    "  for (const f of feats('cut_lincoln')) { ctx.save(); ctx.setLineDash([7, 4]); fillPoly(f.geometry, C.park, C.park, 1.8, 0.16); ctx.restore(); }   // former Lincoln Park over its 1904 block")
rep("  for (const L of ['cut_square', 'forecourt']) for (const f of feats(L)) fillPoly(f.geometry, C.blvd, C['blvd-edge'], 1, 0.95);",
    "  for (const L of ['cut_square', 'forecourt', 'cut_plaza']) for (const f of feats(L)) fillPoly(f.geometry, C.blvd, C['blvd-edge'], 1, 0.95);\n"
    "  for (const f of feats('cut_concourse')) fillPoly(f.geometry, C.civic, C.ink, 0.8, 0.6);")
rep("[['palace', 'Cincinnati Palace'], ['cut_headhouse', 'West headhouse'], ['cut_square', 'Terminal square'], ['cut_building', 'Union Terminal']]",
    "[['palace', 'Cincinnati Palace'], ['cut_headhouse', 'West headhouse'], ['cut_square', 'Terminal square'], ['cut_building', 'Union Terminal'], ['cut_plaza', 'Terminal plaza'], ['cut_lincoln', 'Former Lincoln Park'], ['cut_concourse', 'Train concourse']]")
rep("  for (const L of ['palace', 'cut_headhouse', 'cut_building', 'cut_square', 'cut_park', 'forecourt', 'roundabout', 'boulevard', 'cut_precinct']) {",
    "  for (const L of ['palace', 'cut_headhouse', 'cut_building', 'cut_concourse', 'cut_square', 'cut_plaza', 'cut_park', 'cut_lincoln', 'forecourt', 'roundabout', 'boulevard', 'cut_precinct']) {")
rep("cut_precinct: 'CUT platforms and terminal', cut_building: 'Union Terminal' };",
    "cut_precinct: 'CUT platforms and terminal', cut_building: 'Union Terminal', cut_concourse: 'Train concourse (1933)', cut_plaza: 'Terminal plaza (1933)', cut_lincoln: 'Former Lincoln Park' };")
rep("    if (L === 'cut_precinct') sub.textContent = 'APEx platforms 1-16 under the concourse, Hopkins St to Kenner St';",
    "    if (L === 'cut_precinct') sub.textContent = 'APEx platforms 1-16 under the concourse, Hopkins St to Kenner St';\n"
    "    if (L === 'cut_building') sub.textContent = 'Traced from the architects\\u2019 plot plan of 1 June 1931 (HABS OH-705): the north and south wings, the rotunda (180 ft across) and the front';\n"
    "    if (L === 'cut_concourse') sub.textContent = 'The 1933 train concourse and waiting room over the platforms, as on the 1931 plot plan; the APEx field runs on west of its end to the west headhouse';\n"
    "    if (L === 'cut_plaza') sub.textContent = 'The forecourt on the 1931 plot plan: the curved bus and cab ramps, the plaza driveway and the cascade, from the terminal to the park; Dalton Avenue passes under it';\n"
    "    if (L === 'cut_lincoln') sub.textContent = 'Lincoln Park as the terminal\\u2019s approach on the 1931 plot plan: the north and south driveways and the planted mall, from the plaza to Freeman Avenue, over the park\\u2019s 1904 block and the line of President Place, which it replaces';")
# ---- region: zoom out to the bounds, cull tracks off screen, APEx station labels
rep('    <button class="btn" id="zWv">West side</button>', '    <button class="btn" id="zWv">West side</button>\n    <button class="btn" id="zReg" title="Erlanger, CVG Terminal 1, Eastgate and Aviation">Region</button>')
rep("$('zWv').onclick = () => fit(711450, 4331650, 712850, 4336550);", "$('zWv').onclick = () => fit(711450, 4331650, 712850, 4336550);\n$('zReg').onclick = () => fit(701600, 4320800, 736900, 4347000);")
rep("const clampS = s => Math.max(0.05, Math.min(6, s));", "const clampS = s => Math.max(0.02, Math.min(6, s));")
rep("      for (const t of S.ctx.tracks) { if ((t.sys === 'metro' && !S.layers.met) || (t.sys === 'rer' && !S.layers.rer)) continue; if (t.pid && live.has(t.pid)) continue;",
    "      const rT = cv.getBoundingClientRect(), [tx0, ty1] = S2W(0, 0), [tx1, ty0] = S2W(rT.width, rT.height), vbT = [tx0 - 50, ty0 - 50, tx1 + 50, ty1 + 50];\n      for (const t of S.ctx.tracks) { if ((t.sys === 'metro' && !S.layers.met) || (t.sys === 'rer' && !S.layers.rer)) continue; if (t.pid && live.has(t.pid)) continue; if (!t._bb) t._bb = bbOf(t.c); if (!bbHit(t._bb, vbT)) continue;")
rep("function drawTracks(v) {\n  const TF = S.tracks.features,",
    "function featBB(f) { const g = f.geometry; return g.type === 'Point' ? [g.coordinates[0], g.coordinates[1], g.coordinates[0], g.coordinates[1]] : bbOf(g.type === 'Polygon' ? g.coordinates[0] : g.coordinates); }\n"
    "function drawTracks(v) {\n  const r0 = cv.getBoundingClientRect(), [qx0, qy1] = S2W(0, 0), [qx1, qy0] = S2W(r0.width, r0.height), vbF = [qx0 - 80, qy0 - 80, qx1 + 80, qy1 + 80];\n"
    "  const TF = S.tracks.features.filter(f => bbHit(f._bb || (f._bb = featBB(f)), vbF)),")
rep("      ctx.fillStyle = p.kind === 'flag' ? C.warn : p.kind === 'portal' ? C.lower : C.panel; ctx.strokeStyle = p.kind === 'flag' ? C.warn : C.lower; ctx.lineWidth = 2;",
    "      ctx.fillStyle = p.kind === 'flag' ? C.warn : p.kind === 'portal' ? C.lower : C.panel; ctx.strokeStyle = p.kind === 'flag' ? C.warn : p.kind === 'region_station' ? C.apex : C.lower; ctx.lineWidth = 2;")
rep("    const t = p.layer === 'label' ? p.text : p.label; if (!show || !t) continue;",
    "    const t = p.layer === 'label' ? p.text : p.label; if (!(show || (S.layers.lab && p.kind === 'region_station')) || !t) continue;")
rep("    ctx.fillStyle = p.kind === 'flag' ? C.warn : (p.layer === 'label' && p.kind !== 'lower') ? C.ink : C.lower; ctx.fillText(t, lx, ly);",
    "    ctx.fillStyle = p.kind === 'flag' ? C.warn : p.kind === 'region_station' ? C.apex : (p.layer === 'label' && p.kind !== 'lower') ? C.ink : C.lower; ctx.fillText(t, lx, ly);")
# ---- CUT approaches panel
rep("  kv('APEx bridge', fmt(T.apb_off, 0) + ' m east of the CS bridge, ' + fmt(T.apb_g, 2) + '% up from W 8th');",
    "  kv('APEx bridge', 'four tracks' + (T.apb_brg ? ', bearing ' + fmt(T.apb_brg, 1) + '\\u00b0' : '') + '; ' + fmt(T.apb_off, 0) + ' m east of the CS bridge at the Ohio bank' + (T.apb_off_s != null ? ', ' + fmt(T.apb_off_s, 0) + ' m at the Kentucky bank' : '') + '; ' + fmt(T.apb_g, 2) + '% up from W 8th');\n"
    "  if (T.apb_r) kv('South approach curve', fmt(T.apb_r) + ' m radius, W 8th to W 6th');\n"
    "  if (T.region) kv('Region APEx (KMZ)', fmt(T.region.apex_km, 1) + ' km beyond the approaches, ' + fmt(T.region.four_track_km, 1) + ' km of it four-track');")
rep("The APEx crosses the Ohio on its own bridge just east of the CS bridge, where the APEx Routes KMZ puts it.",
    "South of the platforms the APEx follows Ben&rsquo;s General CUT Path KMZ (15 October): straight south on the field&rsquo;s centre line, one curve of about 814 m radius between W 8th and W 6th, then a straight crossing of the Ohio (bearing 204 degrees) on its own four-track bridge, centred on the KMZ line, 98 m east of the CS bridge at the Ohio bank and 28 m at the Kentucky bank. The line then runs into the CS corridor: the drawn tracks end 120 m into Ludlow, where the APEx centre line reaches the CS line, and south of that the KMZ line runs along the CS (CVG Express) line through Ludlow and Bromley, crossing it several times; whether the two lie side by side there or cross at separate levels is not set.")
rep("      <p>CUT tracks: APEx lines from the APEx Routes KMZ;",
    "      <p>Union Terminal (15 October): the building, its train concourse, the plaza and the former Lincoln Park are traced from the architects&rsquo; plot plan of 1 June 1931 (HABS OH-705, sheet 1, Ben&rsquo;s scan) and fitted to the plan by five street crossings, Dalton, Denman and Freeman on Kenner and Hopkins (affine, within 0.5-1.1 m). The rotunda measures 180 ft across on the drawing. The plaza replaces the open east forecourt; the former Lincoln Park is drawn over the park&rsquo;s 1904 block. Curran Street (under the building) and President Place (at the plaza&rsquo;s east edge) are still drawn from the 1904 sheets.</p>\n"
    "      <p>Region (15 October): RER and APEx are drawn out to Erlanger, CVG Terminal 1, Eastgate and Aviation (E 701,600-736,900, N 4,320,800-4,347,000; the Region button). Outside the plan window the RER is Cincinnati Rail.kmz as drawn (shared trunks once), with its stations, tracks and 670 ft island platforms, curves fitted as inside; the APEx is APEx Routes.kmz as drawn, leaving from the ends of the designed CUT approaches by tangent joins, with four tracks where two or more Tier 1 routes share a corridor (the Kentucky trunk from the four-track bridge through Erlanger, the north trunk to the Vandalia/Norwood split) and two elsewhere. Outside the designed approaches track counts and spacing are drawing values. The Metro stays inside the plan window, and the Sanborn sheets end at the plan.</p>\n"
    "      <p>CUT tracks: APEx lines from the APEx Routes KMZ;")

# ---- area labels: area centroid, Union Terminal first, skip a label that would overlap one already set
rep("    for (const [L, nm] of [['palace', 'Cincinnati Palace'], ['cut_headhouse', 'West headhouse'], ['cut_square', 'Terminal square'], ['cut_building', 'Union Terminal'], ['cut_plaza', 'Terminal plaza'], ['cut_lincoln', 'Former Lincoln Park'], ['cut_concourse', 'Train concourse']]) for (const f of feats(L)) {\n      const r0 = polysOf(f.geometry)[0][0], cx = r0.reduce((s, q) => s + q[0], 0) / r0.length, cy = r0.reduce((s, q) => s + q[1], 0) / r0.length, [x, y] = W2S(cx, cy);\n      ctx.font = '700 13px ' + css('--font-ui'); const tw = ctx.measureText(nm).width; ctx.fillStyle",
    "    const setL = [];\n    for (const [L, nm] of [['palace', 'Cincinnati Palace'], ['cut_building', 'Union Terminal'], ['cut_headhouse', 'West headhouse'], ['cut_square', 'Terminal square'], ['cut_plaza', 'Terminal plaza'], ['cut_lincoln', 'Former Lincoln Park'], ['cut_concourse', 'Train concourse']]) for (const f of feats(L)) {\n      const [cx, cy] = ringCentroid(polysOf(f.geometry)[0][0]), [x, y] = W2S(cx, cy);\n      ctx.font = '700 13px ' + css('--font-ui'); const tw = ctx.measureText(nm).width, bx = [x - tw / 2 - 3, y - 9, x + tw / 2 + 3, y + 9];\n      if (setL.some(b => b[0] < bx[2] && bx[0] < b[2] && b[1] < bx[3] && bx[1] < b[3])) continue; setL.push(bx); ctx.fillStyle")
rep("function featBB(f) {", "function ringCentroid(r) { let a = 0, x = 0, y = 0; const [ox, oy] = r[0]; for (let i = 0; i < r.length - 1; i++) { const x0 = r[i][0] - ox, y0 = r[i][1] - oy, x1 = r[i + 1][0] - ox, y1 = r[i + 1][1] - oy, k = x0 * y1 - x1 * y0; a += k; x += (x0 + x1) * k; y += (y0 + y1) * k; }\n  return Math.abs(a) < 1e-9 ? [r.reduce((s, q) => s + q[0], 0) / r.length, r.reduce((s, q) => s + q[1], 0) / r.length] : [ox + x / (3 * a), oy + y / (3 * a)]; }\nfunction featBB(f) {")
# ---- region APEx readable when zoomed out; the 1933 concourse outlined over the tracks it spans; the RER bound stations named
rep("    if (p.layer === 'apex') { ctx.strokeStyle = C.apex; ctx.lineWidth = lw; ctx.setLineDash([]); ctx.globalAlpha = 0.95; }",
    "    if (p.layer === 'apex') { ctx.strokeStyle = C.apex; ctx.lineWidth = p.kind === 'region' && v.s < 0.2 ? 1.3 : lw; ctx.setLineDash([]); ctx.globalAlpha = 0.95; }")
rep("  ctx.setLineDash([]); ctx.globalAlpha = 1;\n  const show = S.layers.lab && v.s > 0.3;",
    "  ctx.globalAlpha = 0.85; ctx.strokeStyle = C.ink; ctx.lineWidth = 1.2; ctx.setLineDash([6, 4]);   // the 1933 concourse, over the platforms\n"
    "  for (const f of feats('cut_concourse')) for (const pg of polysOf(f.geometry)) { ctx.beginPath(); pathLine(pg[0]); ctx.closePath(); ctx.stroke(); }\n"
    "  ctx.setLineDash([]); ctx.globalAlpha = 1;\n  const show = S.layers.lab && v.s > 0.3;\n"
    "  if (S.layers.lab && S.layers.rer && v.s < 0.3 && S.ctx) { ctx.font = '600 12px ' + css('--font-ui'); ctx.textBaseline = 'middle';   // the region's RER bounds\n"
    "    for (const s of (S.ctx.rer_stations || [])) { if (s.name !== 'Aviation' && s.name !== 'CVG Terminal 1') continue; const [x, y] = W2S(s.p[0], s.p[1]), t = s.name + ' (RER ' + s.lines.join(' ') + ')', tw = ctx.measureText(t).width, lx = s.name === 'Aviation' ? x + 9 : x - 6, ly = s.name === 'Aviation' ? y : y - 16;\n"
    "      ctx.fillStyle = C.panel; ctx.globalAlpha = 0.88; ctx.fillRect(lx - 3, ly - 9, tw + 6, 18); ctx.globalAlpha = 1; ctx.fillStyle = C.rer; ctx.fillText(t, lx, ly); } }")
rep("$('zReg').onclick = () => fit(701600, 4320800, 736900, 4347000);", "$('zReg').onclick = () => fit(701000, 4320300, 737500, 4347500);")

# ---- Dalton's underpass under the plaza: drawn below it (translucent, dashed walls), not as a surface street
rep("      const al = f.properties.kind === 'we_alley', wb = Math.max(al ? 0.8 : 1.2, streetWidth(f) * v.s), c = streetCoords(f);",
    "      if (f.properties.structure === 'underpass') continue;\n      const al = f.properties.kind === 'we_alley', wb = Math.max(al ? 0.8 : 1.2, streetWidth(f) * v.s), c = streetCoords(f);")
rep("    // viaducts: dashed edges\n",
    "    for (const f of ord) { if (f.properties.structure !== 'underpass') continue; const c = streetCoords(f), wb = Math.max(1.2, streetWidth(f) * v.s);   // underpasses: below the plaza\n"
    "      ctx.globalAlpha = 0.3; ctx.strokeStyle = C.bst; ctx.lineWidth = wb; ctx.setLineDash([]); ctx.beginPath(); pathLine(c); ctx.stroke();\n"
    "      ctx.globalAlpha = 0.85; ctx.strokeStyle = C.ink; ctx.lineWidth = 1.2; ctx.setLineDash([6, 4]);\n"
    "      for (const sgn of [-1, 1]) { ctx.beginPath(); pathLine(offsetLine(c, sgn * (wb / 2) / v.s)); ctx.stroke(); }\n"
    "      ctx.setLineDash([]); }\n"
    "    // viaducts: dashed edges\n")
rep("    h.textContent = p.name; sub.textContent = (p.src === 'Sanborn 1922' ?",
    "    h.textContent = p.name; sub.textContent = p.structure === 'underpass' ? 'Underpass under the terminal plaza, Hopkins to Kenner (1931 plot plan; walls 10.8 m apart)' : (p.src === 'Sanborn 1922' ?")
rep(" Curran Street (under the building) and President Place (at the plaza&rsquo;s east edge) are still drawn from the 1904 sheets.</p>",
    " Dalton Avenue runs on under the plaza from Hopkins to Kenner in an underpass (dashed on the plan; walls 10.8 m apart, on the 1904 line). President Place is gone, its land taken into the park, and Curran Street, under the building and the plaza driveway, is gone too.</p>")
open(SP + 'deckpage/index.html', 'w').write(src)
print('ok v36', len(src))
