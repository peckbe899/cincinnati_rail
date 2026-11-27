"""sk_leak.py (skeptic): look for traces of sealed plates and of the H1-H4 windows in the dev, fixer, integrate and
step-4 folders (text files only: scripts, logs, json, txt, md, sh). File access times are not used.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/skeptic/scripts/sk_leak.py OUT.json

Searches every text file (< 30 MB) under text_fix/{dev_block,dev_ditto,fix_block_a,fix_block_b,fix_ditto,integrate,step4}
(git_status*.txt skipped: they list every untracked file of the repo) for:
  paths    sealed scan / paper mask / bins / street map paths (22-N.jpg, cufp/N/, unet_data/N_, streetmap/N)
  field    a json/py plate field or argument equal to a sealed id ("plate": "38", plate='38', N == '38')
  list     a quoted sealed id inside a list or set literal ('38', ...)
  cmd      a command line running a finder or fixer on a sealed id (finder3.py 38, blockfix.py 38 ...)
  sealedok the --sealed-ok flag, or code that empties a SEALED guard
  win      the window coordinates of any sealed crop (x0,y0 and x1,y1 pairs with any separator) and of H1-H4
  heldout  a path into text_v1/heldout*, truth-check/heldout_fixed, gate/pics, skeptic/pics, sealed_* folders
Every hit is kept with file, line and text, so it can be judged.
"""
import json, os, re, sys
sys.dont_write_bytecode = True
ROOT = 'bench_2026-11-26/text_fix'
DIRS = ['dev_block', 'dev_ditto', 'fix_block_a', 'fix_block_b', 'fix_ditto', 'integrate', 'step4']
EXT = ('.py', '.sh', '.json', '.txt', '.log', '.md', '.csv', '.out', '.sha1')
IDS = ['6', '9', '52', '56', '58', '63', '35', '38', '41', '66', '71', '76', '84', '88', '46', '92']
I = '(?:' + '|'.join(sorted(IDS, key=len, reverse=True)) + ')'
crops = json.load(open(f'{ROOT}/sealed_final/crops.json'))
H = {'H1': [5640, 3950, 7140, 4950], 'H2': [880, 2100, 2380, 3100], 'H3': [7040, 4560, 8540, 5560], 'H4': [7190, 3950, 8690, 4950]}
wins = {k: c['win'] for k, c in crops.items()}; wins.update(H)
# scope boxes too (targeted crops)
for k, c in crops.items():
    for j, s in enumerate(c.get('scope', [])): wins[f'{k}/scope{j}'] = s
SEP = r'[\s,;:\[\]\(\)x_-]{1,4}'
win_pats = []
for k, w in wins.items():
    a = rf'(?<!\d){w[0]}{SEP}{w[1]}(?!\d)'; b = rf'(?<!\d){w[2]}{SEP}{w[3]}(?!\d)'
    win_pats.append((k, re.compile(a), re.compile(b)))
P = {
    'paths': re.compile(rf'(22-{I}\.jpg|cufp[/\\]+{I}[/\\]|unet_data[/\\]+{I}_|streetmap[/\\]+{I}[_.\\/]|N_new[/\\]+{I}\b)'),
    'field': re.compile(rf'''(["']plate["']\s*[:=]\s*["']?{I}["']?(?![0-9A-Za-z])|\bplate\s*=\s*["']{I}["']|\bN\s*==\s*["']{I}["'])'''),
    'list': re.compile(rf'''[\[\({{,]\s*["']{I}["']\s*(?=[,\]\)}}])'''),
    'cmd': re.compile(rf'(finder[234]?\.py|blockfix(?:_[ab])?\.py|dittofix\.py|ink_bins\w*\.py|step4\w*\.py)\s+{I}(?![0-9A-Za-z])'),
    'sealedok': re.compile(r'(--sealed-ok|sealed_ok\s*=\s*True|SEALED\s*=\s*set\(\))'),
    'heldout': re.compile(r'(text_v1[/\\]+heldout|heldout_fixed|gate[/\\]+pics|skeptic[/\\]+pics|text_fix[/\\]+sealed_(?:A|B|final|check)|\bsealed_final\b|\bsealed_[AB]\b)'),
}
hits = []
nfiles = 0
for d in DIRS:
    for dp, dn, fn in os.walk(f'{ROOT}/{d}'):
        for f in fn:
            if not f.endswith(EXT) or f.startswith('git_status'): continue
            p = os.path.join(dp, f).replace('\\', '/')
            if os.path.getsize(p) > 30e6: continue
            nfiles += 1
            try: txt = open(p, encoding='utf8', errors='replace').read()
            except Exception: continue
            lines = txt.split('\n')
            for i, ln in enumerate(lines, 1):
                if len(ln) > 4000: segs = [ln[j:j + 4000] for j in range(0, len(ln), 3500)]
                else: segs = [ln]
                for s in segs:
                    for k, rx in P.items():
                        for m in rx.finditer(s):
                            hits.append(dict(kind=k, file=p, line=i, match=m.group(0), text=s[max(0, m.start() - 100):m.end() + 100]))
                    for k, ra, rb in win_pats:
                        ma = ra.search(s)
                        if ma and rb.search(s):
                            hits.append(dict(kind='win', win=k, file=p, line=i, match=ma.group(0), text=s[max(0, ma.start() - 100):ma.end() + 120]))
by = {}
for h in hits:
    key = (h['kind'], h['file'].split('/')[2])
    by[str(key)] = by.get(str(key), 0) + 1
json.dump(dict(files_searched=nfiles, counts=by, hits=hits), open(sys.argv[1], 'w', encoding='utf8'), indent=1)
print('files searched', nfiles)
for k, v in sorted(by.items()): print(k, v)
