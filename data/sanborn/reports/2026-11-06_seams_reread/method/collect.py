"""Collate the two reads of each tie crossing, write data/sanborn/picks22_reread/<plate>/, classify the 15 ties.
Overrides (verdict corrections after looking at the reads' notes) come from overrides.json beside this script."""
import glob, json, os, re, sys
import numpy as np

REPO = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D'
sys.path.insert(0, REPO + '/tools/sanborn')
import _ws, seams as S  # noqa
SP = _ws.DATA
HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(HERE + '/ties15.json', encoding='utf8'))
M = json.load(open(HERE + '/regions.json', encoding='utf8'))
G = json.load(open(HERE + '/groups.json', encoding='utf8'))
OV = json.load(open(HERE + '/overrides.json', encoding='utf8')) if os.path.exists(HERE + '/overrides.json') else {}
R = {}
for g in G:
    for r in (1, 2):
        for q in json.load(open(f'{HERE}/reads/{g}r{r}.json', encoding='utf8')):
            R.setdefault(q['job'], {})[f'read{r}'] = dict(q, reader=f'{g}r{r}')
W = {p: S.plate_world(p) for p in S.plate_ids()}
MOVE, AGREE, REAL = 5.0, 5.0, 10.0
slug = lambda s: re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')

out_rows = []
for e in T:
    pa, pb = list(e['plates'])
    side = {}
    for p in (pa, pb):
        job = f"t{e['n']:02d}_{p[3:]}"
        d = e['plates'][p]; rr = R[job]; reads = [rr['read1'], rr['read2']]
        found = [q for q in reads if q.get('found') and q.get('x') is not None]
        new = None; spread = None
        if len(found) == 2:
            spread = float(np.hypot(found[0]['x'] - found[1]['x'], found[0]['y'] - found[1]['y']))
            if spread <= S.DUP_PX:
                new = [float(np.mean([q['x'] for q in found])), float(np.mean([q['y'] for q in found]))]
        elif len(found) == 1:
            new = [float(found[0]['x']), float(found[0]['y'])]
        ov = OV.get(job, {})
        if 'new_pick' in ov:
            new = ov['new_pick']
        o = d['old_pick']
        rec = dict(crossing=f"{e['street_1']} & {e['street_2']}", plate=p, tie=e['n'], tie_plates=e['tie'], job=job,
                   reads=reads, two_reads_spread_px=None if spread is None else round(spread, 1),
                   new_pick=None, old_pick=dict(x=o['x'], y=o['y'], E=o['E'], N=o['N'], names=o['names'], reads=d['reads']),
                   osm_match=d['osm_match'], note=ov.get('note'))
        if new is not None:
            E, N = W[p](*new)
            rec['new_pick'] = dict(x=round(new[0], 1), y=round(new[1], 1), E=round(E, 2), N=round(N, 2),
                                   moved_px=round(float(np.hypot(new[0] - o['x'], new[1] - o['y'])), 1),
                                   moved_m=round(float(np.hypot(E - o['E'], N - o['N'])), 2))
        osm = [(q['E'], q['N']) for q in (e['osm_same_names'] or [])]
        rec['osm_crossings_of_these_names'] = [dict(E=q[0], N=q[1], from_old_m=round(float(np.hypot(q[0] - o['E'], q[1] - o['N'])), 1),
                                                   from_new_m=None if not rec['new_pick'] else round(float(np.hypot(q[0] - rec['new_pick']['E'], q[1] - rec['new_pick']['N'])), 1)) for q in osm]
        side[p] = rec
        folder = SP + f'picks22_reread/{p}'; os.makedirs(folder, exist_ok=True)
        json.dump(rec, open(f"{folder}/t{e['n']:02d}_{slug(e['street_1'])}__{slug(e['street_2'])}.json", 'w', encoding='utf8', newline='\n'), indent=1)
    A, B = side[pa], side[pb]
    pos = lambda r, k: np.array([r[k]['E'], r[k]['N']]) if r[k] else None
    Ao, Bo, An, Bn = pos(A, 'old_pick'), pos(B, 'old_pick'), pos(A, 'new_pick'), pos(B, 'new_pick')
    d_old = float(np.hypot(*(Ao - Bo)))
    d_new = float(np.hypot(*(An - Bn))) if An is not None and Bn is not None else None
    mA = A['new_pick']['moved_m'] if A['new_pick'] else None; mB = B['new_pick']['moved_m'] if B['new_pick'] else None
    v = dict(n=e['n'], tie=e['tie'], crossing=f"{e['street_1']} & {e['street_2']}", seam_old_m=round(d_old, 2),
             seam_reread_m=None if d_new is None else round(d_new, 2), moved_m={pa: mA, pb: mB},
             osm_same_names_within_150m=[q for q in (e['osm_same_names'] or []) if q['d_m'] <= 150],
             readers_same_names_elsewhere={p: [x for r in side[p]['reads'] for x in (r.get('same_names_elsewhere') or [])] for p in (pa, pb)})
    if d_new is None:
        cls, why = 'unresolved', 'a crossing was not found, or the two reads differ by more than 60 px'
    elif d_new <= AGREE and max(mA, mB) > MOVE and min(mA, mB) <= MOVE:
        bad = pa if mA > mB else pb
        cls, why = 'a', f'mis-pick on {bad}: its new read moved {max(mA, mB):.1f} m and now agrees with {pb if bad == pa else pa} within {d_new:.1f} m'
        v['mispick_plate'] = bad
    elif mA <= MOVE and mB <= MOVE and d_new > REAL:
        cls, why = 'c', f'both reads stand (moved {mA:.1f} and {mB:.1f} m) and still differ by {d_new:.1f} m'
    else:
        cls, why = 'unresolved', f'after the re-read {d_new:.1f} m apart; moves {mA:.1f} / {mB:.1f} m'
    tov = OV.get(f"t{e['n']:02d}", {})
    if 'class' in tov:
        cls, why = tov['class'], tov['why']
        if 'mispick_plate' in tov: v['mispick_plate'] = tov['mispick_plate']
    v.update(verdict=cls, why=why)
    out_rows.append(v)
json.dump(out_rows, open(HERE + '/verdicts.json', 'w', encoding='utf8', newline='\n'), indent=1)
for v in out_rows:
    print(f"{v['n']:2d} {v['tie']:17s} {v['crossing']:38s} old {v['seam_old_m']:6.2f}  reread {v['seam_reread_m']}  moved {v['moved_m']}  -> ({v['verdict']}) {v['why']}")
