try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 37: Union Terminal from the architects' first-floor plan (building with its ramp arms) and the 1931 plot plan (field, plaza
# roads, lawns, terrace); concourse on to the west headhouse; CUT layers; CVG Express on platform M with a flyover; Ludlow approaches.
# Chain: python3 plots/patch_page.py && python3 plots/patch_v34.py && python3 plots/patch_v36.py && python3 plots/patch_v37.py
import sys
SP = _ws.DATA
src = open(SP + 'deckpage/index.html').read()
def rep(old, new, n=1):
    global src
    c = src.count(old)
    if c != n: sys.exit('count %d != %d for: %s' % (c, n, old[:110]))
    src = src.replace(old, new)

# ---- CUT layers
rep('        <label><input type="checkbox" id="lTrk" checked> CUT tracks</label>',
    '        <label><input type="checkbox" id="lTrk" checked> CUT tracks</label>\n'
    '        <div class="sublayers" style="margin:2px 0 4px 22px;display:grid;gap:2px">\n'
    '          <span style="font-size:11px;color:var(--muted)">Union Terminal</span>\n'
    '          <label><input type="checkbox" id="lCB" checked> Building</label>\n'
    '          <label><input type="checkbox" id="lCC" checked> Train concourse</label>\n'
    '          <label><input type="checkbox" id="lCR" checked> Roads and ramps</label>\n'
    '          <label><input type="checkbox" id="lCP" checked> Plaza, terrace and park</label>\n'
    '          <label><input type="checkbox" id="lCA" checked> Platform level (APEx, CVG)</label>\n'
    '          <label><input type="checkbox" id="lCL" checked> Lower level and intercity</label>\n'
    '        </div>')
rep("layers: { san: true, rel: false, blk: true, str: true, met: true, rer: true, trk: true, lab: true, idx: false, we: true, s12: false, plt: true },",
    "layers: { san: true, rel: false, blk: true, str: true, met: true, rer: true, trk: true, lab: true, idx: false, we: true, s12: false, plt: true, cutB: true, cutC: true, cutR: true, cutP: true, cutA: true, cutL: true },")
rep("['lIdx', 'idx'], ['lWe', 'we'], ['l12', 's12'], ['lPlt', 'plt']]) $(id).addEventListener",
    "['lIdx', 'idx'], ['lWe', 'we'], ['l12', 's12'], ['lPlt', 'plt'], ['lCB', 'cutB'], ['lCC', 'cutC'], ['lCR', 'cutR'], ['lCP', 'cutP'], ['lCA', 'cutA'], ['lCL', 'cutL']]) $(id).addEventListener")
rep("const OPEN_LAYERS = new Set(['cut_plaza', 'cut_lincoln', 'cut_concourse',",
    "const CUT_ON = L => !({ cut_building: 'cutB', cut_concourse: 'cutC', cut_road: 'cutR', cut_plaza: 'cutP', cut_lincoln: 'cutP', cut_lawn: 'cutP', cut_terrace: 'cutP', cut_walk: 'cutP' }[L]) || S.layers[{ cut_building: 'cutB', cut_concourse: 'cutC', cut_road: 'cutR', cut_plaza: 'cutP', cut_lincoln: 'cutP', cut_lawn: 'cutP', cut_terrace: 'cutP', cut_walk: 'cutP' }[L]];\n"
    "const OPEN_LAYERS = new Set(['cut_road', 'cut_terrace', 'cut_lawn', 'cut_plaza', 'cut_lincoln', 'cut_concourse',")
# ---- drawing order: plaza, lawns, terrace, walks, building, then the roads and ramps on top
rep("  for (const f of feats('cut_lincoln')) { ctx.save(); ctx.setLineDash([7, 4]); fillPoly(f.geometry, C.park, C.park, 1.8, 0.16); ctx.restore(); }   // former Lincoln Park over its 1904 block",
    "  if (S.layers.cutP) for (const f of feats('cut_lincoln')) { ctx.save(); ctx.setLineDash([7, 4]); fillPoly(f.geometry, C.park, C.park, 1.8, 0.16); ctx.restore(); }   // former Lincoln Park over its 1904 block")
rep("  for (const L of ['cut_square', 'forecourt', 'cut_plaza']) for (const f of feats(L)) fillPoly(f.geometry, C.blvd, C['blvd-edge'], 1, 0.95);\n"
    "  for (const f of feats('cut_concourse')) fillPoly(f.geometry, C.civic, C.ink, 0.8, 0.6);",
    "  for (const L of ['cut_square', 'forecourt', 'cut_plaza']) for (const f of feats(L)) if (CUT_ON(L)) fillPoly(f.geometry, C.blvd, C['blvd-edge'], 1, 0.95);\n"
    "  if (S.layers.cutP) {   // the 1931 plot plan's lawns, terrace and walks\n"
    "    for (const f of feats('cut_lawn')) fillPoly(f.geometry, C.park, C.park, 0.6, 0.62);\n"
    "    for (const f of feats('cut_terrace')) fillPoly(f.geometry, C.paper, C.ink, 1, 0.95);\n"
    "    ctx.save(); ctx.strokeStyle = C.blvd; ctx.globalAlpha = 0.95; ctx.lineWidth = Math.max(1, 2.6 * v.s);\n"
    "    for (const f of feats('cut_walk')) { if (f.geometry.type === 'LineString') { ctx.beginPath(); pathLine(f.geometry.coordinates); ctx.stroke(); } else fillPoly(f.geometry, C.blvd, C.ink, 0.6, 0.95); }\n"
    "    ctx.restore(); }\n"
    "  if (S.layers.cutC) for (const f of feats('cut_concourse')) fillPoly(f.geometry, C.civic, C.ink, 0.8, 0.6);")
rep("  for (const L of ['palace', 'cut_headhouse', 'cut_building']) for (const f of feats(L)) fillPoly(f.geometry, C.civic, C.ink, 1, 0.95);",
    "  for (const L of ['palace', 'cut_headhouse', 'cut_building']) for (const f of feats(L)) if (CUT_ON(L)) fillPoly(f.geometry, C.civic, C.ink, L === 'cut_building' ? 1.8 : 1, 0.95);\n"
    "  if (S.layers.cutR) for (const f of feats('cut_road')) fillPoly(f.geometry, C.bst, C.ink, 0.9, f.properties.kind === 'ramp' ? 0.32 : 0.92);   // roads and ramps on top (ramps see-through, over the building's arms)")
# concourse outline over the platforms only when the concourse layer is on
rep("  for (const f of feats('cut_concourse')) for (const pg of polysOf(f.geometry)) { ctx.beginPath(); pathLine(pg[0]); ctx.closePath(); ctx.stroke(); }",
    "  if (S.layers.cutC) for (const f of feats('cut_concourse')) for (const pg of polysOf(f.geometry)) { ctx.beginPath(); pathLine(pg[0]); ctx.closePath(); ctx.stroke(); }")
# platform level and lower level toggles in the track layer
rep("  const TF = S.tracks.features.filter(f => bbHit(f._bb || (f._bb = featBB(f)), vbF)),",
    "  const lvlOn = p => (p.layer === 'apex_plat' || p.layer === 'passing' || (p.layer === 'apex' && (p.kind === 'platform' || p.kind === 'throat'))) ? S.layers.cutA : (p.layer === 'lower' || p.layer === 'lower_plat') ? S.layers.cutL : true;\n"
    "  const TF = S.tracks.features.filter(f => lvlOn(f.properties) && bbHit(f._bb || (f._bb = featBB(f)), vbF)),")
# track numbers: any name with a number
rep("ctx.fillText(p.name.replace('APEx track ', ''), x, y); }", "ctx.fillText((p.name.match(/\\d+/) || [''])[0], x, y); }")
# ---- labels and picking
rep("for (const [L, nm] of [['palace', 'Cincinnati Palace'], ['cut_building', 'Union Terminal'], ['cut_headhouse', 'West headhouse'], ['cut_square', 'Terminal square'], ['cut_plaza', 'Terminal plaza'], ['cut_lincoln', 'Former Lincoln Park'], ['cut_concourse', 'Train concourse']]) for (const f of feats(L)) {",
    "for (const [L, nm] of [['palace', 'Cincinnati Palace'], ['cut_building', 'Union Terminal'], ['cut_headhouse', 'West headhouse'], ['cut_square', 'Terminal square'], ['cut_terrace', 'Terrace'], ['cut_plaza', 'Terminal plaza'], ['cut_lincoln', 'Former Lincoln Park'], ['cut_concourse', 'Train concourse']]) for (const f of feats(L)) { if (!CUT_ON(L)) continue;")
rep("  for (const L of ['palace', 'cut_headhouse', 'cut_building', 'cut_concourse', 'cut_square', 'cut_plaza', 'cut_park', 'cut_lincoln', 'forecourt', 'roundabout', 'boulevard', 'cut_precinct']) { for (const f of feats(L)) if (polysOf(f.geometry).some(q => inPoly(p, q))) { area = f; break; } if (area) break; }",
    "  for (const L of ['palace', 'cut_headhouse', 'cut_road', 'cut_terrace', 'cut_building', 'cut_concourse', 'cut_square', 'cut_plaza', 'cut_park', 'cut_lincoln', 'forecourt', 'roundabout', 'boulevard', 'cut_precinct']) { if (!CUT_ON(L)) continue; for (const f of feats(L)) if (polysOf(f.geometry).some(q => inPoly(p, q))) { area = f; break; } if (area) break; }")
rep("cut_concourse: 'Train concourse (1933)', cut_plaza: 'Terminal plaza (1933)', cut_lincoln: 'Former Lincoln Park' };",
    "cut_concourse: 'Train concourse (1933), on to the west headhouse', cut_plaza: 'Terminal plaza (1933)', cut_lincoln: 'Former Lincoln Park', cut_terrace: 'Terrace and cascade (1933)' };")
rep("    if (L === 'cut_precinct') sub.textContent = 'APEx platforms 1-16 under the concourse, Hopkins St to Kenner St';",
    "    if (L === 'cut_precinct') sub.textContent = 'APEx platforms 1-14 and CVG Express 15-16 (platform M) under the concourse, Hopkins St to Kenner St';\n"
    "    if (L === 'cut_road') sub.textContent = p.kind === 'ramp' ? 'Ramp down from the plaza to the bus and cab concourse at track level (1931 plot plan)' : 'Drive on the 1931 plot plan';\n"
    "    if (L === 'cut_terrace') sub.textContent = 'The terrace with its pools and cascade, inside the plaza driveway (1931 plot plan)';")
rep("    if (L === 'cut_building') sub.textContent = 'Traced from the architects\\u2019 plot plan of 1 June 1931 (HABS OH-705): the north and south wings, the rotunda (180 ft across) and the front';",
    "    if (L === 'cut_building') sub.textContent = 'From the architects\\u2019 first-floor plan, fitted to the 1931 plot plan: the wings, the concourse rotunda, the front and the curved bus and cab ramp arms';")
rep("    if (L === 'cut_concourse') sub.textContent = 'The 1933 train concourse and waiting room over the platforms, as on the 1931 plot plan; the APEx field runs on west of its end to the west headhouse';",
    "    if (L === 'cut_concourse') sub.textContent = 'The 1933 train concourse and waiting room, a bridge over the platforms (first-floor plan), carried on west over the field to the west headhouse';")
# ---- CUT approaches panel
rep("  if (T.apb_r) kv('South approach curve', fmt(T.apb_r) + ' m radius, W 8th to W 6th');",
    "  if (T.apb_r) kv('South approach curve', fmt(T.apb_r) + ' m radius, W 8th to W 6th');\n"
    "  if (T.field) kv('Platform field (1931 plan)', 'pairs ' + fmt(T.field.pair, 2) + ' m, ' + fmt(T.field.island, 2) + ' m across an island, ' + fmt(T.field.unit, 2) + ' m a unit; platform M beside the building');\n"
    "  if (T.cvg) kv('CVG Express (M, 15-16)', fmt(T.cvg.g_up, 2) + '% up to ' + fmt(T.cvg.z_x, 1) + ' m over the APEx (' + fmt(T.cvg.z_apex, 1) + ' m), then ' + fmt(T.cvg.g_down, 2) + '% down to the CS bridge; tightest curve ' + fmt(T.cvg.r_min) + ' m');\n"
    "  if (T.lud) kv('Ludlow (Kentucky)', 'CS line 2 at grade + APEx 4, ' + fmt(T.lud.gap, 2) + ' m centre to centre; APEx ' + fmt(T.lud.g, 1) + '% up, ' + fmt(T.lud.z_apex, 1) + ' m over the CS line (' + fmt(T.lud.clear, 1) + ' m clear, ' + fmt(T.lud.skew, 0) + '\\u00b0 skew), ' + fmt(T.lud.s_from_bank) + ' m from the bank');")
# ---- notes
rep("South of the platforms the APEx follows Ben&rsquo;s General CUT Path KMZ (15 October): straight south on the field&rsquo;s centre line, one curve of about 814 m radius between W 8th and W 6th, then a straight crossing of the Ohio (bearing 204 degrees) on its own four-track bridge, centred on the KMZ line, 98 m east of the CS bridge at the Ohio bank and 28 m at the Kentucky bank. The line then runs into the CS corridor: the drawn tracks end 120 m into Ludlow, where the APEx centre line reaches the CS line, and south of that the KMZ line runs along the CS (CVG Express) line through Ludlow and Bromley, crossing it several times; whether the two lie side by side there or cross at separate levels is not set. A-D feed the CS pair, which merges with the CVG Express pair at the CS bridge; E-H feed the C&amp;O pair, which stays at -2 under W 6th and then climbs onto the TRIMET C&amp;O viaduct. A freight passing track bypasses the platforms on the west side, as in 1955.</p>",
    "The platform field is the one on the architects&rsquo; plot plan of 1 June 1931: straight parallel tracks, 3.97 m between the tracks of a pair, 11.68 m across an island (8.3 m platforms), seven concourse islands carrying APEx 1-14 from the building westward, and platform M beside the building: the 1933 mail platform, now CVG Express 15-16 (Ben). The plan&rsquo;s westmost through track is the freight passing track. The platforms keep the ruled length (the plan is cut off at its north end). South of the platforms six APEx tracks (Kentucky 4, Cardinal 2) follow Ben&rsquo;s General CUT Path KMZ: straight south, one curve of about 870 m radius between W 8th and W 6th, then the four Kentucky tracks cross the Ohio on their own bridge (bearing 204 degrees), 98 m east of the CS bridge at the Ohio bank and 28 m at the Kentucky bank; the Cardinal pair leaves east south of W 8th. The CVG Express leaves M on the east side and flies over the six APEx tracks just south of W 8th (6.8 m clear), then comes down onto the TRIMET CS viaduct and joins the intercity pair (A-D) at the CS bridge abutment. In Ludlow (Ben: 4 APEx tracks, at least 2 intercity, 6 to 8 in all) the two CS tracks carry the intercity trains and the CVG Express across the 1922 bridge and on at grade along the TRIMET CS line; the APEx runs 15.75 m east of them (centres), climbs 2% on a viaduct and crosses over the CS line about 1 km from the bank, then takes the KMZ line toward Erlanger. Six tracks are drawn: the CVG Express (6 an hour at the peak) and the intercity placeholder (4) make 10 an hour each way on the CS pair, about half of a double track at 3 minutes, so a spare pair is not needed yet; the band leaves room for one on the west side. The CVG Express leaves the CS line for CVG at Erlanger, as on the TRIMET line. E-H feed the C&amp;O pair, which stays at -2 under W 6th and then climbs onto the TRIMET C&amp;O viaduct.</p>")
rep("      <p>Union Terminal (15 October): the building, its train concourse, the plaza and the former Lincoln Park are traced from the architects&rsquo; plot plan of 1 June 1931 (HABS OH-705, sheet 1, Ben&rsquo;s scan) and fitted to the plan by five street crossings, Dalton, Denman and Freeman on Kenner and Hopkins (affine, within 0.5-1.1 m). The rotunda measures 180 ft across on the drawing. The plaza replaces the open east forecourt; the former Lincoln Park is drawn over the park&rsquo;s 1904 block.",
    "      <p>Union Terminal (15 October): the building and its train concourse come from the architects&rsquo; first-floor plan (Ben&rsquo;s image of the HABS floor plans), fitted to the 1931 plot plan by six building corners (similarity, within 0.6-2.4 m); the building takes in the curved bus and cab ramp arms, and the concourse is carried on west over the field to the west headhouse. The platform field, the plaza with its driveway, ramps, terrace and cascade, the drives and lawns of the former Lincoln Park and the park&rsquo;s walks come from the plot plan of 1 June 1931 (HABS OH-705, sheet 1, Ben&rsquo;s scan), fitted by five street crossings, Dalton, Denman and Freeman on Kenner and Hopkins (affine, within 0.5-1.1 m); the track centres were traced on the scan. The Union Terminal layers switch the building, concourse, roads and ramps, plaza and park, platform level and lower level on and off. The plaza replaces the open east forecourt; the former Lincoln Park is drawn over the park&rsquo;s 1904 block.")

rep("  kv('CS climb', fmt(T.cs_g, 2)", "  kv('Intercity pair (A-D) climb', fmt(T.cs_g, 2)")
rep("  kv('CS at Gest / 8th / 6th',", "  kv('Intercity pair at Gest / 8th / 6th',")
open(SP + 'deckpage/index.html', 'w').write(src)
print('ok v37', len(src))
