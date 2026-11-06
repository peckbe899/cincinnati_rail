try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 63 (Ben, 18 October): CVG landside court inside the T1B/T4 U kept clear; T2 as long as T3, T3 a plain bar, both carried east;
# T1A south into the parking area; stands tagged with their airline.
import sys
SP = _ws.DATA
src = open(SP + 'deckpage/index.html').read()
def rep(old, new):
    global src
    if src.count(old) != 1: sys.exit('count %d: %s' % (src.count(old), old[:80]))
    src = src.replace(old, new)
rep("kv('Terminal', p.terminal); sub.textContent = p.kind", "kv('Terminal', p.terminal); if (p.airline) kv('Airline', p.airline); sub.textContent = p.kind")
rep("    if (L === 'cvg_building') sub.textContent = 'CVG building (CVG Layout.kmz)' + (p.moved ?",
    "    if (L === 'cvg_building') sub.textContent = 'CVG building (CVG Layout.kmz)' + (p.reshaped ? '; reshaped 18 October (T1A carried south into the parking area; T2 as long as T3; T3 a plain bar; both carried east to taxiway T)' : '') + (p.moved ?")
open(SP + 'deckpage/index.html', 'w').write(src); print('ok v63')
