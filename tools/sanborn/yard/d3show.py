try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, sys
S = _ws.DATA
d = json.load(open(S + 'yard/d3.json')); P = json.load(open(S + 'yard/part1.json'))
F = [f for f in P['features'] if f['properties']['layer'] in ('yard_limit', 'ud_box', 'ud_line')]
col = {'track': 'yard', 'stub': 'stub', 'throat': 'yard'}
for y, k, c in d['SEG']: F.append({'type': 'Feature', 'properties': {'layer': 'yard_track', 'kind': 'yard' if k != 'stub' else 'stub'}, 'geometry': {'type': 'LineString', 'coordinates': c}})
for k in ('hump', 'ramp', 'zlead', 'nelead'): F.append({'type': 'Feature', 'properties': {'layer': 'yard_lead'}, 'geometry': {'type': 'LineString', 'coordinates': d[k]}})
json.dump({'type': 'FeatureCollection', 'features': F}, open(S + 'yard/d3show.json', 'w'))
