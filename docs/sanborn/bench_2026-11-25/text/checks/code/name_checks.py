"""Street-name checks by code, tested on the street-name reads the repo already holds.

Test data: the crossing reads of picks22_reads/22-{25,28,39,40,43,44,45,80}/[AB]_*.json (two independent readers per
strip, full-plate pixel coordinates; these readers often wrote today's form of a name, e.g. 'West 8th Street').
Every plate here has a cufp world model, so reads can be carried to the world and onto the adjoining plates.

  T1 list coverage    leave-one-plate-out: is each name read on a plate in the list built WITHOUT that plate's reads?
  T2 noisy matching   the as-printed capitals of each name, with 1-2 confusable letters swapped (O/D/Q, I/L/1, S/5 ...)
                      or one letter dropped, matched to (a) the whole list, (b) the plate-local list (OSM names inside the
                      plate's box + 300 m, 1922 reads from the OTHER plates in that box, aliases)
  T3 across the edge  a crossing read on two adjoining plates (within 30 m in the world) must carry the same two names
  T4 today's name     a read name must match an OSM way of that name (or its known alias) within 40 m of the crossing
  T5 sheet numbers    the adjoining sheet numbers printed in a plate's margins must be the plates the world models put there
usage: python -B name_checks.py     (prints the tables, writes out/names.json)
"""
import json, os, re, glob, random, collections
import numpy as np
from shapely.geometry import shape, Point, box
from shapely.strtree import STRtree
HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.dirname(HERE)
import sys; sys.path.insert(0, HERE)
import platemap
from build_namelist import norm, base
SB = os.path.normpath(os.path.join(BASE, '..', '..', '..')) + os.sep
PLATES = ['25', '28', '39', '40', '43', '44', '45', '80']
random.seed(7)

CAPS_CONF = ['ODQ0CG', 'IL1JT', 'EFB', 'S58B', 'MNHW', 'UV', 'PRB', 'KX', 'Z2', 'A4']
CC = {}
for grp in CAPS_CONF:
    for a in grp:
        for b in grp:
            if a != b:
                CC.setdefault(a, set()).add(b)


def wdist(a, b):
    """edit distance with cheap swaps between letters the print makes alike (0.4), spaces and dots cheap (0.3)"""
    a = a.upper(); b = b.upper()
    n, m = len(a), len(b)
    prev = [0.0] * (m + 1)
    for j in range(1, m + 1):
        prev[j] = prev[j - 1] + (0.3 if b[j - 1] in ' .' else 1.0)
    for i in range(1, n + 1):
        ca = a[i - 1]; cur = [prev[0] + (0.3 if ca in ' .' else 1.0)] + [0.0] * m
        alike = CC.get(ca, ())
        for j in range(1, m + 1):
            cb = b[j - 1]
            sub = 0.0 if ca == cb else (0.4 if cb in alike else 1.0)
            cur[j] = min(prev[j - 1] + sub, prev[j] + (0.3 if ca in ' .' else 1.0), cur[j - 1] + (0.3 if cb in ' .' else 1.0))
        prev = cur
    return prev[m]


def match(read, cands):
    """best three candidate base names for a read (as printed); score = distance / length. Candidates whose length
    differs by more than 3 letters are not scored (they cannot come within 0.25 per letter for these lengths)"""
    L = len(read)
    sc = sorted((wdist(read, c) / max(len(c), 1), c) for c in cands if abs(len(c) - L) <= 3)
    return sc[:3] if sc else [(9.0, '')]


def load_reads():
    R = []
    for p in PLATES:
        for f in sorted(glob.glob(f'{SB}picks22_reads/22-{p}/[AB]_*.json')):
            d = json.load(open(f, encoding='utf8'))
            for c in d.get('intersections', []):
                R.append(dict(plate=p, reader=os.path.basename(f)[0], part=d.get('part'), a=c['a'], b=c['b'], x=c['x'], y=c['y']))
    return R


def main():
    NL = json.load(open(os.path.join(BASE, 'data', 'name_list.json'), encoding='utf8'))
    alias = collections.defaultdict(set)
    for a in NL['aliases']:
        alias[base(a['old_key'])].add(base(a['now_key'])); alias[base(a['now_key'])].add(base(a['old_key']))
    R = load_reads()
    for r in R:
        r['E'], r['N'] = platemap.px_to_world(r['plate'], r['x'], r['y'])
    rep = {}
    print(f'reads: {len(R)} crossings on plates {PLATES}')

    # ---- T1 coverage, leave one plate out
    print('\n== T1 list coverage, leave one plate out')
    T1 = collections.Counter()
    rows = []
    for p in PLATES:
        # the list without this plate's 1922 reads (names seen only on p in the 1922 sources are dropped)
        def in_list(k):
            v = NL['names'].get(k)
            if v is None:
                return False
            other = [q for q in v['plates22'] if q != p]
            non1922 = [s for s in v['sources'] if not s.startswith('1922')]
            return bool(other or non1922)
        bases_wo = {}
        for k, v in NL['names'].items():
            if in_list(k):
                bases_wo.setdefault(v['base'], set()).add(k)
        names = {n for r in R if r['plate'] == p for n in (r['a'], r['b'])}
        for n in sorted(names):
            k = norm(n)
            if k in ('', '?') or base(k) in ('', '?', 'alley'):
                continue
            if in_list(k):
                out = 'exact'
            elif base(k) in bases_wo or any(a in bases_wo for a in alias.get(base(k), ())):
                out = 'same name, other suffix/direction or alias'
            else:
                bm = min((wdist(base(k), b) / max(len(b), 1), b) for b in bases_wo)
                out = 'close (spelling)' if bm[0] <= 0.15 else 'not found'
            T1[out] += 1; rows.append(dict(plate=p, name=n, outcome=out))
    tot = sum(T1.values())
    for k, v in T1.most_common():
        print(f'  {k:45s} {v:4d} ({v / tot:.1%})')
    print('  not found:', sorted({r['name'] for r in rows if r['outcome'] == 'not found'})[:40])
    rep['T1'] = dict(counts=dict(T1), rows=rows)

    # ---- OSM for the local lists and T4
    osm = []
    for f in ('basin/osm_basin.geojson', 'lph/osm_north.geojson', 'lph/osm_east.geojson', 'lph/osm_west.geojson', 'lph/osm_norwood.geojson'):
        for ft in json.load(open(SB + f, encoding='utf8'))['features']:
            nm = ft['properties'].get('name')
            if nm and ft['geometry']['type'] in ('LineString', 'MultiLineString'):
                osm.append((shape(ft['geometry']), nm))
    tree = STRtree([g for g, _ in osm])

    def osm_near(E, N, r):
        idx = tree.query(Point(E, N).buffer(r))
        return {base(norm(osm[i][1])) for i in idx if osm[i][0].distance(Point(E, N)) <= r}

    # ---- T2 noisy matching
    print('\n== T2 noisy reads of the printed capitals, matched to the whole list and to the plate-local list')
    all_bases = sorted({v['base'] for v in NL['names'].values()})
    T2 = []
    for p in PLATES:
        Rp = [r for r in R if r['plate'] == p]
        E = [r['E'] for r in Rp]; N = [r['N'] for r in Rp]
        bx = box(min(E) - 300, min(N) - 300, max(E) + 300, max(N) + 300)
        local = {base(norm(osm[i][1])) for i in tree.query(bx)}
        local |= {base(norm(n)) for r in R if r['plate'] != p and bx.contains(Point(r['E'], r['N'])) for n in (r['a'], r['b'])}
        local |= {a for b in list(local) for a in alias.get(b, ())}
        local = {b for b in local if b and b not in ('?', 'alley')}
        truths = sorted({base(norm(n)) for r in Rp for n in (r['a'], r['b'])} - {'', '?', 'alley'})
        for t in truths:
            printed = t.upper()
            for kind in ('1 swap', '2 swaps', '1 dropped'):
                for _ in range(1):
                    s = list(printed)
                    pos = [i for i, ch in enumerate(s) if CC.get(ch)]
                    if kind == '1 dropped':
                        i = random.randrange(len(s)); del s[i]
                    else:
                        k = 1 if kind == '1 swap' else 2
                        if len(pos) < k:
                            continue
                        for i in random.sample(pos, k):
                            s[i] = random.choice(sorted(CC.get(s[i], {s[i]})))
                    noisy = ''.join(s)
                    for lst_name, lst in (('whole list', all_bases), ('plate-local', sorted(local))):
                        m = match(noisy, lst)
                        top = m[0][1]; margin = (m[1][0] - m[0][0]) if len(m) > 1 else 9
                        T2.append(dict(plate=p, truth=t, noisy=noisy, kind=kind, list=lst_name, top=top, score=round(m[0][0], 3),
                                       margin=round(margin, 3), ok=top == t, in_list=t in lst))
    for lst_name in ('whole list', 'plate-local'):
        for kind in ('1 swap', '2 swaps', '1 dropped'):
            L = [x for x in T2 if x['list'] == lst_name and x['kind'] == kind]
            if not L:
                continue
            ok = sum(x['ok'] for x in L); inl = sum(x['in_list'] for x in L)
            conf = [x for x in L if x['margin'] >= 0.05 and x['score'] <= 0.25]
            print(f'  {lst_name:11s} {kind:9s}: {len(L):4d} reads, truth in list {inl / len(L):6.1%}, top-1 right {ok / len(L):6.1%}; '
                  f'confident (score<=0.25, margin>=0.05) {len(conf) / len(L):6.1%} of which right {sum(x["ok"] for x in conf) / max(1, len(conf)):6.1%}')
    rep['T2'] = T2

    # ---- T3 the same crossing read on two plates
    print('\n== T3 crossings read on two adjoining plates (within 30 m)')
    T3 = []
    def key2(r):
        ks = []
        for n in (r['a'], r['b']):
            b_ = base(norm(n)); ks.append({b_} | alias.get(b_, set()))
        return ks
    for i, r in enumerate(R):
        for q in R[i + 1:]:
            if q['plate'] <= r['plate'] or q['plate'] == r['plate']:
                continue
            d = np.hypot(r['E'] - q['E'], r['N'] - q['N'])
            if d > 30:
                continue
            A = key2(r); B = key2(q)
            known = all(not ({'?', ''} & a) for a in A + B)
            same = (A[0] & B[0] and A[1] & B[1]) or (A[0] & B[1] and A[1] & B[0])
            T3.append(dict(a_plate=r['plate'], b_plate=q['plate'], a=f"{r['a']} & {r['b']}", b=f"{q['a']} & {q['b']}", dist_m=round(float(d), 1),
                           agree=bool(same), both_named=bool(known)))
    pairs = collections.Counter((t['a_plate'], t['b_plate']) for t in T3)
    print('  plate pairs:', dict(pairs))
    named = [t for t in T3 if t['both_named']]
    print(f"  pairs of reads: {len(T3)}; both fully named {len(named)}; agree {sum(t['agree'] for t in named)} ({sum(t['agree'] for t in named) / max(1, len(named)):.1%})")
    for t in named:
        if not t['agree']:
            print(f"   disagree: {t['a_plate']} '{t['a']}'  vs  {t['b_plate']} '{t['b']}'  ({t['dist_m']} m)")
    rep['T3'] = T3

    # ---- T4 today's name near the crossing
    print("\n== T4 each read name against today's OSM names within 40 m of the crossing (aliases applied)")
    T4 = collections.Counter(); bad = collections.Counter()
    for r in R:
        near = osm_near(r['E'], r['N'], 40)
        for n in (r['a'], r['b']):
            b_ = base(norm(n))
            if b_ in ('', '?', 'alley'):
                T4['unnamed read'] += 1; continue
            if b_ in near or alias.get(b_, set()) & near:
                T4['matches OSM'] += 1
            elif not near:
                T4['no OSM street within 40 m'] += 1
            else:
                close = min(((wdist(b_, o) / max(len(o), 1)), o) for o in near)
                if close[0] <= 0.15:
                    T4['OSM spelling differs slightly'] += 1
                else:
                    T4['different name in OSM'] += 1; bad[(b_, tuple(sorted(near))[:4])] += 1
    tot = sum(T4.values())
    for k, v in T4.most_common():
        print(f'  {k:32s} {v:5d} ({v / tot:.1%})')
    print('  most frequent mismatches (read base -> OSM bases within 40 m):')
    for (b_, nr), c in bad.most_common(15):
        print(f'   {c:3d}  {b_!r} -> {nr}')
    rep['T4'] = dict(counts=dict(T4), mismatches=[[k[0], list(k[1]), c] for k, c in bad.most_common(60)])

    # ---- T5 adjoining sheet numbers of plate 44 (read by eye in crops/m44_margins.png, m44_bottom_wide.png)
    print('\n== T5 adjoining sheet numbers printed in the margins of plate 44, against the world models')
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    models = sorted(os.path.basename(os.path.dirname(f)) for f in glob.glob(platemap.ROOT + '*/model.npz'))
    size = {p: Image.open(f'{platemap.ROOT}22-{p}.jpg').size for p in models}
    margin = [('top', 4500, 120, '45'), ('right', 10250, 2700, '39'), ('left', 100, 3800, '3 (a digit before it is cut by the scan edge)'),
              ('bottom', 740, 7100, '37')]
    T5 = []
    for side, x, y, printed in margin:
        E, N = platemap.px_to_world('44', x, y)
        hits = [p for p in models if p != '44' and (lambda q: q is not None and 0 <= q[0] < size[p][0] and 0 <= q[1] < size[p][1])(platemap.world_to_px(p, E, N))]
        ok = printed.split()[0] in hits or any(h.endswith(printed.split()[0]) for h in hits)
        T5.append(dict(side=side, printed=printed, models_there=hits, verdict=('agrees' if printed.split()[0] in hits else
                  ('completes the partial read' if ok else ('no world model for that plate' if not hits else 'disagrees')))))
        print(f'  {side:6s} printed {printed!r:50s} plates the models put there {hits}: {T5[-1]["verdict"]}')
    rep['T5'] = T5
    json.dump(rep, open(os.path.join(BASE, 'out', 'names.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
