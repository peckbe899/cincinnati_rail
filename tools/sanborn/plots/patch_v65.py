try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 65 (Ben, 18 October): realistic stand standards (PANYNJ / FAA / ICAO), T4 small widebodies, tunnel notches, CVG grounds and landside.
import sys
SP = _ws.DATA
src = open(SP + 'deckpage/index.html').read()
def rep(old, new):
    global src
    if src.count(old) != 1: sys.exit('count %d: %s' % (src.count(old), old[:80]))
    src = src.replace(old, new)
rep("const big = f.properties.cls === 'L'; fillPoly(f.geometry, big ? C.warn : C.muted, big ? C.warn : C.muted, big ? 1.2 : 0.8, big ? 0.22 : 0.14);",
    "const big = f.properties.cls === 'L', sm = f.properties.cls === 'M'; fillPoly(f.geometry, big ? C.warn : sm ? C.rer : C.muted, big ? C.warn : sm ? C.rer : C.muted, big ? 1.2 : 0.8, big ? 0.22 : 0.14);")
rep("kv('Stand', fmt(p.w, 1) + ' m wide (span plus 7.5 m wingtip clearance), ' + fmt(p.d, 1) + ' m deep');",
    "kv('Stand', fmt(p.w, 1) + ' m wide (span plus 7.5 m / 25 ft wingtip clearance); aircraft ' + fmt(p.d, 1) + ' m long, nose 11.3 m (37 ft) off the facade, 1.5 m tail clearance and a 7.6 m tail-of-stand road behind');")
rep("(p.cls === 'L' ? ': sized for the 747-8 span and 777-9 length, Code F taxilane behind' : ': sized for the A330-900 span and 787-10 length, Code E')",
    "(p.cls === 'L' ? ': sized for the 747-8 span and 777-9 length; ADG VI taxilane behind (51 m to objects)' : p.cls === 'M' ? ': sized for the 787-8 (767-200 fits); ADG V taxilane' : ': sized for the A330-900 span and 787-10 length; ADG V taxilane (42 m to objects)') + '; dual taxilanes between facing rows'")
open(SP + 'deckpage/index.html', 'w').write(src); print('ok v65')
