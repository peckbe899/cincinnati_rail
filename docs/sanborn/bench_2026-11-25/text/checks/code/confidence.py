"""Confidence model: how the code checks combine into ACCEPT, FLAG FOR BEN or REJECT, prototyped on house numbers.

Model (naive Bayes in log-odds):
    log O(read right | checks) = log O(reader) + sum over checks of log LR(check outcome)
    LR(pass) = P(pass | right) / P(pass | wrong),  LR(fail) = P(fail | right) / P(fail | wrong),  n.a. = 1
The likelihood ratios are COUNTED (add-one smoothing, capped at 50:1 either way) from a mis-read simulation on the
by-eye reads of data/house_numbers.json: in each trial every label is mis-read with probability q by one confusable
digit (hn_checks.CONF), so a label's neighbours can be wrong too. They are fitted on four streets and tested on the
fifth (leave one street out), for q = 5%, 15% and 30%.
O(reader) is the reader's own odds; no reader exists yet, so it is set to the trial's q (an assumption).

Decision:
    P >= ACCEPT              accept
    P <= REJECT              the read is rejected; if exactly one confusion candidate passes every check, it is
                             offered to Ben as the correction (flag with a proposal); else rejected (the ink stays text)
    otherwise                flag for Ben
usage: python -B confidence.py      (prints the tables, writes out/confidence.json)
"""
import json, os, sys, random, collections, copy, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import hn_checks as H
ACCEPT = 0.97
REJECT = 0.10
CAP = math.log(50.0)
TRIALS = 30
random.seed(11)


def outcomes(c):
    return {k: bool(v[0]) for k, v in c.items() if not k.startswith('_')}


def trial(st, q):
    """mis-read each label with probability q; returns [(label id, truth text, read text, right?, outcomes)]"""
    S = copy.deepcopy(st)
    truth = {}
    for L in S['sides'].values():
        for r in L:
            truth[r['id']] = r['text']
            if random.random() < q:
                vs = []
                for t, why in H.variants(r['text']):
                    a = H.parts_of(t); b = H.parts_of(r['text'])
                    if a != b:
                        vs.append(t)
                if vs:
                    r['text'] = random.choice(vs)
    R = H.check_street(S)
    out = []
    # right = the read's numbers equal the truth's numbers
    T = copy.deepcopy(st)
    for L in T['sides'].values():
        H.expand_side(L)
    tn = {r['id']: r['nums'] for L in T['sides'].values() for r in L}
    for L in S['sides'].values():
        for r in L:
            out.append(dict(id=r['id'], truth=truth[r['id']], read=r['text'], right=r['nums'] == tn[r['id']], o=outcomes(R[r['id']]),
                            resid=R[r['id']].get('_resid')))
    return S, out


def fit_lr(rows):
    cnt = collections.defaultdict(lambda: collections.Counter())
    nr = sum(1 for r in rows if r['right']); nw = len(rows) - nr
    for r in rows:
        for k, v in r['o'].items():
            cnt[k][(r['right'], v)] += 1
    LR = {}
    for k, c in cnt.items():
        LR[k] = {}
        for v in (True, False):
            pr = (c[(True, v)] + 1) / (nr + 2); pw = (c[(False, v)] + 1) / (nw + 2)
            LR[k][v] = float(np.clip(math.log(pr / pw), -CAP, CAP))
    return LR


def posterior(o, LR, prior):
    lo = math.log(prior / (1 - prior)) + sum(LR.get(k, {}).get(v, 0.0) for k, v in o.items())
    return 1 / (1 + math.exp(-lo))


def main():
    streets = H.load()
    names = [s['street'] for s in streets]
    res = {}
    for q in (0.05, 0.15, 0.30):
        data = {}
        for st in streets:
            rows = []; ctx = []
            for _ in range(TRIALS):
                S, out = trial(st, q)
                rows += out; ctx.append((S, out))
            data[st['street']] = (rows, ctx)
        tab = collections.Counter(); prop = collections.Counter()
        lr_all = fit_lr([r for n in names for r in data[n][0]])
        for i, st in enumerate(streets):
            LR = fit_lr([r for n in names if n != st['street'] for r in data[n][0]])
            for S, out in data[st['street']][1]:
                for r in out:
                    P = posterior(r['o'], LR, 1 - q)
                    if P >= ACCEPT:
                        d = 'accept'
                    elif P <= REJECT:
                        d = 'reject'
                    else:
                        d = 'flag'
                    tab[(r['right'], d)] += 1
                    if not r['right'] and d != 'accept':
                        fix = H.correct(S, r['id'], r['read'])
                        good = [f for f in fix if f[0] <= 2.0]
                        uniq = len(fix) == 1 or (len(fix) > 1 and fix[1][0] - fix[0][0] >= 2.0)
                        if fix and uniq:
                            prop['proposal right' if fix[0][1] == r['truth'] else 'proposal wrong'] += 1
                        else:
                            prop['no clear proposal'] += 1
        nR = sum(v for (rt, _), v in tab.items() if rt); nW = sum(v for (rt, _), v in tab.items() if not rt)
        print(f'\n== mis-read rate q = {q:.0%}  (prior P(right) = {1 - q:.2f}; {TRIALS} trials per street; LRs fitted leaving the street out)')
        print(f'   right reads {nR}: accept {tab[(True, "accept")] / nR:6.1%}  flag {tab[(True, "flag")] / nR:6.1%}  reject {tab[(True, "reject")] / nR:6.1%}')
        print(f'   wrong reads {nW}: accept {tab[(False, "accept")] / nW:6.1%}  flag {tab[(False, "flag")] / nW:6.1%}  reject {tab[(False, "reject")] / nW:6.1%}')
        acc = tab[(True, 'accept')] + tab[(False, 'accept')]
        print(f'   wrong among the accepted: {tab[(False, "accept")]} of {acc} ({tab[(False, "accept")] / max(1, acc):.2%})')
        tp = sum(prop.values())
        print(f'   wrong reads flagged or rejected: correction proposal right {prop["proposal right"] / max(1, tp):.1%}, wrong {prop["proposal wrong"] / max(1, tp):.1%}, none {prop["no clear proposal"] / max(1, tp):.1%}')
        print('   log likelihood ratios (all streets):', {k: {('pass' if v else 'fail'): round(x, 2) for v, x in d.items()} for k, d in sorted(lr_all.items())})
        res[f'q={q}'] = dict(table={f'{"right" if k[0] else "wrong"} {k[1]}': v for k, v in tab.items()}, proposals=dict(prop),
                             lr_all={k: {('pass' if v else 'fail'): x for v, x in d.items()} for k, d in lr_all.items()})
    json.dump(res, open(os.path.join(BASE, 'out', 'confidence.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
