"""House-number checks by code, tested on numbers read by eye (data/house_numbers.json).

Checks, for every label (a printed number or range) on one side of one street:
  format     the text is digits with '-' joins; short parts (12, 08) take their leading digits from the label head
             or, for a label printed alone, from the nearest full number on that side
  parity     odd on one side, even on the other (majority of the side's other labels, leave-one-out)
  order      numbers rise or fall steadily along the side, between cross streets (neighbours on each side)
  fit        robust straight line number = a + b*s through the segment's OTHER labels (s = feet along the street);
             the label must lie within TAU_FIT numbers of it
  hundred    a segment between cross streets keeps one hundred (or crosses one boundary in order)
  across     the opposite side at the same s (its own robust fit) differs by at most TAU_ACROSS
  join       where a side crosses a cross street (or a plate edge) the numbers continue at the same rate,
             or restart at the next hundred
Plate 45 labels are carried into plate 44's pixel frame through the cufp world models (platemap.py), so the
across and join checks also test the adjoining plate.

Then a mis-read simulation: every digit of every label is replaced by its confusion partner(s), one at a time,
and the checks are run again on the side with that one label changed.

usage: python -B hn_checks.py            (writes out/hn_true.json, out/hn_sim.json, prints the tables)
"""
import json, os, sys, itertools, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import platemap
BASE = os.path.dirname(HERE)
SCALE = json.load(open(os.path.join(BASE, '..', '..', '..', 'scale_table.json')))

# digit confusions. Ben named 3/8 and 1/7; the rest are the usual italic-print confusions (an assumption, not measured)
CONF = [('3', '8'), ('1', '7'), ('5', '6'), ('6', '8'), ('0', '8'), ('0', '6'), ('4', '9'), ('2', '7'), ('3', '5'), ('5', '8'), ('1', '4')]
PARTNER = collections.defaultdict(set)
for a, b in CONF:
    PARTNER[a].add(b); PARTNER[b].add(a)

TAU_FIT_MIN = 3.0   # numbers; the fit tolerance is max(TAU_FIT_MIN, 1.5 x the numbers per 25 ft lot): set after looking at the true reads' residuals (see the printout)
TAU_ACROSS = 8.0    # numbers; the two sides are not lot-for-lot
TAU_JOIN = 8.0      # numbers, plus JOIN_RATE_SLACK x rate x gap (the rate is known to about a quarter)
JOIN_RATE_SLACK = 0.25
JOIN_REACH = 400.0  # ft: labels this close to a cross street are tested against the next segment
RANGE_STEPS = (2, 4, 6)   # a printed range (1529-27, 4120-22-24) steps by 2 to 6, one way (all ranges read here step by 2 or 4)


def pxft(plate):
    return 300.0 / SCALE[plate]['ft_per_inch']


def to_frame(plate, frame, x, y):
    if plate == frame:
        return x, y
    q = platemap.px_to_px(plate, frame, x, y)
    return float(q[0]), float(q[1])


# ---------- parsing and expansion
def parts_of(text):
    t = text.strip().rstrip('-')
    if not t:
        return None
    ps = t.split('-')
    if any((not p.isdigit()) for p in ps):
        return None
    return ps


def expand_label(ps, ref=None):
    """ps: printed parts; ref: a full neighbouring number for a label printed short. -> list of ints or None"""
    out = []
    head = ps[0]
    if ref is not None and len(head) < len(str(ref)):
        k = len(str(ref)) - len(head)
        cands = [int(str(ref)[:k] + head)]
        p = int(str(ref)[:k])
        cands += [int(str(p + 1) + head), int(str(p - 1) + head)] if p > 0 else []
        head = str(min(cands, key=lambda c: abs(c - ref)))
    out.append(int(head))
    prev = head
    for p in ps[1:]:
        if len(p) < len(prev):
            v = int(prev[:len(prev) - len(p)] + p)
            if abs(v - int(prev)) > 20:          # crossed a ten/hundred: 1599-01 -> 1601
                alt = [v + 10 ** len(p), v - 10 ** len(p)]
                v = min([v] + alt, key=lambda c: abs(c - int(prev)))
            out.append(v); prev = str(v)
        else:
            out.append(int(p)); prev = p
    return out


# ---------- data
def has_model(plate):
    return os.path.exists(os.path.join(platemap.ROOT, plate, 'model.npz'))


def load():
    """s = feet along the street. Plates with a cufp world model: metres in world along the frame plate's axis
    (so labels on an adjoining plate fall in the same frame); otherwise frame pixels / px per ft."""
    D = json.load(open(os.path.join(BASE, 'data', 'house_numbers.json')))
    streets = []
    for st in D['streets']:
        frame = st['plate_frame']; ax = 0 if st['axis'] == 'x' else 1; k = pxft(frame)
        allxy = [(x, y) for sd in st['sides'].values() if sd['plate'] == frame for _, x, y in sd['labels']]
        mid = np.median(np.array(allxy), 0)
        world = has_model(frame)
        if world:
            p0 = mid.copy(); p1 = mid.copy(); p1[ax] += 1000.0
            w0 = np.array(platemap.px_to_world(frame, *p0)); w1 = np.array(platemap.px_to_world(frame, *p1))
            u = (w1 - w0) / np.linalg.norm(w1 - w0)

            def s_of(plate, x, y):
                w = np.array(platemap.px_to_world(plate, x, y))
                return float(np.dot(w - w0, u)) / 0.3048 + p0[ax] / k
        else:
            def s_of(plate, x, y):
                assert plate == frame, 'a plate without a world model cannot be joined to another'
                return (x, y)[ax] / k
        sides = collections.defaultdict(list)
        for key, sd in st['sides'].items():
            side = sd.get('side_of', key)
            for i, (text, x, y) in enumerate(sd['labels']):
                sides[side].append(dict(id=f"{st['street']}/{key}/{i}", plate=sd['plate'], text=text, x=x, y=y, s=s_of(sd['plate'], x, y)))
        cross = {}
        for n, v in st['cross'].items():
            q = mid.copy(); q[ax] = v
            cross[n] = s_of(frame, *q)
        for side in sides:
            sides[side].sort(key=lambda r: r['s'])
        streets.append(dict(street=st['street'], frame=frame, axis=st['axis'], sides=dict(sides), cross=cross, world=world))
    return streets


def expand_side(labels):
    """fill r['nums'] for every label on one side (None if it cannot be read as numbers)."""
    for r in labels:
        r['parts'] = parts_of(r['text'])
    full = [r for r in labels if r['parts'] and len(r['parts'][0]) >= 3]
    for r in labels:
        if r['parts'] is None:
            r['nums'] = None; continue
        ref = None
        if len(r['parts'][0]) < 3:
            # a label printed short: take the leading digits from the nearest full label (by s)
            if not full:
                r['nums'] = None; continue
            nb = min((f for f in full if f is not r), key=lambda f: abs(f['s'] - r['s']), default=None)
            if nb is None:
                r['nums'] = None; continue
            ref = int(nb['parts'][0]) if nb.get('nums') is None else nb['nums'][-1]
        r['nums'] = expand_label(r['parts'], ref)
    return labels


def segment_of(s, cross):
    return sum(1 for c in sorted(cross.values()) if s > c)


# ---------- robust line
def theil_sen(S, N):
    S = np.asarray(S, float); N = np.asarray(N, float)
    if len(S) < 2:
        return None
    sl = [(N[j] - N[i]) / (S[j] - S[i]) for i, j in itertools.combinations(range(len(S)), 2) if abs(S[j] - S[i]) > 5]
    if not sl:
        return None
    b = float(np.median(sl)); a = float(np.median(N - b * S))
    return a, b


def pts(labels, skip=None):
    """(s, n) for every number of every label except `skip`; a range label gives its numbers around its centre"""
    out = []
    for r in labels:
        if r is skip or not r.get('nums'):
            continue
        for v in r['nums']:
            out.append((r['s'], float(v)))
    return out


def mean_num(r):
    return float(np.mean(r['nums']))


# ---------- the checks
def seg_fit(labels, skip=None, side_labels=None):
    """robust line through a segment's labels except `skip`; with fewer than 3 numbers, the side's slope is borrowed"""
    P = pts([o for o in labels if o is not skip])
    fit = theil_sen(*zip(*P)) if len(P) >= 3 else None
    if fit is None and side_labels is not None and P:
        Pall = pts([o for o in side_labels if o is not skip])
        f2 = theil_sen(*zip(*Pall)) if len(Pall) >= 3 else None
        if f2 is not None:
            b = f2[1]; fit = (float(np.median([v - b * s for s, v in P])), b)
    return fit, P


def fit_tol(fit, P, s):
    """fit tolerance in numbers: 1.5 lots' worth of numbers, at least TAU_FIT_MIN, plus slack when extrapolating"""
    b = fit[1]
    S = [q[0] for q in P]
    ext = max(0.0, min(S) - s, s - max(S)) if S else 0.0
    return max(TAU_FIT_MIN, 1.5 * abs(b) * 25) + JOIN_RATE_SLACK * abs(b) * ext


def segment_relations(st, fits):
    """segment-level across and join relations, and which segment to blame when one fails.
    A failing relation is blamed on the segment whose OTHER relations also fail; if that cannot tell, on both."""
    sides = st['sides']
    rel = []
    for sd in sides:
        for g, F in fits[sd].items():
            if g == '_segs' or F is None:
                continue
            L = fits[sd]['_segs'][g]
            for o in sides:
                if o <= sd:
                    continue
                Fo = fits[o].get(g); Lo = fits[o]['_segs'].get(g, [])
                if Fo is None or not Lo:
                    continue
                lo = max(min(q['s'] for q in L), min(q['s'] for q in Lo)); hi = min(max(q['s'] for q in L), max(q['s'] for q in Lo))
                if hi < lo - 100:
                    continue
                m = (lo + hi) / 2
                rel.append(dict(kind='across', a=(sd, g), b=(o, g), ok=bool(abs((F[0] + F[1] * m) - (Fo[0] + Fo[1] * m)) <= TAU_ACROSS)))
            h = g + 1
            Fh = fits[sd].get(h); Lh = fits[sd]['_segs'].get(h, [])
            if Fh is None or not Lh:
                continue
            r = max(L, key=lambda q: q['s']); q0 = min(Lh, key=lambda q: q['s'])
            gap = q0['s'] - r['s']
            pred = F[0] + F[1] * q0['s']; n = mean_num(q0)
            cont = abs(n - pred) <= TAU_JOIN + JOIN_RATE_SLACK * abs(F[1]) * gap
            restart = abs(int(min(q0['nums'])) // 100 - int(min(r['nums'])) // 100) == 1
            rel.append(dict(kind='join', a=(sd, g), b=(sd, h), ok=bool(cont or restart)))
    for R in rel:
        if R['ok']:
            R['blame'] = []
            continue
        share = {}
        for k in ('a', 'b'):
            other = [Q for Q in rel if Q is not R and R[k] in (Q['a'], Q['b'])]
            share[k] = (sum(not Q['ok'] for Q in other) / len(other)) if other else None
        if share['a'] is not None and share['b'] is not None and share['a'] != share['b']:
            R['blame'] = [R['a'] if share['a'] > share['b'] else R['b']]
        else:
            R['blame'] = [R['a'], R['b']]
    return rel


def check_street(st, only=None):
    """returns {label id: {check: (ok, detail)}}; only: restrict to these ids (for the simulation)"""
    res = {}
    sides = st['sides']; names = list(sides)
    cross = st['cross']
    for sd in names:
        expand_side(sides[sd])
    fits = {}
    for sd in names:                         # per-side, per-segment robust fits on all labels (for across / join)
        segs = collections.defaultdict(list)
        for r in sides[sd]:
            if r.get('nums'):
                segs[segment_of(r['s'], cross)].append(r)
        fits[sd] = {g: (theil_sen(*zip(*pts(L))) if len(pts(L)) >= 3 else seg_fit(L, None, sides[sd])[0]) for g, L in segs.items()}
        fits[sd]['_segs'] = segs
    rel = segment_relations(st, fits)

    def excused(kind, segA, segB):
        for R in rel:
            if R['kind'] == kind and {R['a'], R['b']} == {segA, segB} and not R['ok']:
                return segA not in R['blame']
        return False

    for sd in names:
        L = sides[sd]
        opp = [o for o in names if o != sd]
        for r in L:
            if only is not None and r['id'] not in only:
                continue
            c = {}
            if not r.get('nums'):
                c['format'] = (False, 'not a number / cannot expand')
                res[r['id']] = c
                continue
            nums = r['nums']; n = mean_num(r)
            steps = np.diff(nums)
            okr = all(abs(d) in RANGE_STEPS for d in steps) and len(set(np.sign(steps))) <= 1
            c['format'] = (bool(okr), '' if okr else f'range parts {nums} do not step by 2-6 one way')
            # parity: majority of the other labels on this side
            others = [v for o in L if o is not r and o.get('nums') for v in o['nums']]
            if len(others) >= 3:
                odd = sum(v % 2 for v in others) / len(others)
                maj = 1 if odd >= 0.5 else 0; share = max(odd, 1 - odd)
                bad = [v for v in nums if v % 2 != maj]
                c['parity'] = (bool(not bad or share < 0.8), f'side {"odd" if maj else "even"} {share:.0%}; this {nums}')
            if len(set(v % 2 for v in nums)) > 1:
                c['parity'] = (False, f'mixed parity inside the label {nums}')
            # segment fit, leave-one-out
            g = segment_of(r['s'], cross)
            seg = [o for o in fits[sd]['_segs'].get(g, []) if o is not r]
            fit, P = seg_fit(seg, None, [o for o in L if o is not r])
            if fit is not None:
                a, b = fit
                resid = n - (a + b * r['s'])
                tau = fit_tol(fit, P, r['s'])
                c['fit'] = (bool(abs(resid) <= tau), f'resid {resid:+.1f} (tol {tau:.1f}; rate {b * 25:+.2f} per 25 ft)')
                c['_resid'] = resid
            # order: nearest neighbours in the segment, before and after (labels at a different s)
            if seg and fit is not None:
                sgn = np.sign(fit[1])
                before = [o for o in seg if o['s'] < r['s'] - 3 and o.get('nums')]
                after = [o for o in seg if o['s'] > r['s'] + 3 and o.get('nums')]
                ok = True; why = []
                if before:
                    p = max(before, key=lambda o: o['s'])
                    if np.sign(min(nums) - max(p['nums'])) != sgn and np.sign(max(nums) - min(p['nums'])) != sgn:
                        ok = False; why.append(f'after {p["nums"]}')
                if after:
                    q = min(after, key=lambda o: o['s'])
                    if np.sign(min(q['nums']) - max(nums)) != sgn and np.sign(max(q['nums']) - min(nums)) != sgn:
                        ok = False; why.append(f'before {q["nums"]}')
                c['order'] = (bool(ok), '; '.join(why))
            # duplicate: the same number printed twice on one side; blamed on the label further from its line
            dup = [o for o in L if o is not r and o.get('nums') and set(o['nums']) & set(nums)]
            if dup and fit is not None:
                worse = []
                for o in dup:
                    fo, Po = seg_fit([q for q in fits[sd]['_segs'].get(segment_of(o['s'], cross), []) if q is not o], None, [q for q in L if q is not o])
                    ro = abs(mean_num(o) - (fo[0] + fo[1] * o['s'])) if fo else 0.0
                    if abs(c.get('_resid', 0.0)) >= ro - 0.5:
                        worse.append(o['nums'])
                c['duplicate'] = (not worse, f'same number as {worse}' if worse else 'duplicate, the other label is the odd one')
            # hundred
            hs = [v // 100 for o in seg for v in o['nums']]
            if len(hs) >= 2:
                hmin, hmax = min(hs), max(hs)
                bad = [v for v in nums if not (hmin - (1 if hmax == hmin else 0) <= v // 100 <= hmax + (1 if hmax == hmin else 0))]
                c['hundred'] = (bool(not bad), f'segment hundreds {hmin}-{hmax}; this {nums}')
            # across
            for o in opp:
                fo = fits[o].get(g)
                near = [q for q in fits[o]['_segs'].get(g, []) if abs(q['s'] - r['s']) < 120]
                if fo is None or not near:
                    continue
                d = n - (fo[0] + fo[1] * r['s'])
                plate_o = near[0]['plate']
                key = 'across' if plate_o == r['plate'] else 'across_other_plate'
                ok = abs(d) <= TAU_ACROSS
                note = f'opposite side ({o}, plate {plate_o}) predicts {fo[0] + fo[1] * r["s"]:.0f}, diff {d:+.1f}'
                if not ok and excused('across', (sd, g), (o, g)):
                    ok = True; note += '; excused: the opposite segment is the odd one'
                c[key] = (bool(ok), note)
            # join across cross streets / plate edges: the other segment's line carried over the gap
            for h in (g - 1, g + 1):
                fh = fits[sd].get(h); seg_h = fits[sd]['_segs'].get(h, [])
                if fh is None or not seg_h:
                    continue
                cs = sorted(cross.values())[min(g, h)]
                if abs(r['s'] - cs) > JOIN_REACH:
                    continue
                gap = min(abs(r['s'] - q['s']) for q in seg_h)
                pred = fh[0] + fh[1] * r['s']
                tol = TAU_JOIN + JOIN_RATE_SLACK * abs(fh[1]) * gap
                cont = abs(n - pred) <= tol
                hu_n = int(np.median([v // 100 for q in seg_h for v in q['nums']]))
                restart = abs(int(min(nums)) // 100 - hu_n) == 1
                key = 'join' if all(q['plate'] == r['plate'] for q in seg_h) else 'join_other_plate'
                ok = cont or restart
                note = f'other segment predicts {pred:.0f} +-{tol:.0f}; {"continues" if cont else ("restarts at a hundred" if restart else "neither")}'
                if not ok and excused('join', (sd, g), (sd, h)):
                    ok = True; note += '; excused: the other segment is the odd one'
                c[key] = (bool(ok), note)
            res[r['id']] = c
    return res


def verdict(c):
    fails = [k for k, v in c.items() if not k.startswith('_') and not v[0]]
    return fails


# ---------- candidates and correction
def variants(text):
    out = []
    for i, ch in enumerate(text):
        for p in sorted(PARTNER.get(ch, ())):
            out.append((text[:i] + p + text[i + 1:], f'{ch}->{p} at {i}'))
    return out


def run_with(st, lid, text):
    """re-run the checks on the street with one label's text replaced"""
    for sd in st['sides'].values():
        for r in sd:
            if r['id'] == lid:
                old = r['text']; r['text'] = text
                try:
                    return check_street(st, only={lid}).get(lid, {})
                finally:
                    r['text'] = old
    raise KeyError(lid)


def correct(st, lid, text):
    """candidates one confusion away from the read text; keep those passing every check; best by |fit resid|"""
    ok = []
    for t, why in variants(text):
        c = run_with(st, lid, t)
        if c and not verdict(c):
            ok.append((abs(c.get('_resid', 0.0)), t, why))
    ok.sort()
    return ok


def main():
    streets = load()
    true_rows = []
    for st in streets:
        R = check_street(st)
        for sd, L in st['sides'].items():
            for r in L:
                c = R[r['id']]
                true_rows.append(dict(id=r['id'], street=st['street'], side=sd, plate=r['plate'], text=r['text'], nums=r['nums'],
                                      s_ft=round(r['s'], 1), fails=verdict(c),
                                      checks={k: [bool(v[0]), v[1]] for k, v in c.items() if not k.startswith('_')},
                                      resid=round(c.get('_resid', float('nan')), 2)))
    # residuals of true reads
    res = np.array([abs(t['resid']) for t in true_rows if not np.isnan(t['resid'])])
    print(f'true labels: {len(true_rows)}; leave-one-out |fit residual| median {np.median(res):.2f}, 90% {np.percentile(res, 90):.2f}, 95% {np.percentile(res, 95):.2f}, max {res.max():.2f}')
    fl = [t for t in true_rows if t['fails']]
    print(f'true labels flagged: {len(fl)} of {len(true_rows)}')
    for t in fl:
        print('  ', t['id'], t['text'], t['nums'], t['fails'], {k: v[1] for k, v in t['checks'].items() if not v[0]})
    json.dump(true_rows, open(os.path.join(BASE, 'out', 'hn_true.json'), 'w'), indent=1)

    # simulation
    sim = []
    for st in streets:
        for sd, L in st['sides'].items():
            for r in list(L):
                truth = r['nums']
                for t, why in variants(r['text']):
                    c = run_with(st, r['id'], t)
                    fails = verdict(c)
                    # the variant's numbers
                    nums = None
                    for q in L:
                        if q['id'] == r['id']:
                            old = q['text']; q['text'] = t; expand_side(L); nums = q['nums']; q['text'] = old; expand_side(L)
                    same = nums == truth
                    fix = correct(st, r['id'], t) if fails else []
                    top = fix[0][1] if fix else None
                    uniq = len(fix) == 1 or (len(fix) > 1 and fix[1][0] - fix[0][0] >= 2.0)
                    sim.append(dict(id=r['id'], street=st['street'], side=sd, plate=r['plate'], true_text=r['text'], read=t, why=why,
                                    pair=''.join(sorted((why[0], why[3]))), digit_from_right=len(r['text'].rstrip('-')) - 1 - int(why.split(' at ')[1]),
                                    nums=nums, changes_value=bool(not same), fails=fails, n_cands=len(fix), top=top,
                                    corrected=bool(top == r['text']), unique=bool(bool(fix) and uniq)))
    json.dump(sim, open(os.path.join(BASE, 'out', 'hn_sim.json'), 'w'), indent=1)
    S = [s for s in sim if s['changes_value']]
    det = [s for s in S if s['fails']]
    print(f'\nmis-read variants that change the value: {len(S)}; flagged by at least one check: {len(det)} ({len(det) / len(S):.1%})')
    print(' by confusion pair:')
    byp = collections.defaultdict(list)
    for s in S:
        byp[s['pair']].append(s)
    for p, L in sorted(byp.items()):
        d = sum(1 for s in L if s['fails'])
        cor = sum(1 for s in L if s['fails'] and s['corrected'] and s['unique'])
        print(f'   {p[0]}<->{p[1]}: {len(L):4d} variants, flagged {d / len(L):6.1%}, put right (one clear candidate = truth) {cor / len(L):6.1%}')
    print(' by digit position (0 = last digit):')
    byd = collections.defaultdict(list)
    for s in S:
        byd[min(s['digit_from_right'], 3)].append(s)
    for p, L in sorted(byd.items()):
        d = sum(1 for s in L if s['fails'])
        print(f'   digit {p}{"+" if p == 3 else ""}: {len(L):4d}, flagged {d / len(L):6.1%}')
    print(' which checks fire (share of the flagged variants):')
    cnt = collections.Counter(k for s in det for k in s['fails'])
    for k, v in cnt.most_common():
        print(f'   {k:20s} {v / len(det):6.1%}')
    print(' missed variants (first 25):')
    for s in [s for s in S if not s['fails']][:25]:
        print('   ', s['id'], s['true_text'], '->', s['read'], s['nums'])
    sp = [s for s in S if s['pair'] in ('38', '17')]
    print(f"\nBen's two pairs (3/8, 1/7): {len(sp)} variants, flagged {sum(1 for s in sp if s['fails']) / len(sp):.1%}, "
          f"put right {sum(1 for s in sp if s['fails'] and s['corrected'] and s['unique']) / len(sp):.1%}")
    cor = [s for s in det if s['corrected'] and s['unique']]
    wrong = [s for s in det if s['unique'] and not s['corrected']]
    print(f'flagged variants with one clear candidate: right {len(cor)}, wrong {len(wrong)}, no clear candidate {len(det) - len(cor) - len(wrong)}')


if __name__ == '__main__':
    main()
