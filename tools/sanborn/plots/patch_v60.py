try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 60 (Ben, 18 October): the designed CVG airside: aprons, stands, smooth taxiways with centre lines.
import sys
SP = _ws.DATA
src = open(SP + 'deckpage/index.html').read()
def rep(old, new):
    global src
    if src.count(old) != 1: sys.exit('count %d: %s' % (src.count(old), old[:80]))
    src = src.replace(old, new)
rep("  for (const f of AF) if (f.properties.layer === 'cvg_taxi') { if (f.properties.ext) ctx.setLineDash([5, 3]); fillPoly(f.geometry, C.muted, C.muted, 0.6, 0.45); ctx.setLineDash([]); }",
    """  for (const f of AF) if (f.properties.layer === 'cvg_apron') fillPoly(f.geometry, C.muted, null, 0, 0.28);
  for (const f of AF) if (f.properties.layer === 'cvg_taxi') fillPoly(f.geometry, C.muted, null, 0, 0.55);
  if (v.s > 0.12) { ctx.strokeStyle = C.muted; ctx.lineWidth = 0.8; for (const f of AF) if (f.properties.layer === 'cvg_stand') { ctx.beginPath(); pathLine(f.geometry.coordinates[0]); ctx.closePath(); ctx.stroke(); } }
  if (v.s > 0.08) { ctx.strokeStyle = C.rer; ctx.globalAlpha = 0.8; ctx.lineWidth = 1; for (const f of AF) if (f.properties.layer === 'cvg_taxi_cl') { ctx.beginPath(); pathLine(f.geometry.coordinates); ctx.stroke(); } ctx.globalAlpha = 1; }""")
rep("for (const L of ['cvg_building', 'cvg_runway', 'cvg_taxi', 'cvg_area'])", "for (const L of ['cvg_building', 'cvg_runway', 'cvg_stand', 'cvg_taxi', 'cvg_apron', 'cvg_area'])")
rep("    if (L === 'cvg_taxi') sub.textContent = p.ext ? 'Taxiway carried along the lengthened runway at the diagram\\u2019s parallel-taxiway offset (drawing value)' : 'Taxiways and aprons, from the FAA airport diagram (January 2020, Ben\\u2019s CVG_Layout.tif)';",
    "    if (L === 'cvg_taxi') sub.textContent = 'Taxiway (designed): 25 m wide, parallels 190 m off the runways, 30\\u00b0 rapid exits, filleted junctions; drawing values';\n    if (L === 'cvg_apron') sub.textContent = 'Apron: widebody stands and the taxilanes behind them, cargo and maintenance aprons (designed; drawing values)';\n    if (L === 'cvg_stand') sub.textContent = 'Widebody stand (Code E, 80 m by 70 m, nose-in), ' + p.terminal;")
rep("if (p.layer === 'cvg_runway_cl' || p.layer === 'cvg_taxi') continue;", "if (p.layer === 'cvg_runway_cl' || /^cvg_(taxi|taxi_cl|apron|stand)$/.test(p.layer)) continue;")
open(SP + 'deckpage/index.html', 'w').write(src); print('ok v60')
