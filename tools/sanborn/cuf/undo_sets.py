try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# put back what the plate installs (c70 ... c66, c38, c22) took out (newest first), drop their sets, and set the removal files aside
import json, os, sys
SP = _ws.DATA
BJ = json.load(open(SP + 'deckpage/basin.json'))
for SET, REM in tuple((f'c{n}', f'cufp/{n}/removed.json') for n in ('70', '69', '67', '68', '66')) + (('c38', 'cuf38/c38_removed.json'), ('c22', 'cuf/c22_removed.json')):   # newest first (plates 66-70 added 2026-10-21)
    if not os.path.exists(SP + REM): print('no', REM); continue
    R0 = json.load(open(SP + REM)); ids = {f['properties']['id'] for f in R0['features']}
    BJ['features'] = [f for f in BJ['features'] if f['properties'].get('set') != SET and f['properties'].get('id') not in ids] + R0['features']
    os.replace(SP + REM, SP + REM.replace('.json', '_prev.json')); print('undid', SET, len(R0['features']))
json.dump(BJ, open(SP + 'deckpage/basin.json', 'w'), separators=(',', ':'))
