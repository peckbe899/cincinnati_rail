"""RER-4 (TRI D) north of Camp Washington on the upper deck, tied to the APEx level (Ben, 2026-10-27).

The Mill Creek Deck's APEx level is canon. From Camp Washington to the region edge D runs above the APEx
(the north arch viaduct, then the Indianapolis / Floridian line), so its rail is set from what lies under it:

    target = (the highest rail under D) + 7.9 m

7.9 m is the crossing rule (D's deck 1.6 m + 0.5 m + 5.8 m clear, RER); "under D" is any rail within FOOT m of
D's line: the Deck's structures (APEx, ORR and Transvalley on the north arch viaduct and its fill, at the Deck's
APEx levels), RER-2 (B) at its saved level, and, past the viaduct where the Deck's APEx tracks have no level,
nothing: the tie ends where the Deck's APEx level ends (the west end of the north arch viaduct, at the Deck's plan
window). D climbs from the Camp Washington platform end at GRADE (the Deck's 2.5%) while it peels off between the B
tracks, holds at least the target with grades no steeper than GRADE, and past it climbs at no more than the RER maximum
grade to its default profile (it goes on up to Monfort Heights).

Writes data/profile/rer/alignments/RER_4.json in the Rail Profiles page's saved-profile form: station levels
(st), vertices (pvi) and painted structure (ovr: elevated from the Camp Washington platform end). South of Camp
Washington the editor's default levels are kept as they are.

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
CLEAR = 7.9      # crossing rule over a rail below: deck 1.6 + 0.5 + 5.8 m clear (RER)
MARGIN = 0.3     # for the vertical curves at the crests
GRADE = 0.025    # the Deck's climb to the Indianapolis deck (2.5%)
FOOT = 9.0       # rails this close to D's line are under its deck (half its width, about)
STEP = 10.0
START = 'Camp Washington'


def main():
    import make_profile_context as mpc
    from shapely.geometry import Point
    from shapely.prepared import prep
    d4 = json.loads((SITE / 'rer/lines/RER_4.json').read_text())
    mp = MetroProfile.load(SITE / 'rer/lines/RER_4.json', None, SITE / 'rer/settings.json')
    b2 = MetroProfile.load(SITE / 'rer/lines/RER_2.json', SITE / 'rer/alignments/RER_2.json', SITE / 'rer/settings.json')
    path4, path2 = mpc.Path(d4['path']), mpc.Path(json.loads((SITE / 'rer/lines/RER_2.json').read_text())['path'])
    B = mpc.build()
    structs = [(st, prep(st['geom'].buffer(FOOT))) for st in B['S'] if st['short'] in ('North arch viaduct', 'North trunk fill')]
    import shapely
    from shapely.ops import unary_union
    T = B['T']

    names = [s['name'] for s in mp.stations]
    i0 = names.index(START)
    half = mp.settings['platform'] / 2
    c_cw, z_cw = mp.stations[i0]['c'], float(mp.st[i0])
    c_pe = c_cw + half                                   # the platform's north end
    cs = np.arange(c_pe, mp.length + 1e-6, STEP)
    below, src = [], []
    for c in cs:
        x, y = path4.at(c)
        q = Point(x, y)
        zb, s = -1e9, None
        for st, pp in structs:
            if pp.contains(q):
                z = st['z'](x, y)
                if z > zb:
                    zb, s = z, st['short']
        c2 = path2.chain((x, y))
        x2, y2 = path2.at(c2)
        if np.hypot(x2 - x, y2 - y) < FOOT:
            z = float(b2.rail_at(c2))
            if z > zb:
                zb, s = z, 'RER-2 (B)'
        below.append(zb)
        src.append(s)
    below = np.array(below)
    target = np.where(below > -1e8, below + CLEAR + MARGIN, -1e9)
    # the envelope: at least the target, no steeper than GRADE either way
    env = np.full(len(cs), -1e9)
    for j, t in enumerate(target):
        if t > -1e8:
            env = np.maximum(env, t - GRADE * np.abs(cs - cs[j]))
    tied = np.where(below > -1e8)[0]
    c_end = cs[tied[-1]] if len(tied) else c_pe          # the last point with the Deck's APEx level under D
    climb = z_cw + GRADE * (cs - c_pe)
    z = np.minimum(climb, np.maximum(env, z_cw))         # the climb from the platform end, then the envelope
    # past the tie D has to reach its default profile (it climbs on to Monfort Heights): the tied level, raised where
    # needed so that D can climb to the default at no more than the RER's maximum grade, then the default
    dflt = np.array([float(mp.rail_at(c)) for c in cs])
    gmax = mp.settings['maxGrade'] / 1000.0
    base = np.where(cs <= c_end, z, -1e9)
    after_tie = cs > c_end
    base[after_tie] = dflt[after_tie]
    zz = base.copy()
    for j in np.where(after_tie)[0]:                     # reachable from every later point at gmax
        zz = np.maximum(zz, np.where(cs < cs[j], base[j] - gmax * (cs[j] - cs), -1e9))
    z = zz
    j_join = next((j for j in range(len(cs)) if cs[j] > c_end and abs(z[j] - dflt[j]) < 0.01 and all(abs(z[k] - dflt[k]) < 0.01 for k in range(j, min(len(cs), j + 30)))), len(cs) - 1)
    c_join = cs[j_join]
    c_leave = next((cs[j] for j in range(len(cs)) if cs[j] <= c_end and z[j] > max(env[j], z_cw) + 0.05 and cs[j] > c_pe + 500), c_end)
    short = [(c, t - zz) for c, t, zz in zip(cs, target, z) if t > -1e8 and zz < t - MARGIN - 0.01]
    # stations north of Camp Washington: level platforms at the highest level over their length
    st_doc = {mp.st_key(i): round(float(mp.st[i]), 2) for i in range(len(mp.stations))}
    for i in range(i0 + 1, len(mp.stations)):
        c = mp.stations[i]['c']
        if c - half > c_join:
            continue                                     # past the tie: the default level
        m = (cs >= c - half) & (cs <= c + half)
        zs = float(z[m].max()) if m.any() else float(np.interp(c, cs, z))
        st_doc[mp.st_key(i)] = round(zs, 2)
        z[m] = zs
    # vertices: the editor's defaults south of the platform end, then ours (every change of grade, simplified)
    vc, vz = mp.vertices()
    pvi = [[round(float(c), 1), round(float(zz), 2)] for c, zz in zip(vc, vz) if c < c_cw - half - 1]
    after = [[round(float(c), 1), round(float(zz), 2)] for c, zz in zip(vc, vz) if c > c_join + 1]
    keep = [0]
    for j in range(1, j_join):
        g0 = (z[j] - z[keep[-1]]) / (cs[j] - cs[keep[-1]])
        g1 = (z[j + 1] - z[j]) / (cs[j + 1] - cs[j])
        if abs(g1 - g0) > 0.0005:
            keep.append(j)
    keep.append(j_join)
    pvi += [[round(float(cs[j]), 1), round(float(z[j]), 2)] for j in keep] + after
    doc = {'line': 'RER-4', 'system': 'Cincinnati RER', 'length_m': d4['length_m'], 'platform_m': mp.settings['platform'],
           'st': st_doc, 'sg': {}, 'so': {}, 'del': [], 'gapfill': [], 'pvi': pvi,
           'ovr': [[round(c_pe, 1), round(float(c_leave), 1), 'elevated']],
           'updated': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z'), 'v': 1,
           'note': ('Generated by tools/make_rer4_upper.py (Ben, 2026-10-27): north of the Camp Washington platform end D is tied to '
                    f'the Deck\'s APEx level, {CLEAR} m over the highest rail under it (crossing rule), climbing at {GRADE * 100:.1f}%, '
                    f'to {c_leave:.0f} m, then up at no more than the RER maximum grade to the editor\'s defaults by {c_join:.0f} m (D climbs on to Monfort '
                    f'Heights); elsewhere the editor\'s defaults. Not saved in the Rail Profiles editor.')}
    out = SITE / 'rer/alignments/RER_4.json'
    out.write_text(json.dumps(doc, indent=1))
    # check with the profile itself (vertical curves included)
    chk = MetroProfile.load(SITE / 'rer/lines/RER_4.json', out, SITE / 'rer/settings.json')
    rail = np.array([float(chk.rail_at(c)) for c in cs])
    lack = [(c, t - MARGIN - r) for c, t, r in zip(cs, target, rail) if t > -1e8 and r < t - MARGIN - 0.05]
    gr = np.diff(rail) / STEP * 1000
    print(f'max grade north of the platform end {np.abs(gr[cs[1:] <= c_join + 50]).max():.1f} per mille')
    print(f'RER-4 from {START} ({z_cw} m, platform end {c_pe:.0f} m); tied to the APEx level to {c_leave:.0f} m (Deck APEx level under D to {c_end:.0f} m), climbing at up to {gmax * 1000:.0f} per mille to its default profile at {c_join:.0f} m')
    for c in list(range(int(c_pe), int(c_join), 500)) + [int(c_end)]:
        j = int(np.argmin(np.abs(cs - c)))
        print(f'  c {cs[j]:>7.0f}  under {below[j] if below[j] > -1e8 else float("nan"):7.2f} ({src[j]})  rail {rail[j]:7.2f}  clear {rail[j] - below[j] if below[j] > -1e8 else float("nan"):5.2f}')
    print('stations:', {k: v for k, v in st_doc.items() if names.index(k.split('#')[0]) >= i0 if k.split('#')[0] in names})
    if lack:
        a, b = lack[0][0], lack[-1][0]
        print(f'short of {CLEAR} m over the rail below from {a:.0f} to {b:.0f} m ({sum(1 for _ in lack) * STEP:.0f} m in all), worst {max(v for _, v in lack):.2f} m')
    print('summary', chk.summary())


if __name__ == '__main__':
    main()
