"""RER-4 (TRI D) north of Camp Washington on the upper deck with the Indianapolis APEx (Ben, 2026-10-27).

The lower deck of the north arch viaduct carries the ORR and Transvalley pairs, R5, B and the APEx Dayton and Norwood
pairs over the roads. D and the Indianapolis APEx pair run on an upper deck at the minimum height over it (the crossing
rule, 7.9 m over its highest rail), held to the hillside, then climb at a constant grade in a tunnel to the Floridian
portal at the ground, about 186 m. The geometry is the Profiles context's (tools/make_profile_context.py upper_deck()),
so the profile, the context blocks and Station 3D agree.

D leaves the Camp Washington platform end on the lower deck (between the B tracks) and climbs at 2.5% (the Deck's
grade) to the upper deck, follows it and the tunnel to the portal, then climbs at no more than the RER maximum grade
to its default profile (it goes on up to Monfort Heights). From Union Terminal to Camp Washington D runs on the B/D
pair, so it takes B's station levels and no bend points between them: the same rail as B (Ben, 2026-10-27: the
heights match). South of Union Terminal the editor's defaults are kept.

Writes data/profile/rer/alignments/RER_4.json in the Rail Profiles page's saved-profile form (st, pvi, ovr), and the
locked stretches in data/profile/rer/canon.json (Ben, 2026-10-27: the viaduct heights are locked): B from the
Northside / Spring Grove platform (the viaduct end) to the Straight platform, D from the Straight platform to the
Floridian portal. The page and railsim/metro_profile.py hold them whatever a saved profile says.

    python tools/make_rer4_upper.py
"""
import datetime
import json
import sys
from pathlib import Path as P

import numpy as np

ROOT = P(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
from railsim.metro_profile import MetroProfile   # noqa: E402

SITE = ROOT / 'data' / 'profile'
STEP = 10.0
START = 'Camp Washington'
SHARED = ('Union Terminal', 'Western', 'Straight', 'Camp Washington')   # on the B/D pair: B's levels


def main():
    import make_profile_context as mpc
    from shapely.geometry import Point
    d4 = json.loads((SITE / 'rer/lines/RER_4.json').read_text())
    mp = MetroProfile.load(SITE / 'rer/lines/RER_4.json', None, SITE / 'rer/settings.json')
    path4 = mpc.Path(d4['path'])
    I = mpc.build()['indy']
    mp2 = MetroProfile.load(SITE / 'rer/lines/RER_2.json', SITE / 'rer/alignments/RER_2.json', SITE / 'rer/settings.json')
    b_st = {s['name']: float(mp2.st[i]) for i, s in enumerate(mp2.stations)}
    names = [s['name'] for s in mp.stations]
    i0 = names.index(START)
    half = mp.settings['platform'] / 2
    c_cw, z_cw = mp.stations[i0]['c'], float(mp.st[i0])
    c_pe = c_cw + half
    cs = np.arange(c_pe, mp.length + 1e-6, STEP)
    c_port = path4.chain(I['portal'])                       # the Floridian portal on D's line
    c_hill = path4.chain(I['ref'].interpolate(I['d_h']).coords[0])   # the hillside on D's line
    # the climb at 2.5% to the upper deck, held to the hillside, the tunnel grade to the portal
    z = np.minimum(z_cw + mpc.UPPER_GRADE * (cs - c_pe), I['H'])
    m = (cs > c_hill) & (cs <= c_port)
    z[m] = I['H'] + (I['z_p'] - I['H']) * (cs[m] - c_hill) / (c_port - c_hill)
    # past the portal: at no more than the RER maximum grade to the default profile, then the default
    dflt = np.array([float(mp.rail_at(c)) for c in cs])
    gmax = mp.settings['maxGrade'] / 1000.0
    j_p = int(np.searchsorted(cs, c_port, side='right'))
    for j in range(j_p, len(cs)):
        d = cs[j] - c_port
        z[j] = min(max(dflt[j], I['z_p'] - gmax * d), I['z_p'] + gmax * d)
    j_join = next((j for j in range(j_p, len(cs)) if abs(z[j] - dflt[j]) < 0.01 and all(abs(z[k] - dflt[k]) < 0.01 for k in range(j, min(len(cs), j + 20)))), len(cs) - 1)
    c_join = cs[j_join]
    st_doc = {mp.st_key(i): round(b_st[s['name']] if s['name'] in SHARED else float(mp.st[i]), 2) for i, s in enumerate(mp.stations)}
    assert abs(st_doc[mp.st_key(i0)] - z_cw) < 0.01, 'Camp Washington: B and D differ'
    c_ut = mp.stations[names.index('Union Terminal')]['c']
    for i in range(i0 + 1, len(mp.stations)):              # level platforms on the new stretch
        c = mp.stations[i]['c']
        if c - half > c_join:
            continue
        mm = (cs >= c - half) & (cs <= c + half)
        st_doc[mp.st_key(i)] = round(float(z[mm].max()), 2)
        z[mm] = z[mm].max()
    vc, vz = mp.vertices()
    pvi = [[round(float(c), 1), round(float(zz), 2)] for c, zz in zip(vc, vz) if c < c_ut - half - 1]
    keep = [0]
    for j in range(1, j_join):
        g0 = (z[j] - z[keep[-1]]) / (cs[j] - cs[keep[-1]])
        g1 = (z[j + 1] - z[j]) / (cs[j + 1] - cs[j])
        if abs(g1 - g0) > 0.0005:
            keep.append(j)
    keep.append(j_join)
    pvi += [[round(float(cs[j]), 1), round(float(z[j]), 2)] for j in keep]
    pvi += [[round(float(c), 1), round(float(zz), 2)] for c, zz in zip(vc, vz) if c > c_join + 1]
    doc = {'line': 'RER-4', 'system': 'Cincinnati RER', 'length_m': d4['length_m'], 'platform_m': mp.settings['platform'],
           'st': st_doc, 'sg': {}, 'so': {}, 'del': [], 'gapfill': [], 'pvi': pvi,
           'ovr': [[round(c_pe, 1), round(c_hill, 1), 'elevated'], [round(c_hill, 1), round(float(c_port), 1), 'deep']],
           'updated': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z'), 'v': 1,
           'note': (f'Generated by tools/make_rer4_upper.py (Ben, 2026-10-27): from the Camp Washington platform end D climbs at '
                    f'{mpc.UPPER_GRADE * 100:.1f}% to the upper deck with the Indianapolis APEx ({I["H"]:.1f} m, {mpc.UPPER_CLEAR} m over the '
                    f'lower deck\'s highest rail), holds it to the hillside ({c_hill:.0f} m), climbs in the tunnel to the Floridian portal '
                    f'({I["z_p"]:.0f} m at {c_port:.0f} m), then rejoins the editor\'s defaults by {c_join:.0f} m. Not saved in the Rail Profiles editor.')}
    out = SITE / 'rer/alignments/RER_4.json'
    out.write_text(json.dumps(doc, indent=1))
    # the locks: B on the viaduct and the ramp into the Straight box, D from the Straight box to the portal
    cj = SITE / 'rer/canon.json'
    canon = json.loads(cj.read_text())
    st2 = {s['name']: s['c'] for s in mp2.stations}
    lo2, hi2 = st2['Northside / Spring Grove'] - half, st2['Straight'] + half
    canon['lines']['RER_2']['locked'] = [{
        'c0': round(lo2, 1), 'c1': round(hi2, 1),
        'st': {n: round(b_st[n], 2) for n in ('Northside / Spring Grove', 'Arlington', 'Camp Washington', 'Straight')},
        'pvi': [[round(c, 1), round(z, 2)] for c, z in mp2.pvi if lo2 <= c <= hi2],
        'ovr': [[round(a, 1), round(b, 1), t] for a, b, t in mp2.ovr if a >= lo2 and b <= hi2],
        'src': 'B on the north viaduct (Northside 162.5, Arlington 165.9, Camp Washington 165.2 m) and the ramp into the Straight box (151.64 m), as the Deck (Ben, 27 October): locked'}]
    lo4 = mp.stations[names.index('Straight')]['c'] - half
    canon['lines']['RER_4']['locked'] = [{
        'c0': round(lo4, 1), 'c1': round(float(c_port), 1),
        'st': {n: st_doc[mp.st_key(names.index(n))] for n in ('Straight', 'Camp Washington')},
        'pvi': [p for p in pvi if lo4 <= p[0] <= c_port],
        'ovr': doc['ovr'],
        'src': f'D on the B/D pair from the Straight box to Camp Washington, then the upper deck with the Indianapolis APEx ({I["H"]:.1f} m) to the hillside and the Floridian tunnel to the portal ({I["z_p"]:.0f} m), as the Deck (Ben, 27 October): locked'}]
    cj.write_text(json.dumps(canon, indent=1, ensure_ascii=False) + '\n')
    chk = MetroProfile.load(SITE / 'rer/lines/RER_4.json', out, SITE / 'rer/settings.json')
    rail = np.array([float(chk.rail_at(c)) for c in cs])
    gr = np.diff(rail) / STEP * 1000
    print(f'RER-4: {START} {z_cw} m, platform end {c_pe:.0f} m; upper deck {I["H"]:.1f} m; hillside {c_hill:.0f} m; '
          f'portal {c_port:.0f} m ({I["z_p"]:.0f} m); defaults from {c_join:.0f} m; max grade {np.abs(gr[cs[1:] <= c_join + 50]).max():.1f} per mille')
    for c in list(range(int(c_pe), int(c_join) + 400, 400)):
        j = int(np.argmin(np.abs(cs - c)))
        print(f'  c {cs[j]:>7.0f}  rail {rail[j]:7.2f}  ground {float(chk.ground_at(cs[j])):7.2f}  {chk.type_at(cs[j])}')
    print('summary', chk.summary())


if __name__ == '__main__':
    main()
