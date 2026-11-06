try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 59 (Ben, 17 October): switches on the APEx (marker kind 'switch'), drawn as small ticks when zoomed in; click info for switches.
import sys
SP = _ws.DATA
src = open(SP + 'deckpage/index.html').read()
def rep(old, new):
    global src
    if src.count(old) != 1: sys.exit('count %d: %s' % (src.count(old), old[:80]))
    src = src.replace(old, new)
rep("""    const [x, y] = W2S(f.geometry.coordinates[0], f.geometry.coordinates[1]);
    if (p.layer === 'marker') {""",
"""    const [x, y] = W2S(f.geometry.coordinates[0], f.geometry.coordinates[1]);
    if (p.layer === 'marker' && p.kind === 'switch') { if (v.s < 0.45) continue; const r = Math.max(2.5, Math.min(5, 2.2 * v.s)); ctx.fillStyle = p.num >= 40 ? C.warn : C.apex; ctx.strokeStyle = C.panel; ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.moveTo(x, y - r); ctx.lineTo(x + r, y); ctx.lineTo(x, y + r); ctx.lineTo(x - r, y); ctx.closePath(); ctx.fill(); ctx.stroke(); continue; }
    if (p.layer === 'marker') {""")
open(SP + 'deckpage/index.html', 'w').write(src); print('ok v59')
# CVG taxiways and aprons (airport.json layer cvg_taxi), under the runways
src = open(SP + 'deckpage/index.html').read()
rep("  for (const f of AF) if (f.properties.layer === 'cvg_runway') fillPoly(f.geometry, C['apex-plat'], C.ink, 0.8, 0.95);",
    "  for (const f of AF) if (f.properties.layer === 'cvg_taxi') { if (f.properties.ext) ctx.setLineDash([5, 3]); fillPoly(f.geometry, C.muted, C.muted, 0.6, 0.45); ctx.setLineDash([]); }\n  for (const f of AF) if (f.properties.layer === 'cvg_runway') fillPoly(f.geometry, C['apex-plat'], C.ink, 0.8, 0.95);")
rep("for (const L of ['cvg_building', 'cvg_runway', 'cvg_area'])", "for (const L of ['cvg_building', 'cvg_runway', 'cvg_taxi', 'cvg_area'])")
rep("    if (L === 'cvg_building') sub.textContent = 'CVG building (CVG Layout.kmz)';",
    "    if (L === 'cvg_building') sub.textContent = 'CVG building (CVG Layout.kmz)';\n    if (L === 'cvg_taxi') sub.textContent = p.ext ? 'Taxiway carried along the lengthened runway at the diagram\\u2019s parallel-taxiway offset (drawing value)' : 'Taxiways and aprons, from the FAA airport diagram (January 2020, Ben\\u2019s CVG_Layout.tif)';")
open(SP + 'deckpage/index.html', 'w').write(src); print('ok v59b')
src = open(SP + 'deckpage/index.html').read()
rep("for (const f of AF) { const p = f.properties; if (p.layer === 'cvg_runway_cl') continue;", "for (const f of AF) { const p = f.properties; if (p.layer === 'cvg_runway_cl' || p.layer === 'cvg_taxi') continue;")
open(SP + 'deckpage/index.html', 'w').write(src)
