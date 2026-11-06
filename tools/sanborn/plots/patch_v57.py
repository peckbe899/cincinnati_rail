try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Version 57 (Ben, 18 October): the viaduct and bridge footprints are drawn under the Union Terminal layers (after the blocks), so the
# terminal, concourse and headhouse read on top of the station deck instead of being covered by it.
import sys
SP = _ws.DATA
src = open(SP + 'deckpage/index.html').read()
def rep(old, new):
    global src
    if src.count(old) != 1: sys.exit('count %d: %s' % (src.count(old), old[:80]))
    src = src.replace(old, new)
rep("  if (S.layers.via && S.struct) drawStruct(v);\n  if (S.layers.apt && S.airport) drawAirport(v);", "  if (S.layers.apt && S.airport) drawAirport(v);")
rep("  if (S.layers.blk) drawLocks(v, wx0, wy0, wx1, wy1);", "  if (S.layers.blk) drawLocks(v, wx0, wy0, wx1, wy1);\n  if (S.layers.via && S.struct) drawStruct(v);")
open(SP + 'deckpage/index.html', 'w').write(src); print('ok v57')
