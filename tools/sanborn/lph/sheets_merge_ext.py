try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
# Append the extension frames (lph/tf_ext.json) to deckpage/sheets.json from lph/sheets_ext.json (backup sheets_pre_ext.json).
import json, shutil
SP = _ws.DATA
X = set(json.load(open(SP + 'lph/tf_ext.json'))); S = json.load(open(SP + 'deckpage/sheets.json'))
shutil.copy(SP + 'deckpage/sheets.json', SP + 'deckpage/sheets_pre_ext.json')
have = {s['sheet'] for s in S}
add = [s for s in json.load(open(SP + 'lph/sheets_ext.json')) if s['sheet'] in X and s['sheet'] not in have]
S += add; json.dump(S, open(SP + 'deckpage/sheets.json', 'w')); print('added', len(add), sorted(s['sheet'] for s in add), {s['vol'] for s in add})
