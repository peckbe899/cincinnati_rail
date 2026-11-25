"""Build the offline street-name list for the name checks, from what the repo already holds (read only).

Sources (all under data/sanborn/):
  1922 atlas reads   sbg/picks22/*.json, picks22_reads/22-*/[AB]_*.json, picks22_complete/reads/*.json ('printed'),
                     streetmap/22-44.json line names, picks22_guided/*/streets_marked.json / streets_added.json
  other atlas years  sbg/picks/*.json (1904 vol. 3/5/6 sheets), sbg/picks12/*.json (1912), basin/named_*.geojson (1904 West End
                     and Basin), lph/lph_streets*.json (1904 Lower Price Hill)
  today (OSM)        basin/osm_basin.geojson, lph/osm_{north,east,west,norwood}.geojson
  renames/aliases    tools/sanborn/cufp/fit.py ALIAS (read as text), cufp/config.json per-plate alias/merge,
                     sbg/osmchk/pick_fix.json alias, picks22_reads/22-*/names_resolved.json renames
Writes data/name_list.json: one entry per normalised key with its spellings, sources, 1922 plates, and aliases.
usage: python -B build_namelist.py
"""
import json, os, re, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.dirname(HERE)
SB = os.path.normpath(os.path.join(BASE, '..', '..', '..')) + os.sep
REPO = os.path.normpath(os.path.join(SB, '..', '..')) + os.sep

ORD = {'first': '1st', 'second': '2nd', 'third': '3rd', 'fourth': '4th', 'fifth': '5th', 'sixth': '6th', 'seventh': '7th', 'eighth': '8th',
       'ninth': '9th', 'tenth': '10th', 'eleventh': '11th', 'twelfth': '12th', 'thirteenth': '13th', 'fourteenth': '14th', 'fifteenth': '15th'}
SUF = {'st': 'street', 'st.': 'street', 'str': 'street', 'street': 'street', 'ave': 'avenue', 'ave.': 'avenue', 'av': 'avenue', 'av.': 'avenue',
       'avenue': 'avenue', 'pl': 'place', 'pl.': 'place', 'place': 'place', 'rd': 'road', 'rd.': 'road', 'road': 'road', 'ter': 'terrace',
       'terrace': 'terrace', 'ct': 'court', 'court': 'court', 'al': 'alley', 'alley': 'alley', 'la': 'lane', 'ln': 'lane', 'lane': 'lane',
       'pike': 'pike', 'blvd': 'boulevard', 'boulevard': 'boulevard', 'way': 'way', 'row': 'row', 'dr': 'drive', 'drive': 'drive', 'sq': 'square'}
DIR = {'w': 'west', 'w.': 'west', 'west': 'west', 'e': 'east', 'e.': 'east', 'east': 'east', 'n': 'north', 'n.': 'north', 'north': 'north',
       's': 'south', 's.': 'south', 'south': 'south'}
SUFFIXES = set(SUF.values())


def norm(name):
    """'W. SIXTH ST.' -> 'west 6th street'; parenthesised notes dropped"""
    n = re.sub(r'\(.*?\)', ' ', name or '').strip().lower()
    n = n.replace('mt.', 'mount').replace('mt ', 'mount ').replace('&', ' and ')
    toks = [t for t in re.split(r'[\s,]+', n) if t]
    out = []
    for i, t in enumerate(toks):
        t2 = t.strip('.')
        if t2 in ORD:
            out.append(ORD[t2]); continue
        if i == 0 and t in DIR:
            out.append(DIR[t]); continue
        if t2 == 'st' and i < len(toks) - 1:        # 'St. Lawrence' = 'Saint Lawrence' (OSM spells Saint out)
            out.append('saint'); continue
        if i == len(toks) - 1 and (t in SUF or t2 in SUF):
            out.append(SUF.get(t, SUF.get(t2))); continue
        out.append(t2)
    return ' '.join(out)


def base(key):
    """the name without a direction word or a suffix: 'west 6th street' -> '6th'"""
    w = key.split()
    if w and w[0] in ('west', 'east', 'north', 'south') and len(w) > 1:
        w = w[1:]
    if len(w) > 1 and w[-1] in SUFFIXES:
        w = w[:-1]
    return ' '.join(w)


BAD = {'', '?', 'alley', 'street', 'avenue', 'ave avenue', 'unnamed', 'unnamed alley', 'private alley', 'private way'}


def main():
    E = collections.defaultdict(lambda: dict(spellings=collections.Counter(), sources=collections.Counter(), plates22=set()))

    def add(name, src, plate=None):
        if not name or name.strip() in ('?',):
            return
        k = norm(name)
        if k in BAD or len(base(k)) < 2 or base(k) in ('?', 'alley'):
            return
        e = E[k]; e['spellings'][re.sub(r'\s*\(.*?\)', '', name).strip()] += 1; e['sources'][src] += 1
        if plate:
            e['plates22'].add(plate)

    # 1922 reads
    for f in glob.glob(SB + 'sbg/picks22/*.json'):
        d = json.load(open(f, encoding='utf8'))
        pl = re.sub(r'^22-', '', str(d.get('sheet', ''))); pl = re.sub(r'([LR]|_\d+)$', '', pl)
        for p in d.get('intersections', []):
            add(p.get('a'), '1922 sbg/picks22', pl); add(p.get('b'), '1922 sbg/picks22', pl)
        for w in d.get('widths', []) or []:
            add(w.get('street'), '1922 sbg/picks22', pl)
    for f in glob.glob(SB + 'picks22_reads/22-*/[AB]_*.json'):
        d = json.load(open(f, encoding='utf8')); pl = d['sheet'].replace('22-', '')
        for p in d.get('intersections', []):
            add(p.get('a'), '1922 picks22_reads', pl); add(p.get('b'), '1922 picks22_reads', pl)
    for f in glob.glob(SB + 'picks22_complete/reads/*.json'):
        for r in json.load(open(f, encoding='utf8')):
            pl = str(r.get('job', '')).split('_')[0]
            for n in r.get('printed', []) or []:
                add(n, '1922 picks22_complete printed', pl)
    for l in json.load(open(SB + 'streetmap/22-44.json', encoding='utf8'))['lines']:
        add(l.get('name'), '1922 Ben streetmap 44', '44')
    for f in glob.glob(SB + 'picks22_guided/22-*/streets_marked.json') + glob.glob(SB + 'picks22_guided/22-*/streets_added.json'):
        pl = f.replace('\\', '/').split('/')[-2].replace('22-', '')
        for s in json.load(open(f, encoding='utf8')):
            add(s.get('name'), '1922 streets_marked', pl)
    # other atlas years
    for f in glob.glob(SB + 'sbg/picks/*.json'):
        d = json.load(open(f, encoding='utf8'))
        for p in d.get('intersections', []):
            add(p.get('a'), '1904 sbg/picks'); add(p.get('b'), '1904 sbg/picks')
    for f in glob.glob(SB + 'sbg/picks12/*.json'):
        d = json.load(open(f, encoding='utf8'))
        for p in (d.get('intersections', []) if isinstance(d, dict) else []):
            add(p.get('a'), '1912 sbg/picks12'); add(p.get('b'), '1912 sbg/picks12')
    for f in ('basin/named_we.geojson', 'basin/named_east.geojson'):
        for ft in json.load(open(SB + f, encoding='utf8'))['features']:
            if ft['properties'].get('kind') != 'drop':
                add(ft['properties'].get('name'), '1904 basin named')
    for f in glob.glob(SB + 'lph/lph_streets*.json'):
        d = json.load(open(f, encoding='utf8'))
        for ft in (d['features'] if isinstance(d, dict) else d):
            add((ft.get('properties') or ft).get('name'), '1904 lph')
    # today
    for f in ('basin/osm_basin.geojson', 'lph/osm_north.geojson', 'lph/osm_east.geojson', 'lph/osm_west.geojson', 'lph/osm_norwood.geojson'):
        for ft in json.load(open(SB + f, encoding='utf8'))['features']:
            add(ft['properties'].get('name'), 'today OSM')
    # aliases
    AL = []
    src = open(REPO + 'tools/sanborn/cufp/fit.py', encoding='utf8').read()
    m = re.search(r"ALIAS = \{key\(a_\): key\(b_\) for a_, b_ in (\{.*?\})\.items\(\)\}", src, re.S)
    if m:
        for a, b in re.findall(r"'([^']+)':\s*'([^']+)'", m.group(1)):
            AL.append(dict(old=a, now=b, src='tools/sanborn/cufp/fit.py ALIAS'))
    cfg = json.load(open(SB + 'cufp/config.json', encoding='utf8'))
    for pl, c in cfg.items():
        for a, b in (c.get('alias') or {}).items():
            AL.append(dict(old=a, now=b, src=f'cufp/config.json {pl} alias'))
        for a, b in (c.get('merge') or {}).items():
            AL.append(dict(old=a, now=b, src=f'cufp/config.json {pl} merge'))
    for a in json.load(open(SB + 'sbg/osmchk/pick_fix.json', encoding='utf8')).get('alias', []):
        AL.append(dict(old=a['from'], now=a['to'], src='sbg/osmchk/pick_fix.json alias'))
    for f in glob.glob(SB + 'picks22_reads/22-*/names_resolved.json'):
        for r in json.load(open(f, encoding='utf8')).get('renames', []):
            AL.append(dict(old=r['frm'], now=r['to'], src=f.replace('\\', '/').split('data/sanborn/')[-1], why=r.get('why', '')))
    seen = set(); AL2 = []
    for a in AL:
        k = (norm(a['old']), norm(a['now']))
        if k not in seen and k[0] != k[1]:
            seen.add(k); AL2.append(dict(a, old_key=k[0], now_key=k[1]))
    out = dict(about=__doc__.strip().splitlines()[0], made_by='code/build_namelist.py', n_keys=len(E),
               aliases=AL2,
               names={k: dict(spellings=dict(v['spellings'].most_common(5)), sources=dict(v['sources']), plates22=sorted(v['plates22']), base=base(k))
                      for k, v in sorted(E.items())})
    json.dump(out, open(os.path.join(BASE, 'data', 'name_list.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
    S = collections.Counter()
    for k, v in E.items():
        grp = tuple(sorted({s.split(' ')[0] for s in v['sources']}))
        S[grp] += 1
    n22 = sum(1 for v in E.values() if any(s.startswith('1922') for s in v['sources']))
    nto = sum(1 for v in E.values() if 'today OSM' in v['sources'])
    both = sum(1 for v in E.values() if 'today OSM' in v['sources'] and any(s.startswith('1922') for s in v['sources']))
    print(f'name keys {len(E)}; with a 1922 read {n22}; in OSM today {nto}; both {both}; aliases {len(AL2)}')
    for g, c in S.most_common():
        print('  ', g, c)
    pls = collections.Counter(p for v in E.values() for p in v['plates22'])
    print('  1922 plates with names:', len(pls))


if __name__ == '__main__':
    main()
