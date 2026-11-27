"""Split a hand-input source file with '=== ID' sections into truth/annot/ID.txt (only sections that changed).
python -B split_annot.py SRC"""
import os, sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import INV
src = open(sys.argv[1], encoding='utf8').read().split('\n')
cur, buf, secs = None, [], {}
for ln in src:
    if ln.startswith('=== '):
        if cur: secs[cur] = buf
        cur, buf = ln[4:].strip(), []
    else: buf.append(ln)
if cur: secs[cur] = buf
for k, v in secs.items():
    p = os.path.join(INV, 'truth', 'annot', f'{k}.txt'); t = '\n'.join(v).rstrip('\n') + '\n'
    if not os.path.exists(p) or open(p, encoding='utf8').read() != t:
        open(p, 'w', encoding='utf8', newline='\n').write(t); print('wrote', k)
