import json, os, glob, re
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
U = D + 'unet_data/'
st = json.load(open(U + 'run_plates.json', encoding='utf8'))
print('plates in state', len(st))
from collections import Counter
print(Counter(v.get('state') for v in st.values()))
for n, v in st.items():
    if v.get('state') != 'done': print('FAILED', n, v.get('error'))
rows = []
for f in sorted(glob.glob(U + '*_blocks_ng.json')):
    b = json.load(open(f, encoding='utf8')); n = b['plate']
    src = D + f'cufp/{n}/source.json'
    s = json.load(open(src)) if os.path.exists(src) else None
    rows.append((n, b['blocks'], b['sides'], b['green'], b['share_on_printed_line_by_length'], st.get(n, {}).get('blocks', ''), 'pdf' if s else 'png', time_ := os.path.getmtime(f)))
import time
for r in rows: print(r[0], 'blocks', r[1], 'sides', r[2], 'green', r[3], 'share', r[4], r[6], time.strftime('%H:%M', time.localtime(r[7])), '|', r[5])
