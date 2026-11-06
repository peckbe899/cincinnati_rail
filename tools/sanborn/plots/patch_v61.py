try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 61 (Ben, 18 October): measured CVG contact stands, large (777/747/A350) and smaller (767/787/A330) widebody; T1B and T4 moved 90 m north.
import sys
SP = _ws.DATA
src = open(SP + 'deckpage/index.html').read()
def rep(old, new):
    global src
    if src.count(old) != 1: sys.exit('count %d: %s' % (src.count(old), old[:80]))
    src = src.replace(old, new)
rep("  if (v.s > 0.12) { ctx.strokeStyle = C.muted; ctx.lineWidth = 0.8; for (const f of AF) if (f.properties.layer === 'cvg_stand') { ctx.beginPath(); pathLine(f.geometry.coordinates[0]); ctx.closePath(); ctx.stroke(); } }",
    "  if (v.s > 0.12) { for (const f of AF) if (f.properties.layer === 'cvg_stand') { const big = f.properties.cls === 'L'; fillPoly(f.geometry, big ? C.warn : C.muted, big ? C.warn : C.muted, big ? 1.2 : 0.8, big ? 0.22 : 0.14); } }")
rep("    if (L === 'cvg_taxi') sub.textContent = 'Taxiway (designed): 25 m wide, parallels 190 m off the runways, 30\\u00b0 rapid exits, filleted junctions; drawing values';",
    "    if (L === 'cvg_taxi') sub.textContent = 'Taxiway (designed): 25 m wide, parallels 190 m off the runways (working value), 30\\u00b0 rapid exits, filleted junctions';")
rep("    if (L === 'cvg_apron') sub.textContent = 'Apron: widebody stands and the taxilanes behind them, cargo and maintenance aprons (designed; drawing values)';",
    "    if (L === 'cvg_apron') sub.textContent = 'Apron: contact stands and the taxilanes behind them (ICAO Annex 14 clearances), cargo and maintenance aprons';")
rep("    if (L === 'cvg_stand') sub.textContent = 'Widebody stand (Code E, 80 m by 70 m, nose-in), ' + p.terminal;",
    "    if (L === 'cvg_stand') { kv('Stand', fmt(p.w, 1) + ' m wide (span plus 7.5 m wingtip clearance), ' + fmt(p.d, 1) + ' m deep'); kv('Terminal', p.terminal); sub.textContent = p.kind + (p.cls === 'L' ? ': sized for the 747-8 span and 777-9 length, Code F taxilane behind' : ': sized for the A330-900 span and 787-10 length, Code E') + '; nose-in contact stand, measured along the terminal face'; }")
rep("    if (L === 'cvg_building') sub.textContent = 'CVG building (CVG Layout.kmz)';",
    "    if (L === 'cvg_building') sub.textContent = 'CVG building (CVG Layout.kmz)' + (p.moved ? '; moved ' + Math.abs(p.moved[1]) + ' m ' + (p.moved[1] > 0 ? 'north' : 'south') + ' (18 October) so both faces of the Terminal 2 gap take stands' : '');")
open(SP + 'deckpage/index.html', 'w').write(src); print('ok v61')
