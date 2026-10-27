"""The RER rights of way the Mill Creek Deck sets, as locked stretches of the Rail Profiles canon (Ben, 2026-10-27:
"implement and lock all of the existing RER ROWs that are set, like Evans to Westwood and Evans to Spring Grove
Cemetery").

RER A (Deck design note of 13 and 21 October; its RER marks, street cuts and structure lines, data/deck):
- trunk, fork to Union Terminal: 159.3 m at the fork (Dolph), a walled ramp down at 3.3% (Bank 155.2, Dayton 152.5),
  the box under Exeter, 148.4 m where it leaves the deck north of York, 147.5 m at Evans under W Liberty, 135.9 m
  under CUT's lower level (8.1 m under its 144.0 m rail), Union Terminal 135.7 m;
- Westwood branch: from the fork on a viaduct, 3.26% up to its platform at ground, 168.9 m;
- the stem to South Cumminsville, on a viaduct: Western Hills 165.2 m (over Harrison), 168.2 m over the Hopple
  viaduct, easing to 167.0 m under RER D and held through South Cumminsville to the split;
- RER-1a (the Wyoming branch): 167.0 m through Northside, then 3.3% down from the platform end (Chambers 157.2,
  Lingo 155.2, Dane 152.9) to 144.2 m under Linden, into the tunnel under Spring Grove Cemetery (not profiled beyond);
- RER-1b (the Colerain branch): its viaduct from the split, 300 m at 167.0 m (its descent is not set in the Deck).

RER B: its flyover viaduct over APEx Dayton between Paddock and Fairgrounds (the Deck: 7.3 m or more over it), at
175.0 m over the crossing, 8.3 m over the APEx at ground (the Rail Profiles crossing rule for a viaduct over at grade).

Each anchor is a Deck point, projected onto the route, so the locks follow the routes when tools/rer_deck_routes.py
rebuilds them. The B and D locks (tools/make_rer4_upper.py, moved onto the trunks) are kept. Writes
data/profile/rer/canon.json.

    python tools/rer_deck_locks.py
"""
import os
import sys

from shapely.geometry import Point

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rer_deck_routes import SITE, ROOT, chain_of, jload, jsave   # noqa: E402

HALF = 204.2 / 2
TAG = 'Deck RER A'
STATE_TYPE = {'viaduct': 'elevated', 'tunnel': 'cutcover', 'deck': 'cutcover', 'ramp': None}   # a walled ramp: by the ground

# route: (from, to, stations {name: rail}, bend points [(Deck point, rail)], structure from the Deck's rer_struct, src)
ROWS = {
    'RER_A_trunk': dict(
        a=('c', 0.0), b=('platform_end', 'Union Terminal'),
        st={'Evans': 147.5, 'Union Terminal': 135.7},
        pvi=[('start', 159.3), ((712359.0, 4332994.0), 155.2), ((712352.3, 4332912.8), 152.5),
             ((712341.5, 4332787.8), 148.4), ('ctx', 'CUT lower level', 135.9)],
        struct=('A', ('ramp', 'tunnel', 'deck')),
        src='RER A from the fork (159.3 m) down its 3.3% walled ramp (Bank 155.2, Dayton 152.5), the box under Exeter, '
            'off the deck north of York (148.4 m), Evans 147.5 m under W Liberty, 135.9 m under CUT\'s lower level, '
            'Union Terminal 135.7 m (Deck, Ben 13 October): locked'),
    'RER_A_westwood': dict(
        a=('c', 0.0), b=('platform_end', 'Westwood'),
        st={'Westwood': 168.9},
        pvi=[('start', 159.3)],
        struct=('A (Westwood)', ('viaduct',)),
        src='RER A Westwood branch from the fork (159.3 m) on a viaduct, over State Avenue (162.5 m), 3.26% up to its '
            'platform at ground, 168.9 m (Deck, Ben 13 October): locked'),
    'RER_A_cumminsville': dict(
        a=('c', 0.0), b=('end',),
        st={'Western Hills': 165.2, 'Hopple': 168.2, 'South Cumminsville': 167.0},
        pvi=[('start', 159.3), ((711695.0, 4336518.8), 167.0), ('end', 167.0)],
        struct=('A', ('viaduct',)),
        src='RER A on its viaduct from the fork: Western Hills 165.2 m over Harrison, 168.2 m over the Hopple viaduct, '
            'easing to 167.0 m under RER D (174.3 m) and held through South Cumminsville to the split (Deck, Ben 21 '
            'October): locked'),
    'RER_A_wyoming': dict(
        a=('c', 0.0), b=('pt', (713508.0, 4337876.0)),
        st={'Northside': 167.0},
        pvi=[('start', 167.0), ((713418.8, 4337832.8), 144.2)],
        extend=((713508.0, 4337876.0), -0.033),   # the 3.3% on through the Deck's tunnel stretch, so Linden is on the grade
        struct=('A', ('viaduct', 'tunnel')),
        src='RER-1a from the split at 167.0 m through Northside, then 3.3% down from the platform end (Chambers 157.2, '
            'Lingo 155.2, Dane 152.9) to 144.2 m under Linden, on at 3.3% through the Deck\'s tunnel stretch under Spring Grove '
            'Cemetery (Deck, Ben 13 October; not profiled beyond): locked'),
    'RER_A_colerain': dict(
        a=('c', 0.0), b=('c', 300.0),
        st={},
        pvi=[('start', 167.0), (('c', 300.0), 167.0)],
        struct=('A (RER-1b)', ('viaduct',)),
        src='RER-1b on its viaduct from the split at 167.0 m (Deck; its descent past OH-74 is not set): locked'),
    'RER_B_trunk': dict(
        a=('pt', (718015.0, 4341695.0)), b=('pt', (718465.0, 4342256.0)),
        st={},
        pvi=[(('at', (718272.9, 4341973.3), -60.0), 175.0), (('at', (718272.9, 4341973.3), 60.0), 175.0)],   # level over the APEx
        struct=('B', ('viaduct',)),
        tag='Deck RER B flyover',
        src='RER B over APEx Dayton between Paddock and Fairgrounds on the Deck\'s 720 m flyover viaduct: 175.0 m over the APEx '
            'at ground (166.7 m), 8.3 m, the crossing rule for a viaduct over track at grade (the Deck: 7.3 m or more): locked'),
}


def main():
    canon_f = os.path.join(SITE, 'rer', 'canon.json')
    canon = jload(canon_f)
    ctx = jload(os.path.join(ROOT, 'data', 'deck', 'context.json'))
    pctx = jload(os.path.join(SITE, 'context', 'lines.json'))['lines']
    for rid, row in ROWS.items():
        r = jload(os.path.join(SITE, 'rer', 'lines', rid + '.json'))
        L, chain, at = chain_of(r['path'])
        sc = {s['name']: s['c'] for s in r['stations']}

        def where(spec):
            if spec[0] == 'pt':
                return chain(spec[1])
            if spec[0] == 'c':
                return spec[1]
            if spec[0] == 'end':
                return r['length_m']
            if spec[0] == 'start':
                return 0.0
            if spec[0] == 'platform_end':
                return sc[spec[1]] + HALF
            raise ValueError(spec)
        c0, c1 = sorted((where(row['a']), where(row['b'])))
        pvi = []
        for q in row['pvi']:
            if q[0] == 'ctx':   # a level under another structure: at its end nearer the fork
                blk = next(b for b in pctx.get(rid, {}).get('blocks', []) if b['n'].startswith(q[1]))
                c = min(blk['c0'], blk['c1'])
            elif q[0] in ('start', 'end'):
                c = where((q[0],))
            elif q[0][0] == 'at':              # ('at', Deck point, metres along the route from it)
                c = chain(q[0][1]) + q[0][2]
            elif isinstance(q[0][0], str):     # ('c', chainage)
                c = where(q[0])
            else:                              # a Deck point
                c = chain(q[0])
            pvi.append([round(c, 1), q[-1]])
        if row.get('extend'):
            pt, g = row['extend']
            c_end = chain(pt)
            pvi.append([round(c_end, 1), round(pvi[-1][1] + g * (c_end - pvi[-1][0]), 2)])
        for nm in row['st']:   # no bend point inside a platform: the station level holds it
            pvi = [p for p in pvi if abs(p[0] - sc[nm]) > HALF + 1]
        pvi.sort()
        ovr = []
        line, states = row['struct']
        for x in ctx['rer_struct']:
            t = STATE_TYPE.get(x['state'])
            if x['line'] != line or x['state'] not in states or not t:
                continue
            a, b = sorted((chain(x['c'][0]), chain(x['c'][-1])))
            if L.distance(Point(x['c'][0])) > 30 and L.distance(Point(x['c'][-1])) > 30:
                continue
            a, b = max(a, c0), min(b, c1)
            if b - a > 1:
                ovr.append([round(a, 1), round(b, 1), t])
        ovr.sort()
        cn = canon['lines'].setdefault(rid, {})
        tag = row.get('tag', TAG)
        cn['locked'] = [lk for lk in cn.get('locked', []) if lk.get('by') != tag] + [
            {'c0': round(c0, 1), 'c1': round(c1, 1), 'st': row['st'], 'pvi': pvi, 'ovr': ovr, 'src': row['src'], 'by': tag}]
        print(f"{rid}: locked {c0:.0f}-{c1:.0f}, stations {row['st']}, bends {pvi}, structure {ovr}")
    jsave(canon_f, canon, indent=1)


if __name__ == '__main__':
    main()
