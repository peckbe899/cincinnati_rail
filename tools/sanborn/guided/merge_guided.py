"""Guided reading, step 2: two guided reads of every crossing on today's map (guide.py) -> picks.

    cd data/sanborn
    python ../../tools/sanborn/guided/merge_guided.py N

Reads picks22_guided/22-N/guide_A.json (the crossings, with today's names and positions) and the readers' files
A_*.json and B_*.json. A crossing is a pick when both readers found it and their points are within 30 px; the pick is
the mean. Two of today's crossings read at one plate point (within 25 px) count once. Writes picks22_guided/22-N/merge.json
and controls.json, and puts the picks into sbg/picks22/s22-N_<part>.json: an earlier pick within 90 px of a guided pick
is replaced by it, earlier picks with no guided pick stay for the street set (crossings that exist only in 1922) but are marked
"fit": false, so cufp/fit.py does not use them as controls. A guided pick carries
today's names, turned back into the 1922 name where cufp/config.json has an alias for the plate.
"""
import glob, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import _ws  # noqa: E402
SP = _ws.DATA; N = sys.argv[1]; D = SP + f'picks22_guided/22-{N}/'
G = {r['id']: r for r in json.load(open(D + 'guide_A.json'))}
def load(R):
    out = {}
    for f in sorted(glob.glob(D + f'{R}_*.json')):
        for r in json.load(open(f, encoding='utf-8-sig')): out[r['id']] = r
    return out
A, B = load('A'), load('B')
fa = lambda R, i: bool(R.get(i, {}).get('found'))
both = [i for i in G if fa(A, i) and fa(B, i)]
apart = {i: float(np.hypot(A[i]['x'] - B[i]['x'], A[i]['y'] - B[i]['y'])) for i in both}
_drop = json.load(open(SP + 'cufp/config.json', encoding='utf8'))[N].get('guided_drop', {})      # {id: why}: both readers marked a point, but it is not this crossing
ok = [i for i in both if apart[i] <= 30 and i not in _drop]
picks, same = [], []                     # same: another of today's crossings at a plate point already taken (Tower and Glencross both meet Mitchell at one point): drawn, not a second control
for i in ok:
    x, y = (A[i]['x'] + B[i]['x']) / 2, (A[i]['y'] + B[i]['y']) / 2
    first = next((p for p in picks if np.hypot(x - p['x'], y - p['y']) < 25), None)
    if first: same.append(dict(id=i, a=G[i]['a'], b=G[i]['b'], x=first['x'], y=first['y'], dup=True)); continue
    picks.append(dict(id=i, a=G[i]['a'], b=G[i]['b'], x=x, y=y, E=G[i]['E'], N=G[i]['N'], apart_px=round(apart[i], 1)))
_cfg = json.load(open(SP + 'cufp/config.json', encoding='utf8'))[N]
rev = {v: k for k, v in _cfg.get('alias', {}).items()}; rev.update(_cfg.get('names_1922', {}))    # today's name -> the plate's name
d = np.array([apart[i] for i in both])
rep = dict(sheet=f'22-{N}', crossings=len(G), found_A=sum(fa(A, i) for i in G), found_B=sum(fa(B, i) for i in G), found_both=len(both),
           same_verdict=sum(fa(A, i) == fa(B, i) for i in G), apart_px=dict(median=round(float(np.median(d)), 1), p90=round(float(np.percentile(d, 90)), 1), max=round(float(d.max()), 1)),
           picks=len(picks), apart_over_30=[dict(id=i, a=G[i]['a'], b=G[i]['b'], A=[A[i]['x'], A[i]['y']], B=[B[i]['x'], B[i]['y']], note_A=A[i].get('note', ''), note_B=B[i].get('note', '')) for i in both if apart[i] > 30],
           one_reader_only=[dict(id=i, a=G[i]['a'], b=G[i]['b'], found_by='A' if fa(A, i) else 'B') for i in G if fa(A, i) != fa(B, i)],
           not_drawn=[dict(id=i, a=G[i]['a'], b=G[i]['b'], note_A=A.get(i, {}).get('note', ''), note_B=B.get(i, {}).get('note', '')) for i in G if not fa(A, i) and not fa(B, i)])
json.dump(rep, open(D + 'merge.json', 'w', encoding='utf8', newline='\n'), indent=1)
json.dump(picks, open(D + 'controls.json', 'w', encoding='utf8', newline='\n'), indent=1)
strips = json.load(open(SP + 'cufp/strips.json'))[N]; replaced = kept = 0
for k, (x0, y0, x1, y1) in enumerate(strips, 1):
    fn = SP + f'sbg/picks22/s22-{N}_{k}.json'
    dd = json.load(open(fn, encoding='utf8')) if os.path.exists(fn) else dict(sheet=f'22-{N}', part=k, strip=[x0, y0, x1, y1], intersections=[])
    old = [p for p in dd.get('intersections', []) if p.get('kind') != 'guided']
    old = [p for p in old if p.get('kind') != 'added']
    keep = [p for p in old if not any(np.hypot(p['x'] - q['x'], p['y'] - q['y']) < 90 for q in picks)]
    replaced += len(old) - len(keep); kept += len(keep)
    mine = [dict(a=rev.get(q['a'], q['a']), b=rev.get(q['b'], q['b']), x=round(q['x'], 1), y=round(q['y'], 1), kind='guided', id=q['id'], **({'fit': False} if q.get('dup') else {})) for q in picks + same if x0 <= q['x'] < x1]
    for p in mine:                            # cufp/config.json "guided_not_controls": {id: why}: drawn as a street crossing, not used to place the plate
        if p['id'] in _cfg.get('guided_not_controls', {}): p['fit'] = False
    for p in keep: p['fit'] = False            # earlier blind picks: kept for the street set, not controls (cufp/fit.py skips them)
    more = [dict(a=e['a'], b=e['b'], x=e['x'], y=e['y'], kind='added', fit=False, why=e.get('why', '')) for e in _cfg.get('extra_picks', []) if x0 <= e['x'] < x1]   # cufp/config.json "extra_picks": crossings read off the plate by hand for the street set only
    dd['ends'] = [e for e in dd.get('ends', []) if e.get('kind') != 'added'] + [dict(street=e['street'], x=e['x'], y=e['y'], kind='added', note=e.get('why', '')) for e in _cfg.get('extra_ends', []) if x0 <= e['x'] < x1]
    dd['intersections'] = keep + mine + more
    json.dump(dd, open(fn, 'w', encoding='utf8', newline='\n'), indent=1)
print(json.dumps({k: v for k, v in rep.items() if not isinstance(v, list)}), '| earlier picks replaced', replaced, 'kept', kept)
