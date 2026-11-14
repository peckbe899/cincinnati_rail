"""Guided reading, merge (13-14 November 2026): two guided reads of a plate -> controls and the plate's street points.

    cd data/sanborn
    python ../../tools/sanborn/guided/merge_guided.py N

Inputs in picks22_guided/22-N/ (each pass read twice, by readers A and B working apart):
  guide_A.json + A_*.json, B_*.json       crossings of today's streets (guide.py)
  trace.json + trace_A_*.json, trace_B_*  stations along today's streets (trace.py stations)
  ends.json + ends*_A_*.json, ends*_B_*   where each traced run of a street ends on the plate (trace.py ends)
  review.json + review_A_*, review_B_*    streets the drawing misses or gets wrong (review.py)
Every pass is optional except the crossings; a later pass adds to the earlier ones.

Rules, the same on every plate:
- A street is today's street id (streets.py), never a name: two streets the name key runs together stay apart.
- Crossing: both readers found it within 30 px -> a pick at the mean. Two of today's crossings at one plate point (within
  25 px) count once as a control; the others are drawn there but are not controls. Both found it more than 30 px apart:
  a jog, both points go into both streets (drawn), neither is a control.
- Screening of controls: a pick both readers marked "low" is not a control. Then, repeatedly, the pick that a thin-plate
  fit of all the others misses by most is taken out while it misses by more than 8 m; one missed by more than 20 m is
  not the crossing it was taken for and is not drawn either.
- Station: both found within 30 px -> a point on the street; both say not drawn -> a gap; they disagree -> left out
  (listed). A street's stations and crossings in order along it, split at the gaps, are its runs.
- Run ends: every end of a run is read (trace.py ends) unless the run ends at a crossing where today's street ends too.
  Both readers mark the end within 40 px -> the end point; both say it runs on -> the point where it leaves the crop is
  added and the next crop is read (rounds).
- Names: the plate's printed name for each run, taken from what the readers copied (two or more agreeing copies of a
  whole name), else the 1922 name from cufp/config.json "alias", else today's name.
- Review: a missing street both readers report (each reader's points within 40 px of the other's line) is added as a
  street of its own; a wrong line both report (within 80 px) is listed in merge.json for the next round.
Writes merge.json, controls.json and sbg/picks22/s22-N_<part>.json (rewritten: intersections, bends, ends, each point
carrying its street id; the earlier blind picks stay in picks22_reads/).
"""
import collections, glob, json, os, re, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import streets as S  # noqa: E402
from shapely.geometry import Point, LineString  # noqa: E402
from scipy.interpolate import RBFInterpolator  # noqa: E402
N = sys.argv[1]; SP = S.SP; D = SP + f'picks22_guided/22-{N}/'
P = S.Plate(N); ST = P.streets(); BY = {s['sid']: s for s in ST}
CFG = json.load(open(SP + 'cufp/config.json', encoding='utf8')).get(N, {})
ALIAS_1922 = {v: k for k, v in CFG.get('alias', {}).items()}           # today's name -> 1922 name
CTRL_M, WRONG_M, AGREE, END_AGREE, SAME_PT = 8.0, 20.0, 30.0, 40.0, 25.0

def reads(pattern):
    out = {}
    for f in sorted(glob.glob(D + pattern)):
        for r in json.load(open(f, encoding='utf-8-sig')): out[r['id']] = r
    return out
copied = []
def uncopy(R, items, who):
    """a reader who gives two items one point although the items lie more than 60 px apart on the plate copied it
    (some readers fill items they did not open from a neighbour): those reads count as not given"""
    pts = [(i, r) for i, r in R.items() if r.get('found', r.get('ends')) and 'x' in r and i in items]
    bad = set()
    for k, (i, a) in enumerate(pts):
        for j, b in pts[k + 1:]:
            if abs(a['x'] - b['x']) <= 2 and abs(a['y'] - b['y']) <= 2:
                pi, pj = items[i].get('pred'), items[j].get('pred')
                if pi and pj and np.hypot(pi[0] - pj[0], pi[1] - pj[1]) > 60: bad |= {i, j}
    for i in bad: copied.append(dict(read=who, id=i)); R.pop(i)
    return R
def pair(A, B, i, key='found'):
    a, b = A.get(i, {}), B.get(i, {})
    return bool(a.get(key)), bool(b.get(key)), a, b
def dist(a, b): return float(np.hypot(a['x'] - b['x'], a['y'] - b['y']))

# ---------------------------------------------------------------- crossings
G = {r['id']: r for r in json.load(open(D + 'guide_A.json', encoding='utf8'))}
RAW_A, RAW_B = reads('A_*.json'), reads('B_*.json')
CA, CB = uncopy(dict(RAW_A), G, 'A'), uncopy(dict(RAW_B), G, 'B')
# Ben's calls on low-confidence crossings (decisions.json: {id: "real" | "A" | "B" | "not"}): "real" = the readers' mean,
# "A"/"B" = that reader's point; either way a control that screening does not remove. "not" = not a control, not drawn.
DEC = json.load(open(D + 'decisions.json', encoding='utf8')) if os.path.exists(D + 'decisions.json') else {}
for g in G.values():
    g['sid_a'] = P.sid_at(ST, g['a'], g['E'], g['N']); g['sid_b'] = P.sid_at(ST, g['b'], g['E'], g['N'])
picks, street_only, jogs = [], [], []
for i, g in G.items():
    d = DEC.get(i)
    if d == 'not': continue
    if d in ('real', 'A', 'B'):
        qs = [r for k, r in (('A', RAW_A.get(i, {})), ('B', RAW_B.get(i, {}))) if r.get('found') and 'x' in r and d in ('real', k)]
        if qs:
            x, y = float(np.mean([q['x'] for q in qs])), float(np.mean([q['y'] for q in qs]))
            picks.append(dict(id=i, a=g['a'], b=g['b'], sid_a=g['sid_a'], sid_b=g['sid_b'], x=x, y=y, E=g['E'], N=g['N'], apart_px=0.0,
                              both_low=False, ben=d, printed={g['sid_a']: [qs[0].get('name_a_printed', '')], g['sid_b']: [qs[0].get('name_b_printed', '')]}))
            continue
    fa, fb, a, b = pair(CA, CB, i)
    if not (fa and fb): continue
    if dist(a, b) > AGREE:
        jogs.append(i)
        for q in (a, b): street_only.append(dict(id=i, x=q['x'], y=q['y'], sids=[g['sid_a'], g['sid_b']], why='jog: the readers took different legs'))
        continue
    x, y = (a['x'] + b['x']) / 2, (a['y'] + b['y']) / 2
    first = next((p for p in picks if np.hypot(x - p['x'], y - p['y']) < SAME_PT), None)
    rec = dict(id=i, a=g['a'], b=g['b'], sid_a=g['sid_a'], sid_b=g['sid_b'], x=x, y=y, E=g['E'], N=g['N'], apart_px=round(dist(a, b), 1),
               both_low=a.get('sure') == 'low' and b.get('sure') == 'low', printed={g['sid_a']: [a.get('name_a_printed', ''), b.get('name_a_printed', '')], g['sid_b']: [a.get('name_b_printed', ''), b.get('name_b_printed', '')]})
    if first: rec['same_point_as'] = first['id']
    picks.append(rec)

# screening
def tps_fit(X, O):
    A_ = np.c_[X / 1000, np.ones(len(X))]; C = np.linalg.lstsq(A_, O, rcond=None)[0]
    rb = RBFInterpolator(X / 1000, O - A_ @ C, kernel='thin_plate_spline', smoothing=1.0, degree=1)
    return lambda q: np.c_[q / 1000, np.ones(len(q))] @ C + rb(q / 1000)
cand = [p for p in picks if 'same_point_as' not in p and not p['both_low']]
screened = []
while len(cand) > 8:
    X = np.array([[p['x'], p['y']] for p in cand]); O = np.array([[p['E'], p['N']] for p in cand]); e = np.zeros(len(cand))
    for k in range(len(cand)):
        if cand[k].get('ben'): continue                  # Ben's call stands
        m = np.ones(len(cand), bool); m[k] = False; e[k] = np.hypot(*(tps_fit(X[m], O[m])(X[k:k + 1])[0] - O[k]))
    w = int(np.argmax(e))
    if e[w] <= CTRL_M: break
    screened.append(dict(id=cand[w]['id'], a=cand[w]['a'], b=cand[w]['b'], heldout_m=round(float(e[w]), 1))); cand.pop(w)
F = tps_fit(np.array([[p['x'], p['y']] for p in cand]), np.array([[p['E'], p['N']] for p in cand]))
ctrl_ids = {p['id'] for p in cand}
for p in picks:
    p['control'] = p['id'] in ctrl_ids
    p['miss_m'] = round(float(np.hypot(*(F(np.array([[p['x'], p['y']]]))[0] - [p['E'], p['N']]))), 1)
    p['drawn'] = p['control'] or p['miss_m'] <= WRONG_M
    if p['both_low'] and p['miss_m'] > WRONG_M: p['drawn'] = False

# bins: every crossing a reader found is HIGH (a control on its own) or LOW (with why), for Ben to call (decisions.json)
PK = {p['id']: p for p in picks}; COPIED = {c['id'] for c in copied}; bins = []
for i, g in G.items():
    a, b = RAW_A.get(i, {}), RAW_B.get(i, {})
    fa, fb = bool(a.get('found') and 'x' in a), bool(b.get('found') and 'x' in b)
    if not (fa or fb): continue
    p = PK.get(i); row = dict(id=i, a=g['a'], b=g['b'], A=[a['x'], a['y'], a.get('sure')] if fa else None,
                              B=[b['x'], b['y'], b.get('sure')] if fb else None, ben=DEC.get(i))
    if p and p.get('same_point_as'): continue           # follows the crossing at the same point
    if p and p['control']: row.update(bin='high' if not p.get('ben') else 'ben', why='')
    elif p and p['both_low']: row.update(bin='low', why=f"both readers 'low' ({p['apart_px']} px apart)")
    elif p: row.update(bin='low', why=f"screened: the fit of the others misses it by {p['miss_m']} m")
    elif i in COPIED: row.update(bin='low', why='copy check: a reader gave this point to another item too')
    elif fa and fb: row.update(bin='low', why=f'readers {round(dist(a, b))} px apart')
    else: row.update(bin='low', why='only reader ' + ('A' if fa else 'B') + ' found it; the other: ' + ((b if fa else a).get('note', '') or '')[:80])
    if DEC.get(i) == 'not': row['bin'] = 'ben'
    bins.append(row)
json.dump(bins, open(D + 'bins.json', 'w', encoding='utf8', newline='\n'), indent=1)
print('bins: high', sum(r['bin'] == 'high' for r in bins), 'low', sum(r['bin'] == 'low' for r in bins), 'decided', sum(r['bin'] == 'ben' for r in bins))

# ---------------------------------------------------------------- stations, runs
T = {r['id']: r for r in json.load(open(D + 'trace.json', encoding='utf8'))} if os.path.exists(D + 'trace.json') else {}
TA, TB = uncopy(reads('trace_A_*.json'), T, 'trace A'), uncopy(reads('trace_B_*.json'), T, 'trace B')
seq = collections.defaultdict(list); disputed = []
for i, r in T.items():
    if i not in TA or i not in TB: continue
    fa, fb, a, b = pair(TA, TB, i)
    if fa and fb and dist(a, b) <= AGREE:
        seq[r['sid']].append(dict(t=r['t'], kind='station', x=(a['x'] + b['x']) / 2, y=(a['y'] + b['y']) / 2, printed=[a.get('printed', ''), b.get('printed', '')], id=i))
    elif not fa and not fb:
        seq[r['sid']].append(dict(t=r['t'], kind='gap', id=i))
    else:
        disputed.append(dict(id=i, sid=r['sid'], name=r['name'], A=[a.get('x'), a.get('y')] if fa else a.get('note', ''), B=[b.get('x'), b.get('y')] if fb else b.get('note', '')))
for p in picks:
    if not p['drawn']: continue
    for s in ('sid_a', 'sid_b'):
        if p[s] and p[s] in BY:
            seq[p[s]].append(dict(t=BY[p[s]]['geom'].project(Point(p['E'], p['N'])), kind='crossing', x=p['x'], y=p['y'], printed=p['printed'].get(p[s], []), id=p['id']))
for q in street_only:
    for s in q['sids']:
        if s and s in BY: seq[s].append(dict(t=BY[s]['geom'].project(Point(*P.world([[q['x'], q['y']]])[0])), kind='jog', x=q['x'], y=q['y'], printed=[], id=q['id']))
runs = []
for sid, items in seq.items():
    items.sort(key=lambda z: z['t']); cur = []
    groups = []
    for z in items:
        if z['kind'] == 'gap':
            if cur: groups.append(cur); cur = []
        else: cur.append(z)
    if cur: groups.append(cur)
    L = BY[sid]['geom'].length
    for k, grp in enumerate(groups, 1):
        def open_(z, at_end):
            today_end = (z['t'] < 20) if not at_end else (z['t'] > L - 20)
            return not (z['kind'] == 'crossing' and today_end)
        runs.append(dict(sid=sid, run=k, rid=f'{sid}/{k}', name=BY[sid]['name'], t=[round(z['t'], 1) for z in grp], points=[[round(z['x'], 1), round(z['y'], 1)] for z in grp],
                         printed=[s for z in grp for s in z.get('printed', []) if s], start_open=open_(grp[0], False), end_open=open_(grp[-1], True), start=None, end=None))

# ---------------------------------------------------------------- run ends (rounds)
E = json.load(open(D + 'ends.json', encoding='utf8')) if os.path.exists(D + 'ends.json') else []
EA, EB = reads('ends*_A_*.json'), reads('ends*_B_*.json')
RUN = {r['rid']: r for r in runs}; end_log = []
for e in sorted(E, key=lambda z: z.get('round', 1)):
    r = RUN.get(f"{e['sid']}/{e['run']}")
    if r is None or e['id'] not in EA or e['id'] not in EB: continue
    a, b = EA[e['id']], EB[e['id']]
    if 'x' not in a or 'x' not in b: end_log.append(dict(id=e['id'], rid=r['rid'], result='no point')); continue
    d = dist(a, b); pt = [round((a['x'] + b['x']) / 2, 1), round((a['y'] + b['y']) / 2, 1)]
    if a.get('ends') and b.get('ends') and d <= END_AGREE:
        r[e['side']] = dict(x=pt[0], y=pt[1], at=a.get('at', ''), id=e['id']); res = 'ends'
    elif not a.get('ends') and not b.get('ends') and d <= 2 * END_AGREE:
        # a reader who "follows on" may have turned onto another street, or back along this one: stop there
        own = r['points'][1:] if e['side'] == 'end' else r['points'][:-1]
        other = [(LineString(q['points']).distance(Point(pt)), q) for q in runs if q['sid'] != r['sid'] and len(q['points']) > 1]
        near = min(other, key=lambda z: z[0]) if other else (1e9, None)
        if len(own) > 1 and LineString(own).distance(Point(pt)) < 35:
            res = 'back along itself'
        elif near[0] < 35:
            j = LineString(near[1]['points']).interpolate(LineString(near[1]['points']).project(Point(pt)))
            r[e['side']] = dict(x=round(j.x, 1), y=round(j.y, 1), at='runs into ' + near[1]['name'], id=e['id']); res = 'joins ' + near[1]['rid']
        else:
            if e['side'] == 'end': r['points'].append(pt)
            else: r['points'].insert(0, pt)
            r[e['side'] + '_more'] = pt; res = 'runs on'
    else: res = 'readers disagree'
    for q in (a, b):
        if q.get('printed'): r['printed'].append(q['printed'])
    end_log.append(dict(id=e['id'], rid=r['rid'], side=e['side'], result=res, apart_px=round(d, 1)))

# one printed street that is two of today's streets (Ross Avenue east of Imwalle is Tennessee Avenue today): the shorter
# run that lies along the longer one is the same street, and is dropped
dups = []
for r in sorted(runs, key=lambda z: len(z['points'])):
    if len(r['points']) < 2: continue
    for q in runs:
        if q is r or q['sid'] == r['sid'] or q.get('dup_of') or len(q['points']) < len(r['points']) or len(q['points']) < 2: continue
        lq = LineString(q['points'])
        if np.mean([lq.distance(Point(p)) < 35 for p in r['points']]) >= 0.8:
            r['dup_of'] = q['rid']; dups.append(dict(rid=r['rid'], name=r['name'], same_as=q['rid'])); break
runs = [r for r in runs if not r.get('dup_of')]

# ---------------------------------------------------------------- review: streets the drawing misses
RV = {}
for R in 'AB':
    for f in sorted(glob.glob(D + f'review_{R}_*.json')):
        d_ = json.load(open(f, encoding='utf-8-sig')); RV.setdefault(R, dict(missing=[], wrong=[]))
        RV[R]['missing'] += d_.get('missing', []); RV[R]['wrong'] += d_.get('wrong', [])
added, wrong = [], []
if 'A' in RV and 'B' in RV:
    used = set()
    for m in RV['A']['missing']:
        if len(m.get('points', [])) < 2: continue
        la = LineString(m['points'])
        for j, n in enumerate(RV['B']['missing']):
            if j in used or len(n.get('points', [])) < 2: continue
            lb = LineString(n['points'])
            ina = [q for q in m['points'] if lb.distance(Point(q)) <= END_AGREE]; inb = [q for q in n['points'] if la.distance(Point(q)) <= END_AGREE]
            if len(ina) >= 2 and len(inb) >= 2 and len(ina) >= 0.5 * len(m['points']) and len(inb) >= 0.5 * len(n['points']):   # both readers place it; the stretch both report
                used.add(j); pts = sorted(ina + inb, key=lambda q: la.project(Point(q)))
                added.append(dict(printed=[m.get('printed', ''), n.get('printed', '')], points=pts, start_at=m.get('start_at', ''), end_at=m.get('end_at', ''))); break
    for w in RV['A']['wrong']:
        if any(np.hypot(w['x'] - v['x'], w['y'] - v['y']) <= 80 for v in RV['B']['wrong']): wrong.append(w)

# ---------------------------------------------------------------- names
SUF = {'ST': 'Street', 'STR': 'Street', 'STREET': 'Street', 'AV': 'Avenue', 'AVE': 'Avenue', 'AVENUE': 'Avenue', 'PL': 'Place', 'PLACE': 'Place',
       'LN': 'Lane', 'LANE': 'Lane', 'RD': 'Road', 'ROAD': 'Road', 'CT': 'Court', 'COURT': 'Court', 'TER': 'Terrace', 'TERRACE': 'Terrace', 'DR': 'Drive', 'DRIVE': 'Drive', 'AL': 'Alley', 'ALLEY': 'Alley'}
def clean(s):
    if not s or '..' in s or '…' in s or re.search(r'partial|\bcut\b|illegib|\?', s, re.I): return None     # the reader marked the name as not whole
    s = re.sub(r'[^A-Za-z\' ]', ' ', s or '').split()
    if not s or any(len(w) < 2 for w in s[:1]): return None
    w = [x.upper() for x in s]; suf = SUF.get(w[-1]) if len(w) > 1 else None
    core = w[:-1] if suf else w
    if not core or len(''.join(core)) < 3: return None
    return ' '.join(c.capitalize() for c in core) + (' ' + suf if suf else '')
def name_for(today, printed):
    tw = today.split(); tcore = ' '.join(tw[:-1] if len(tw) > 1 and tw[-1] in SUF.values() else tw).lower()
    for pre in ('east ', 'west ', 'north ', 'south '):
        if tcore.startswith(pre): tcore = tcore[len(pre):]
    refs = [tcore]
    if today in ALIAS_1922:
        aw = ALIAS_1922[today].split(); refs.append(' '.join(aw[:-1] if len(aw) > 1 and aw[-1] in SUF.values() else aw).lower())
    def whole(n):                       # a printed name cut by the crop or the plate is not a name: ORCHAR, ROSE of Rose Hill, CARTHA of Carthage, WICK of Warwick
        w = n.split(); core = ' '.join(w[:-1] if len(w) > 1 and w[-1] in SUF.values() else w).lower()
        if not core or core.split()[0] in [v.lower() for v in SUF.values()]: return False
        return not any(core != ref and (ref.startswith(core) or ref.endswith(core)) for ref in refs)
    c = collections.Counter(x for x in (clean(s) for s in printed) if x and whole(x))
    best = [n for n, k in c.most_common() if k >= 2]
    if best:
        n = best[0]
        if len(n.split()) == 1 or n.split()[-1] not in SUF.values():   # no suffix printed: the 1922 alias's if it is this name, else today's
            if today in ALIAS_1922 and n.lower() == refs[-1]: return ALIAS_1922[today], 'printed'
            n = n + ' ' + (today.split()[-1] if today.split()[-1] in SUF.values() else 'Street')
        return n, 'printed'
    if today in ALIAS_1922: return ALIAS_1922[today], 'alias'
    return today, 'today'
for r in runs: r['name_1922'], r['name_from'] = name_for(r['name'], r['printed'])
# a wrong line both reviewers report: the traced points of the nearest run within 80 px of it are taken out (the crossings
# stay), and an end read there is dropped; the line then stops at the next point both readers placed on a printed street
for w in wrong:
    near = min(runs, key=lambda r: LineString(r['points']).distance(Point(w['x'], w['y'])) if len(r['points']) > 1 else 1e9, default=None)
    if near is None or len(near['points']) < 2 or LineString(near['points']).distance(Point(w['x'], w['y'])) > 80: w['action'] = 'no run near'; continue
    keep = [q for q in near['points'] if np.hypot(q[0] - w['x'], q[1] - w['y']) > 80]
    if len(keep) == len(near['points']):          # no point near: the wrong stretch is the segment between two points; the run is cut there
        pts = near['points']; i = int(np.argmin([LineString([pts[k], pts[k + 1]]).distance(Point(w['x'], w['y'])) for k in range(len(pts) - 1)]))
        tail = dict(near, run=f"{near['run']}b", rid=near['rid'] + 'b', points=pts[i + 1:], start=None); near['points'] = pts[:i + 1]; near['end'] = None
        runs.append(tail); w['action'] = f"{near['rid']} cut between points {i} and {i + 1}"; continue
    if len(keep) >= 2:
        w['action'] = f"{len(near['points']) - len(keep)} points taken out of {near['rid']}"; near['points'] = keep
        for side in ('start', 'end'):
            if near[side] and np.hypot(near[side]['x'] - w['x'], near[side]['y'] - w['y']) <= 120: near[side] = None
    else: w['action'] = 'left: the run would be gone'
# a missing stretch that carries on from the end of a traced run (Mitchell west to Carthage) extends that run
def same_name(a, r):                 # an unnamed stretch, or one whose printed name is this run's
    ns = [x for x in (clean(s_) for s_ in a['printed']) if x]
    if not ns: return True
    cores = {' '.join(w for w in n.lower().split() if w.capitalize() not in SUF.values()) for n in ns}
    rn = {' '.join(w for w in v.lower().split() if w.capitalize() not in SUF.values() and w not in ('east', 'west', 'north', 'south')) for v in (r['name'], r['name_1922'])}
    return bool(cores & rn)
for a in added:                       # already traced: both readers saw a line missing that the build had cut off (a build fault, listed), not a missing street
    for r in runs:
        if len(r['points']) > 1 and np.mean([LineString(r['points']).distance(Point(q)) < 35 for q in a['points']]) >= 0.8 and same_name(a, r):
            a['extends'] = r['rid']; a['already_traced'] = True; break
for a in added:
    if a.get('extends'): continue
    best = None
    for r in runs:
        if not same_name(a, r): continue
        for side, q in (('start', r['points'][0]), ('end', r['points'][-1])):
            for which, p in (('first', a['points'][0]), ('last', a['points'][-1])):
                d_ = np.hypot(q[0] - p[0], q[1] - p[1])
                if d_ <= 80 and (best is None or d_ < best[0]): best = (d_, r, side, which)
    if best:
        _, r, side, which = best; pts = a['points'] if which == 'first' else a['points'][::-1]
        if side == 'end': r['points'] += pts
        else: r['points'] = pts[::-1] + r['points']
        r[side] = None; a['extends'] = r['rid']
review_used = [dict(printed=a['printed'], into=a['extends'], already_traced=a.get('already_traced', False)) for a in added if a.get('extends')]
added = [a for a in added if not a.get('extends')]
for k, a in enumerate(added, 1):
    ns = [x for x in (clean(s) for s in a['printed']) if x]
    n = max(ns, key=lambda x: (x.split()[-1] in SUF.values(), len(x))) if ns else None     # the fullest printed form
    a['sid'] = 'r-' + (S.slug(n) if n else 'unnamed') + f'#{k}'; a['name_1922'] = n or ''
RUNNAME = {}
for r in runs: RUNNAME.setdefault(r['sid'], []).append(r)
def run_of(sid, x, y):
    rs = RUNNAME.get(sid, [])
    if not rs: return None
    return min(rs, key=lambda r: min(np.hypot(x - q[0], y - q[1]) for q in r['points']))

# ---------------------------------------------------------------- write
strips = json.load(open(SP + 'cufp/strips.json'))[N]
OUTP = {k: dict(sheet=f'22-{N}', part=k, strip=list(b), intersections=[], bends=[], ends=[], source='guided (tools/sanborn/guided/merge_guided.py)') for k, b in enumerate(strips, 1)}
def part_of(x): return next((k for k, b in enumerate(strips, 1) if b[0] <= x < b[2]), len(strips))
for p in picks:
    if not p['drawn']: continue
    ra, rb = run_of(p['sid_a'], p['x'], p['y']), run_of(p['sid_b'], p['x'], p['y'])
    OUTP[part_of(p['x'])]['intersections'].append(dict(a=ra['name_1922'] if ra else p['a'], b=rb['name_1922'] if rb else p['b'], osm_a=p['a'], osm_b=p['b'],
        sid_a=ra['rid'] if ra else p['sid_a'], sid_b=rb['rid'] if rb else p['sid_b'], x=round(p['x'], 1), y=round(p['y'], 1), kind='guided', id=p['id'], fit=p['control']))
for r in runs:
    for q in r['points']: OUTP[part_of(q[0])]['bends'].append(dict(street=r['name_1922'], sid=r['rid'], x=q[0], y=q[1], kind='traced'))
    for side in ('start', 'end'):
        if r[side]: OUTP[part_of(r[side]['x'])]['ends'].append(dict(street=r['name_1922'], sid=r['rid'], x=r[side]['x'], y=r[side]['y'], note=r[side]['at'], kind='read'))
for a in added:
    for q in a['points']: OUTP[part_of(q[0])]['bends'].append(dict(street=a['name_1922'], sid=a['sid'], x=q[0], y=q[1], kind='review'))
for k, d_ in OUTP.items():
    json.dump(d_, open(SP + f'sbg/picks22/s22-{N}_{k}.json', 'w', encoding='utf8', newline='\n'), indent=1)
ctrl = [p for p in picks if p['control']]
json.dump([dict(id=p['id'], a=p['a'], b=p['b'], x=p['x'], y=p['y'], E=p['E'], N=p['N']) for p in ctrl], open(D + 'controls.json', 'w', encoding='utf8', newline='\n'), indent=1)
d = np.array([dist(CA[i], CB[i]) for i in G if pair(CA, CB, i)[0] and pair(CA, CB, i)[1]])
rep = dict(sheet=f'22-{N}', crossings=len(G), found_both=len(d), same_verdict=sum(pair(CA, CB, i)[0] == pair(CA, CB, i)[1] for i in G),
           apart_px=dict(median=round(float(np.median(d)), 1), p90=round(float(np.percentile(d, 90)), 1)), picks=len(picks), controls=len(ctrl),
           screened=screened, not_drawn=[dict(id=p['id'], a=p['a'], b=p['b'], miss_m=p['miss_m']) for p in picks if not p['drawn']], jogs=jogs,
           stations=len(T), stations_read=sum(1 for i in T if i in TA and i in TB), stations_disputed=disputed,
           runs=[{k: v for k, v in r.items()} for r in runs], ends_read=end_log,
           copied_reads=copied, duplicate_runs=dups, review_extended=review_used, review_added=added, review_wrong=wrong)
json.dump(rep, open(D + 'merge.json', 'w', encoding='utf8', newline='\n'), indent=1)
print(json.dumps(dict(crossings=len(G), picks=len(picks), controls=len(ctrl), screened=len(screened), not_drawn=len(rep['not_drawn']), jogs=len(jogs),
                      stations=len(T), stations_read=rep['stations_read'], disputed=len(disputed), runs=len(runs),
                      open_ends=sum(r['start_open'] and not r['start'] for r in runs) + sum(r['end_open'] and not r['end'] for r in runs),
                      ends_read=len(end_log), review_added=len(added), review_wrong=len(wrong))))
