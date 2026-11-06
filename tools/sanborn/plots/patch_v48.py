try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 48 (Ben, 17 October): a layer with the footprints of the rail viaducts and bridges (structures.json) and their widths.
# Chain: ... patch_v44.py && patch_v48.py
import sys
SP = _ws.DATA
src = open(SP + 'deckpage/index.html').read()
def rep(old, new, n=1):
    global src
    c = src.count(old)
    if c != n: sys.exit('count %d != %d for: %s' % (c, n, old[:110]))
    src = src.replace(old, new)
rep('<label><input type="checkbox" id="lApt" checked> CVG airport</label>',
    '<label><input type="checkbox" id="lApt" checked> CVG airport</label>\n        <label><input type="checkbox" id="lVia" checked> Viaducts and bridges</label>')
rep("apt: true }", "apt: true, via: true }")
rep("['lApt', 'apt']]) $(id)", "['lApt', 'apt'], ['lVia', 'via']]) $(id)")
rep("  try { S.airport = await fetch('airport.json')",
    "  try { S.struct = await fetch('structures.json').then(r => r.json()); for (const f of S.struct.features) f._bb = structBB(f.geometry); } catch (e) { S.struct = null; }\n  try { S.airport = await fetch('airport.json')")
rep("function featBB(f) {",
    """function structBB(g) { const b = [1e18, 1e18, -1e18, -1e18], go = c => { if (typeof c[0] === 'number') { b[0] = Math.min(b[0], c[0]); b[1] = Math.min(b[1], c[1]); b[2] = Math.max(b[2], c[0]); b[3] = Math.max(b[3], c[1]); } else c.forEach(go); }; go(g.coordinates); return b; }
function drawStruct(v) {   // rail viaduct and bridge footprints (structures.json): outer track centre + 4.2 m each side, drawing values
  const r0 = cv.getBoundingClientRect(), [qx0, qy1] = S2W(0, 0), [qx1, qy0] = S2W(r0.width, r0.height), vb = [qx0 - 50, qy0 - 50, qx1 + 50, qy1 + 50];
  const SF = S.struct.features.filter(f => bbHit(f._bb, vb)); ctx.save();
  for (const f of SF) { const p = f.properties; if (p.layer !== 'struct') continue;
    const col = p.kind === 'viaduct_existing' ? C.muted : p.kind === 'bridge' ? C.apex : C.warn;
    ctx.setLineDash(p.kind === 'trough' ? [6, 4] : []); fillPoly(f.geometry, col, null, 1, 0.13); fillPoly(f.geometry, null, col, Math.max(1.2, Math.min(2.4, 1.4 * v.s)), 0.95); }
  ctx.setLineDash([]);
  if (S.layers.lab && v.s >= 0.45) { ctx.font = '700 11px ' + css('--font-ui'); ctx.textBaseline = 'middle';
    for (const f of SF) { const p = f.properties; if (p.layer !== 'struct_w') continue; const [x, y] = W2S(f.geometry.coordinates[0], f.geometry.coordinates[1]), t = fmt(p.width_m, 1) + ' m', tw = ctx.measureText(t).width;
      ctx.globalAlpha = 0.9; ctx.fillStyle = C.panel; ctx.fillRect(x - tw / 2 - 3, y - 8, tw + 6, 16); ctx.globalAlpha = 1; ctx.fillStyle = C.warn; ctx.fillText(t, x - tw / 2, y); } }
  ctx.restore(); }
function featBB(f) {""")
rep("  if (S.layers.apt && S.airport) drawAirport(v);\n  // transit",
    "  if (S.layers.via && S.struct) drawStruct(v);\n  if (S.layers.apt && S.airport) drawAirport(v);\n  // transit")
rep("  if (!area && S.layers.apt && S.airport) for (const L of ['cvg_building',",
    "  if (!area && S.layers.via && S.struct) for (const f of S.struct.features) if (f.properties.layer === 'struct' && bbHit(f._bb, [p[0], p[1], p[0], p[1]]) && polysOf(f.geometry).some(q => inPoly(p, q))) { area = f; break; }\n  if (!area && S.layers.apt && S.airport) for (const L of ['cvg_building',")
rep("    if (L === 'cvg_building') sub.textContent = 'CVG building (CVG Layout.kmz)';",
    """    if (L === 'cvg_building') sub.textContent = 'CVG building (CVG Layout.kmz)';
    if (L === 'struct') { kv('Structure', { viaduct: 'Viaduct', station: 'Station deck on the viaduct', trough: 'Open trough between retaining walls', bridge: 'River bridge', viaduct_existing: 'Viaduct (existing line)' }[p.kind] || p.kind);
      if (p.w_min) kv('Width', p.w_min === p.w_max ? fmt(p.w_min, 1) + ' m' : fmt(p.w_min, 1) + ' to ' + fmt(p.w_max, 1) + ' m'); if (p.tracks) kv('Tracks', p.tracks); if (p.length_m) kv('Length', fmt(p.length_m) + ' m');
      sub.textContent = p.note + '. Footprint: outer track centre plus 4.2 m each side (overhead line masts on the deck edge, walkway, parapet; a drawing value), gaps under 6 m between tracks decked over, platforms of stations on the structure included.'; }""")
open(SP + 'deckpage/index.html', 'w').write(src)
print('ok v48', len(src))
