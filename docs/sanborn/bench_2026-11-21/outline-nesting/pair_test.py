"""Does a 'parallel partner' test tell street-hole sides from pocket sides?  A street is two parallel lines: a hole side
that is a street side has another exported side (any polygon) running parallel to it (<= ANG deg), across a gap of
WMIN..WMAX full px, overlapping >= OVL of its length in projection.

    python pair_test.py      -> pair_test.json; prints, for plate 44 (scored against Ben's lines via holes44.json) and
                                for the eye-judged PDF sample (sample_holes/verdicts.json), how many pass

Not used by outlines_nest.py unless adopted.
"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
ANG, WMIN, WMAX, OVL = 12.0, 15.0, 260.0, 0.4


def exported(polys):
    out = []
    for hi, p in enumerate(polys):
        for s in p:
            if s['state'] == 'short' or s.get('paper_edge'): continue
            out.append((hi, bool(p and p[0].get('hole')), np.array(s['a'], float), np.array(s['b'], float)))
    return out


def has_partner(a, b, segs, skip):
    d = b - a; L = np.hypot(*d); u = d / L; nrm = np.array([-u[1], u[0]]); c = np.cos(np.radians(ANG))
    for j, (_, _, p, q) in enumerate(segs):
        if j == skip: continue
        e = q - p; Le = np.hypot(*e)
        if Le < 1 or abs((e / Le) @ u) < c: continue
        w = abs(((p + q) / 2 - a) @ nrm)
        if not (WMIN <= w <= WMAX): continue
        t0, t1 = sorted(((p - a) @ u, (q - a) @ u)); ov = max(0.0, min(L, t1) - max(0.0, t0))
        if ov >= OVL * L: return True
    return False


def plate_pass(polys):
    segs = exported(polys); res = {}
    for i, (hi, hole, a, b) in enumerate(segs):
        if hole: res[(tuple(a.round(1)), tuple(b.round(1)))] = has_partner(a, b, segs, i)
    return res


if __name__ == '__main__':
    out = {}
    # 44: per hole side, on Ben's lines or not (holes44.json from runs/nest)
    P = json.load(open(HERE + 'runs/nest/outlines.json', encoding='utf8')); H = json.load(open(HERE + 'runs/nest/holes44.json'))['holes']
    pp = plate_pass(P); rows = []
    for r in H:
        p = P[r['poly']]; k = 0
        for s in p:
            if s['state'] == 'short' or s.get('paper_edge'): continue
            q = r['per_side'][k]; k += 1
            rows.append(dict(hole=r['poly'], len=q['len'], on_ben=q['on_ben'], passes=pp[(tuple(np.round(s['a'], 1)), tuple(np.round(s['b'], 1)))]))
    def agg(f): s = [x for x in rows if f(x)]; return dict(n=len(s), len=sum(x['len'] for x in s), on_ben_len=round(sum(x['len'] * (x['on_ben'] or 0) for x in s)))
    out['44'] = dict(all=agg(lambda x: True), passes=agg(lambda x: x['passes']), fails=agg(lambda x: not x['passes']), rows=rows)
    print('44 hole sides:', out['44']['all'], '| pass:', out['44']['passes'], '| fail:', out['44']['fails'])
    # PDF sample
    S = json.load(open(HERE + 'sample_holes/sample.json'))['sample']
    V = json.load(open(HERE + 'sample_holes/verdicts.json')) if os.path.exists(HERE + 'sample_holes/verdicts.json') else {}
    cache = {}; srows = []
    for o in S:
        n = o['plate']
        if n not in cache: cache[n] = plate_pass(json.load(open(HERE + f'runs_plates/new/{n}/outlines.json', encoding='utf8')))
        ok = cache[n].get((tuple(np.round(o['a'], 1)), tuple(np.round(o['b'], 1))))
        srows.append(dict(k=o['k'], plate=n, passes=ok, verdict=V.get(str(o['k']))))
    for v in ('yes', 'no', 'unsure'):
        s = [x for x in srows if x['verdict'] == v]; print(f'PDF sample verdict {v}: {len(s)}, pass {sum(bool(x["passes"]) for x in s)}')
    out['pdf_sample'] = srows
    json.dump(out, open(HERE + 'pair_test.json', 'w'), indent=1)
