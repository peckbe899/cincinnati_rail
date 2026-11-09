"""Two independent reads per strip -> picks (Ben, 8 November 2026: plates 25 and 28; docs/sanborn/RULES.md rule 12).

    cd data/sanborn
    python ../../tools/sanborn/complete/merge_reads.py 22-25 22-28

Reads: data/sanborn/picks22_reads/<sheet>/<A|B>_<part>.json, each a full read of one strip (INSTRUCTIONS22.md, section of
8 November). Within a strip, a crossing of read A and one of read B are the same crossing when their street names match
(sbg/names.py key and base, either order) and they lie within 60 px; each read's crossing pairs with at most one of the
other's, nearest first. A pick is kept only for such a pair, at the mean of the two. Crossings with "?" for a name are
not picks (the fit cannot match them to OSM). Bends, ends and widths are kept from both reads (a bend or end of one
street within 60 px in both reads counts once, at the mean).

Where the two reads name one street differently, two further readers asked only what is printed on it settle the name
(picks22_reads/<sheet>/names_resolved.json); the merge applies their agreed names before pairing.

Writes sbg/picks22/<sheet>_<part>.json (the existing layout: s22-25_1.json ...), and picks22_reads/<sheet>/merge.json
and README.md: per strip and per plate the crossings read, the picks, and every crossing the reads did not agree on
(only one read has it, or both have it more than 60 px apart).
"""
import collections, datetime, glob, json, os, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _ws  # noqa: E402
sys.path.insert(0, _ws.CODE + 'sbg')
from names import key, base  # noqa: E402

SP = _ws.DATA
AGREE_PX = 60.0


def k2(a, b):
    return tuple(sorted((base(key(a)), base(key(b)))))


def pair(LA, LB, keyf):
    """nearest-first one-to-one pairs of LA and LB items with the same key within AGREE_PX"""
    cand = []
    for i, a in enumerate(LA):
        for j, b in enumerate(LB):
            if keyf(a) == keyf(b):
                d = float(np.hypot(a['x'] - b['x'], a['y'] - b['y']))
                if d <= AGREE_PX:
                    cand.append((d, i, j))
    ti, tj, out = set(), set(), []
    for d, i, j in sorted(cand):
        if i in ti or j in tj:
            continue
        ti.add(i); tj.add(j); out.append((i, j, d))
    return out, ti, tj


def merge_plate(sheet):
    D = SP + f'picks22_reads/{sheet}/'
    parts = sorted({int(os.path.basename(f)[2:-5]) for f in glob.glob(D + '[AB]_*.json')})
    rows, dis = [], []
    for k in parts:
        fa, fb = D + f'A_{k}.json', D + f'B_{k}.json'
        if not (os.path.exists(fa) and os.path.exists(fb)):
            rows.append(dict(part=k, missing_read='A' if not os.path.exists(fa) else 'B')); continue
        A, B = json.load(open(fa, encoding='utf8')), json.load(open(fb, encoding='utf8'))
        # a street the two reads named differently, settled by two further readers (picks22_reads/<sheet>/names_resolved.json)
        rf = D + 'names_resolved.json'
        for rn in (json.load(open(rf, encoding='utf8'))['renames'] if os.path.exists(rf) else []):
            if rn['part'] != k:
                continue
            x0, y0, x1, y1 = rn['box']
            for p in (A if rn['read'] == 'A' else B).get('intersections', []):
                if x0 <= p['x'] <= x1 and y0 <= p['y'] <= y1:
                    for f in ('a', 'b'):
                        if p[f] == rn['frm']:
                            p[f] = rn['to']; p['renamed'] = f"{rn['frm']} -> {rn['to']} (names_resolved.json)"
        IA = [p for p in A.get('intersections', []) if '?' not in p['a'] + p['b']]
        IB = [p for p in B.get('intersections', []) if '?' not in p['a'] + p['b']]
        pr, ta, tb = pair(IA, IB, lambda p: k2(p['a'], p['b']))
        picks = []
        for i, j, d in pr:
            a, b = IA[i], IB[j]
            picks.append(dict(a=a['a'], b=a['b'], x=round((a['x'] + b['x']) / 2, 1), y=round((a['y'] + b['y']) / 2, 1),
                              kind=a.get('kind') or b.get('kind'), reads=[dict(read='A', x=a['x'], y=a['y']), dict(read='B', x=b['x'], y=b['y'])],
                              spread_px=round(d, 1), **({'b_names': [b['a'], b['b']]} if (b['a'], b['b']) != (a['a'], a['b']) else {})))
        # the rest: is it in the other read at all (same names, any distance)?
        for which, L, taken, other in (('A', IA, ta, IB), ('B', IB, tb, IA)):
            for i, p in enumerate(L):
                if i in taken:
                    continue
                same = [q for q in other if k2(q['a'], q['b']) == k2(p['a'], p['b'])]
                near = min(same, key=lambda q: np.hypot(q['x'] - p['x'], q['y'] - p['y'])) if same else None
                dd = float(np.hypot(near['x'] - p['x'], near['y'] - p['y'])) if near else None
                why = f'only read {which} has it' if near is None else f'the reads are {dd:.0f} px apart'
                if near is not None and which == 'B' and any(r['part'] == k and r['crossing'] == f"{p['a']} & {p['b']}" and r['why'] == why for r in dis):
                    continue
                dis.append(dict(part=k, crossing=f"{p['a']} & {p['b']}", read=which, x=p['x'], y=p['y'], why=why,
                                other=None if near is None else dict(x=near['x'], y=near['y'])))
        def union(LA, LB, keyf):
            pr2, t1, t2 = pair(LA, LB, keyf)
            out = [dict(LA[i], x=round((LA[i]['x'] + LB[j]['x']) / 2, 1), y=round((LA[i]['y'] + LB[j]['y']) / 2, 1)) for i, j, d in pr2]
            out += [p for i, p in enumerate(LA) if i not in t1] + [p for j, p in enumerate(LB) if j not in t2]
            return out
        bends = union(A.get('bends', []), B.get('bends', []), lambda p: base(key(p.get('street', ''))))
        ends = union(A.get('ends', []), B.get('ends', []), lambda p: base(key(p.get('street', ''))))
        wid = {}
        for w in A.get('widths', []) + B.get('widths', []):
            wid.setdefault(base(key(w.get('street', ''))), w)
        out = dict(sheet=sheet, part=k, strip=A.get('strip'), made=datetime.datetime.now().isoformat(timespec='seconds'),
                   by='tools/sanborn/complete/merge_reads.py: two independent reads, a pick only where they agree within 60 px',
                   reads=[os.path.relpath(fa, SP).replace('\\', '/'), os.path.relpath(fb, SP).replace('\\', '/')],
                   intersections=picks, widths=list(wid.values()), bends=bends, ends=ends,
                   notes=' | '.join(x for x in (A.get('notes'), B.get('notes')) if x))
        json.dump(out, open(SP + f'sbg/picks22/s{sheet}_{k}.json', 'w', encoding='utf8', newline='\n'), indent=1)
        rows.append(dict(part=k, read_A=len(IA), read_B=len(IB), picks=len(picks),
                         disagree=sum(1 for r in dis if r['part'] == k)))
    # a crossing in the overlap of two strips may be read by A in one strip and by B in the next: two independent
    # reads all the same. Pair such leftovers (only-one-read entries of neighbouring strips) and add them as picks.
    only = [d for d in dis if d['why'].startswith('only read')]
    used, extra = set(), []
    for i, a in enumerate(only):
        for j, b in enumerate(only):
            if j <= i or i in used or j in used or a['read'] == b['read'] or abs(a['part'] - b['part']) != 1:
                continue
            ka = k2(*a['crossing'].split(' & ', 1)); kb = k2(*b['crossing'].split(' & ', 1))
            d = float(np.hypot(a['x'] - b['x'], a['y'] - b['y']))
            if ka == kb and d <= AGREE_PX:
                used |= {i, j}; extra.append((a, b, d))
    for a, b, d in extra:
        k = min(a['part'], b['part']); f = SP + f'sbg/picks22/s{sheet}_{k}.json'
        J = json.load(open(f, encoding='utf8')); n1, n2 = a['crossing'].split(' & ', 1)
        J['intersections'].append(dict(a=n1, b=n2, x=round((a['x'] + b['x']) / 2, 1), y=round((a['y'] + b['y']) / 2, 1), kind=None,
                                       reads=[dict(read=a['read'], part=a['part'], x=a['x'], y=a['y']), dict(read=b['read'], part=b['part'], x=b['x'], y=b['y'])],
                                       spread_px=round(d, 1), note='read once in each of two neighbouring strips (their overlap)'))
        json.dump(J, open(f, 'w', encoding='utf8', newline=chr(10)), indent=1)
        for r in rows:
            if r['part'] == k:
                r['picks'] += 1
        for r in rows:
            if r['part'] in (a['part'], b['part']):
                r['disagree'] -= 1
    dis = [d for i, d in enumerate(only) if i not in used] + [d for d in dis if not d['why'].startswith('only read')]
    return rows, dis


def main(sheets):
    allrows = {}
    L = ['# Plates 25 and 28: the two reads merged (' + datetime.date.today().isoformat() + ')', '',
         'Each strip read twice, independently (`docs/sanborn/workspace_notes/sbg/INSTRUCTIONS22.md`, section of 8 November). '
         'A pick is kept only where the two reads have the same crossing (same street names) within 60 px, at their mean '
         '(`tools/sanborn/complete/merge_reads.py`). Strips overlap by about 300 px, so a crossing near a strip edge can be '
         'counted in two strips; the fit merges those.', '']
    for sh in sheets:
        rows, dis = merge_plate(sh)
        json.dump(dict(sheet=sh, strips=rows, disagreements=dis), open(SP + f'picks22_reads/{sh}/merge.json', 'w', encoding='utf8', newline='\n'), indent=1)
        allrows[sh] = (rows, dis)
        L += [f'## {sh}', '', '| Strip | Read A crossings | Read B crossings | Picks | Not agreed |', '|---|---|---|---|---|']
        for r in rows:
            L.append(f"| {r['part']} | {r.get('read_A')} | {r.get('read_B')} | {r.get('picks')} | {r.get('disagree')} |")
        L.append(f"| **All** | {sum(r.get('read_A', 0) for r in rows)} | {sum(r.get('read_B', 0) for r in rows)} | {sum(r.get('picks', 0) for r in rows)} | {len(dis)} |")
        L += ['', 'Crossings the reads did not agree on:', '']
        L += [f"- strip {d['part']}, {d['crossing']} (read {d['read']} at {d['x']:.0f}, {d['y']:.0f}): {d['why']}" for d in dis] or ['- none']
        L.append('')
        print(sh, rows, 'disagreements', len(dis))
    open(SP + 'picks22_reads/README.md', 'w', encoding='utf8', newline='\n').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main(sys.argv[1:])
