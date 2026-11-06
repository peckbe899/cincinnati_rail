try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 42 (Ben, 16 October): CVG Express platforms 200 m (four 50 m or three 67 m units) and the same station rules as the RER and Metro:
# the airside line from the split to the yard (tracks.json 'cvx') joins the station editor as a third system 'cvx' (line editable, platforms
# movable along it, island or side, delete/restore, reset). Chain: ... patch_v41.py && patch_v42.py
import sys
SP = _ws.DATA
src = open(SP + 'deckpage/index.html').read()
def rep(old, new, n=1):
    global src
    c = src.count(old)
    if c != n: sys.exit('count %d != %d for: %s' % (c, n, old[:110]))
    src = src.replace(old, new)

# ---- load tracks.json before the transit features are built
rep("  Object.assign(S, { deck, ctx: cx, sheets, tiles, relief }); buildTransitFeats();\n  try { S.tracks = await fetch('tracks.json').then(r => r.json()); } catch (e) { S.tracks = null; }",
    "  Object.assign(S, { deck, ctx: cx, sheets, tiles, relief });\n  try { S.tracks = await fetch('tracks.json').then(r => r.json()); } catch (e) { S.tracks = null; }\n  buildTransitFeats();")
# ---- the third system
rep("const visT = f => f.properties.sys === 'metro' ? S.layers.met : S.layers.rer;",
    "const visT = f => f.properties.sys === 'metro' ? S.layers.met : f.properties.sys === 'cvx' ? S.layers.trk : S.layers.rer;\n"
    "const CVX = () => (S.tracks && S.tracks.cvx) || null;   // the CVG Express airside line (tracks.json), edited like the RER and Metro")
rep("const PW = { metro: { island: 8.0, side: 4.0 }, rer: { island: 11.0, side: 6.0 } };   // platform widths: drawing values",
    "const PW = { metro: { island: 8.0, side: 4.0 }, rer: { island: 11.0, side: 6.0 }, cvx: { island: 10.0, side: 6.0 } };   // platform widths: drawing values")
rep("const H0 = (sys, era) => sys === 'rer' ? 2.25 : era === 'twin' ? 4.0 : 1.95, EDGE = sys => sys === 'rer' ? 1.75 : 1.45, TAPER = 40;",
    "const H0 = (sys, era) => sys === 'rer' || sys === 'cvx' ? 2.25 : era === 'twin' ? 4.0 : 1.95, EDGE = sys => sys === 'rer' ? 1.75 : sys === 'cvx' ? 1.6 : 1.45, TAPER = 40;")
rep("  S.ctx.plats.forEach((q, i) => S.pf.push({ type: 'Feature', properties: { layer: 'plat', sys: q.sys, line: q.line, id: q.id || 'P' + i, pid: q.pid || null, st: q.st || '', name: q.name || '' }, geometry: { type: 'Polygon', coordinates: [q.c] } }));\n  buildStations();",
    "  S.ctx.plats.forEach((q, i) => S.pf.push({ type: 'Feature', properties: { layer: 'plat', sys: q.sys, line: q.line, id: q.id || 'P' + i, pid: q.pid || null, st: q.st || '', name: q.name || '' }, geometry: { type: 'Polygon', coordinates: [q.c] } }));\n"
    "  const X = CVX(); S.ctx.tracks = (S.ctx.tracks || []).filter(t => t.sys !== 'cvx');\n"
    "  if (X) { const f = { type: 'Feature', properties: { layer: 'transit', sys: 'cvx', id: X.id, name: X.name, sub: 'airside, deep-bored, GoA3', k: X.k }, geometry: { type: 'LineString', coordinates: X.v } }; S.tf.push(f); S.tfById.set(X.id, f);\n"
    "    X.plats.forEach(q => S.pf.push({ type: 'Feature', properties: { layer: 'plat', sys: 'cvx', line: q.line, id: q.id, pid: q.pid, st: q.st, name: '' }, geometry: { type: 'Polygon', coordinates: [q.c] } }));\n"
    "    for (const t of X.tracks) S.ctx.tracks.push(t); }\n"
    "  buildStations();")
rep("  for (const s of (S.ctx.rer_stations || [])) add('rer', s.name, 'RER ' + s.lines.join(' '), s.p);",
    "  for (const s of (S.ctx.rer_stations || [])) add('rer', s.name, 'RER ' + s.lines.join(' '), s.p);\n"
    "  if (CVX()) for (const s of CVX().stations) add('cvx', s.name, 'CVG Express', s.p);")
rep("sys = q0.sys, L = sys === 'rer' ? (S.ctx.meta.rer_platform_m || 204.2) : (S.ctx.meta.metro_platform_m || 152.4);",
    "sys = q0.sys, L = sys === 'cvx' ? (CVX().platform_m || 200) : sys === 'rer' ? (S.ctx.meta.rer_platform_m || 204.2) : (S.ctx.meta.metro_platform_m || 152.4);")
# ---- drawing: platforms, generated tracks (dashed in tunnel), tracks from settings, centre line and station dots
rep("      for (const st of S.sf) { if (!visT(st)) continue; const col = st.properties.sys === 'metro' ? C.metro : C.rer;",
    "      for (const st of S.sf) { if (!visT(st)) continue; const col = st.properties.sys === 'metro' ? C.metro : st.properties.sys === 'cvx' ? C.cvg : C.rer;")
rep("      for (const t of S.ctx.tracks) { if ((t.sys === 'metro' && !S.layers.met) || (t.sys === 'rer' && !S.layers.rer)) continue; if (t.pid && live.has(t.pid)) continue; if (!t._bb) t._bb = bbOf(t.c); if (!bbHit(t._bb, vbT)) continue;\n"
    "        ctx.globalAlpha = 1; ctx.strokeStyle = t.sys === 'metro' ? C.metro : C.rer; ctx.lineWidth = tw; ctx.setLineDash(t.sys === 'metro' ? [6, 3] : []); ctx.beginPath(); pathLine(t.c); ctx.stroke(); }",
    "      for (const t of S.ctx.tracks) { if ((t.sys === 'metro' && !S.layers.met) || (t.sys === 'rer' && !S.layers.rer) || (t.sys === 'cvx' && !S.layers.trk)) continue; if (t.pid && live.has(t.pid)) continue; if (!t._bb) t._bb = bbOf(t.c); if (!bbHit(t._bb, vbT)) continue;\n"
    "        ctx.globalAlpha = 1; ctx.strokeStyle = t.sys === 'metro' ? C.metro : t.sys === 'cvx' ? C.cvg : C.rer; ctx.lineWidth = tw; ctx.setLineDash(t.sys === 'metro' ? [6, 3] : t.sys === 'cvx' && !t.open ? [7, 4] : []); ctx.beginPath(); pathLine(t.c); ctx.stroke(); }")
rep("        ctx.globalAlpha = 1; ctx.strokeStyle = f.properties.sys === 'metro' ? C.metro : C.rer; ctx.lineWidth = tw; ctx.setLineDash(f.properties.sys === 'metro' ? [6, 3] : []);",
    "        ctx.globalAlpha = 1; ctx.strokeStyle = f.properties.sys === 'metro' ? C.metro : f.properties.sys === 'cvx' ? C.cvg : C.rer; ctx.lineWidth = tw; ctx.setLineDash(f.properties.sys === 'metro' ? [6, 3] : f.properties.sys === 'cvx' ? [7, 4] : []);")
rep("  if (S.ctx && S.layers.rer && S.ctx.rer_struct) drawRerStruct(v);",
    "  if (S.ctx && S.layers.trk && CVX()) {   // CVG Express airside: centre line when zoomed out, station dots and names\n"
    "    ctx.save(); if (v.s < 0.8) { ctx.strokeStyle = C.cvg; ctx.lineWidth = 2.5; ctx.setLineDash([7, 4]); for (const f of S.tf) { if (f.properties.sys !== 'cvx') continue; ctx.beginPath(); pathLine(lineCoords(f)); ctx.stroke(); } ctx.setLineDash([]); }\n"
    "    for (const f of S.sf) { if (f.properties.sys !== 'cvx') continue; const st = f.properties, [x, y] = W2S(...f.geometry.coordinates); if (stDeleted(f)) { drawGhost(x, y, C.cvg); continue; }\n"
    "      ctx.fillStyle = C.panel; ctx.strokeStyle = C.cvg; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.arc(x, y, 5, 0, 7); ctx.fill(); ctx.stroke();\n"
    "      if (S.layers.lab && v.s > 0.06) { ctx.font = '700 12px ' + css('--font-ui'); const t = st.name + ' (CVG Express)', tw = ctx.measureText(t).width, lx = st.name === 'Terminal 1A' ? x - 10 - tw : x + 10, ly = y + (st.name === 'Terminal 1B' ? -14 : 14);\n"
    "        ctx.fillStyle = C.panel; ctx.globalAlpha = 0.88; ctx.fillRect(lx - 3, ly - 8, tw + 6, 16); ctx.globalAlpha = 1; ctx.fillStyle = C.cvg; ctx.textBaseline = 'middle'; ctx.fillText(t, lx, ly); } }\n"
    "    ctx.restore(); }\n"
    "  if (S.ctx && S.layers.rer && S.ctx.rer_struct) drawRerStruct(v);")
# the v41 platform picking goes (the platforms are stations now)
rep("  if (!area && S.layers.trk && S.tracks) for (const L of ['cvg_plat', 'cvg_shop', 'cvg_yard'])", "  if (!area && S.layers.trk && S.tracks) for (const L of ['cvg_shop', 'cvg_yard'])")
# ---- panels
rep("h.textContent = featLabel(f); sub.textContent = 'Centre line' + (p.sys === 'metro' ? (p.era === 'twin' ? ' · twin tubes (Lines 1-7)' : ' · one double-track bore (Lines 8-14)') : '') + (p.sub ? ' · ' + p.sub : '');",
    "h.textContent = featLabel(f); sub.textContent = 'Centre line' + (p.sys === 'metro' ? (p.era === 'twin' ? ' · twin tubes (Lines 1-7)' : ' · one double-track bore (Lines 8-14)') : p.sys === 'cvx' ? ' · CVG Express from the split east of CVG to the yard (CVG Express Final.kmz)' : '') + (p.sub ? ' · ' + p.sub : '');")
rep("n.textContent = 'Once edited, the tracks are redrawn as a pair along your line (Metro twin tubes 8 m apart, bores 3.9 m, RER 4.5 m)",
    "n.textContent = 'Once edited, the tracks are redrawn as a pair along your line (Metro twin tubes 8 m apart, bores 3.9 m, RER and CVG Express 4.5 m)")
rep("h.textContent = p.name; sub.textContent = (p.sys === 'metro' ? 'Metro station · ' + p.line.replace(/ Line /g, ', Line ') : 'RER station · ' + p.line) + (del ? ' · deleted' : '');",
    "h.textContent = p.name; sub.textContent = (p.sys === 'metro' ? 'Metro station · ' + p.line.replace(/ Line /g, ', Line ') : p.sys === 'cvx' ? 'CVG Express station (airside) · deep-bored, GoA3, platform screen doors' : 'RER station · ' + p.line) + (del ? ' · deleted' : '');")
rep("    kv('Edited', S.edits.stations[p.id] ? 'yes' : 'no'); body.append(h, sub, dl);",
    "    if (p.sys === 'cvx') { const q = CVX().stations.find(s => s.name === p.name); if (q) { kv('Rail', fmt(q.z, 1) + ' m, ' + fmt(q.depth, 1) + ' m under the ground (' + fmt(q.ground, 1) + ' m)'); kv('From CUT', fmt(q.km, 2) + ' km from the south end of platform M (station point)'); } }\n"
    "    kv('Edited', S.edits.stations[p.id] ? 'yes' : 'no'); body.append(h, sub, dl);")
rep("'Platforms are ' + (p.sys === 'rer' ? '670 ft (RER)' : '500 ft (Metro)') + ', as ruled;",
    "'Platforms are ' + (p.sys === 'rer' ? '670 ft (RER)' : p.sys === 'cvx' ? fmt(CVX().platform_m) + ' m (CVG Express: four 50 m or three 67 m units), with screen doors' : '500 ft (Metro)') + ', as ruled;")
# ---- export
rep("out.push({ type: 'Feature', properties: { layer: p.sys === 'metro' ? 'metro_line' : 'rer_line',", "out.push({ type: 'Feature', properties: { layer: p.sys === 'metro' ? 'metro_line' : p.sys === 'cvx' ? 'cvx_line' : 'rer_line',")
rep("out.push({ type: 'Feature', properties: { layer: p.sys === 'metro' ? 'metro_station' : 'rer_station',", "out.push({ type: 'Feature', properties: { layer: p.sys === 'metro' ? 'metro_station' : p.sys === 'cvx' ? 'cvx_station' : 'rer_station',")
rep("out.push({ type: 'Feature', properties: { layer: p.sys === 'metro' ? 'metro_platform' : 'rer_platform',", "out.push({ type: 'Feature', properties: { layer: p.sys === 'metro' ? 'metro_platform' : p.sys === 'cvx' ? 'cvx_platform' : 'rer_platform',")
rep("else if (L === 'tri_prop' || L === 'rer_line' || L === 'rer_platform' || L === 'rer_station') style = 'tri';",
    "else if (L === 'tri_prop' || L === 'rer_line' || L === 'rer_platform' || L === 'rer_station' || L === 'cvx_line' || L === 'cvx_platform' || L === 'cvx_station') style = 'tri';")
# ---- CUT approaches panel and notes
rep("' m apart), then ' + fmt(V.yard.g_up, 1) + '% up to the yard'); }", "' m apart; ' + fmt(V.plat) + ' m platforms, movable like the RER and Metro), then ' + fmt(V.yard.g_up, 1) + '% up to the yard'); }")
rep("then a 292 m curve (380 m in Ben&rsquo;s drawing, tightened so the T1B platform is straight) onto the 1969 line west through T1B and T1A. The stations are 150 m side platforms with screen doors (GoA3), at Ben&rsquo;s stop points, 366, 266, 818 and 672 m apart and 21 to 29 m below the ground; T3 is 15.3 km and T1A 17.4 km from the south end of platform M. Beyond T1A the line curves north (475 m)",
    "then a 380 m curve onto the 1969 line west through T1B and T1A. The stations are at Ben&rsquo;s stop points, 366, 266, 818 and 672 m apart and 21 to 29 m below the ground; T3 is 15.3 km and T1A 17.4 km from the south end of platform M. The platforms are 200 m (Ben: four 50 m or three 67 m units), side platforms with screen doors (GoA3) as drawn, centred on the stop points except at T1B (80 m west, so it clears the 380 m curve) and T1A (14 m east, clear of the curve to the yard). From the split to the yard the line is in the station editor like the RER and Metro: select a station to move its platforms along the line, make them island or side, or delete it; the line itself can be edited. Beyond T1A the line curves north (475 m)")
# the airport is a base layer: draw it before the transit lines, so stations, platforms and labels sit on top of the terminal buildings
rep("  if (S.layers.apt && S.airport) drawAirport(v);\n  if (S.layers.trk && S.tracks) drawTracks(v);", "  if (S.layers.trk && S.tracks) drawTracks(v);")
rep("  // transit\n  if (S.ctx) {\n    const showT = v.s >= 0.8 && S.ctx.tracks;", "  if (S.layers.apt && S.airport) drawAirport(v);\n  // transit\n  if (S.ctx) {\n    const showT = v.s >= 0.8 && S.ctx.tracks;")
open(SP + 'deckpage/index.html', 'w').write(src)
print('ok v42', len(src))
