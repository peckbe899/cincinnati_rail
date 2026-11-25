"""Lot-frontage check by code: the frontages printed along a block face must add up to the face length measured on
the plate at its printed scale; where they do not, the forward and backward running sums say which lot is wrong.

Tested on three faces read by eye (data/lot_frontages.json) and on mis-read variants of every label.
usage: python -B frontage_check.py      (prints the tables, writes out/frontage.json)
"""
import json, os, re, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.dirname(HERE)
SCALE = json.load(open(os.path.join(BASE, '..', '..', '..', 'scale_table.json')))
FRAC = {'1/2': 0.5, '1/4': 0.25, '3/4': 0.75, '½': 0.5, '¼': 0.25, '¾': 0.75}
SUM_TOL_FT = 2.0       # ft, or SUM_TOL_REL of the face, whichever is larger (printed scale vs scan: about 1%)
SUM_TOL_REL = 0.01
LOT_SLACK_PX = 12      # a label may sit this far outside the middle half of its lot
CONF = [('3', '8'), ('1', '7'), ('5', '6'), ('6', '8'), ('0', '8'), ('0', '6'), ('4', '9'), ('2', '7'), ('3', '5'), ('5', '8'), ('1', '4')]
PARTNER = collections.defaultdict(set)
for a_, b_ in CONF:
    PARTNER[a_].add(b_); PARTNER[b_].add(a_)

RX_FT = re.compile(r"^(\d{1,3})(\.\d{1,2})?'$")                          # 25'  37.50'
RX_DEC = re.compile(r"^(\d{1,3})\.(\d{1,2})$")                             # 20.92  (decimal, no mark: still feet)
RX_FI = re.compile(r"^(\d{1,3})'(\d{1,2})(?: ?(1/2|1/4|3/4|½|¼|¾))?\"$")  # 25'3"  20'10 1/2"
RX_BARE = re.compile(r"^(\d{1,3})$")                                       # 90: a lot number by the KEY, or a frontage without its mark


def parse(t):
    """-> (kind, feet): kind 'ft', 'ditto', 'bare' (integer without a foot mark), or 'bad'"""
    t = t.strip()
    if t in ('"', "''", '〃', '”'):
        return 'ditto', None
    m = RX_FT.match(t)
    if m:
        return 'ft', float(m.group(1) + (m.group(2) or ''))
    m = RX_FI.match(t)
    if m:
        inch = int(m.group(2)) + FRAC.get(m.group(3) or '', 0.0)
        if inch >= 12:
            return 'bad', None
        return 'ft', int(m.group(1)) + inch / 12.0
    m = RX_DEC.match(t)
    if m:
        return 'ft', float(t)
    m = RX_BARE.match(t)
    if m:
        return 'bare', float(t)
    return 'bad', None


def check_face(face, pxft, texts=None):
    """returns a dict with the sum test and, on a mismatch, where the running sums part"""
    a = np.array(face['a'], float); b = np.array(face['b'], float)
    Lpx = float(np.linalg.norm(b - a)); u = (b - a) / Lpx
    texts = texts or [t for t, _ in face['labels']]
    xs = [x for _, x in face['labels']]
    # label position along the face (x only was read; the faces here run along x)
    ts = [(x - a[0]) / u[0] for x in xs]
    parsed = []; last = None; bad = []
    for t in texts:
        k, v = parse(t)
        if k == 'ditto':
            k, v = ('ft', last) if last is not None else ('bad', None)
        if k == 'ft':
            last = v
        if k == 'bad':
            bad.append(t)
        parsed.append((k, v))
    Lft = Lpx / pxft
    tol = max(SUM_TOL_FT, SUM_TOL_REL * Lft)
    out = dict(face=face['id'], length_px=round(Lpx, 1), length_ft=round(Lft, 2), tol_ft=round(tol, 2), format_bad=bad)
    # every reading of the bare integers: frontage, or a lot number (then that lot's frontage is unknown)
    bare = [i for i, (k, _) in enumerate(parsed) if k == 'bare']
    options = []
    for mask in range(2 ** len(bare)):
        as_ft = {bare[j] for j in range(len(bare)) if mask >> j & 1}
        known = sum(v for i, (k, v) in enumerate(parsed) if (k == 'ft') or (i in as_ft))
        unknown = [i for i in bare if i not in as_ft] + [i for i, (k, _) in enumerate(parsed) if k == 'bad']
        diff = known - Lft
        if unknown:                       # one or more lots without a frontage: they take up the rest
            rest = Lft - known
            ok = rest >= 8.0 * len(unknown)
            options.append(dict(bare_as_frontage=sorted(as_ft), printed_sum_ft=round(known, 2), unknown_lots=len(unknown),
                                inferred_ft=round(rest, 2), ok=bool(ok)))
        else:
            options.append(dict(bare_as_frontage=sorted(as_ft), printed_sum_ft=round(known, 2), diff_ft=round(diff, 2), ok=bool(abs(diff) <= tol)))
    out['options'] = options
    full = [o for o in options if 'diff_ft' in o]
    out['sum_ok'] = bool(full and full[0]['ok']) if not bare else any(o['ok'] for o in options)
    out['diff_ft'] = full[0]['diff_ft'] if full and not bare else None
    # localisation from the running sums (only when every lot has a frontage)
    if not bare and not bad:
        W = np.array([v for _, v in parsed]) * pxft
        fwd = np.cumsum(W) - W / 2; bwd = Lpx - (np.cumsum(W[::-1]) - W[::-1] / 2)[::-1]
        okf = [bool(abs(fwd[i] - ts[i]) <= W[i] / 2 + LOT_SLACK_PX) for i in range(len(W))]
        okb = [bool(abs(bwd[i] - ts[i]) <= W[i] / 2 + LOT_SLACK_PX) for i in range(len(W))]
        out['fwd_ok'] = okf; out['bwd_ok'] = okb
        if not out['sum_ok']:
            last_f = max([i for i in range(len(W)) if all(okf[:i + 1])], default=-1)
            first_b = min([i for i in range(len(W)) if all(okb[i:])], default=len(W))
            out['suspect_labels'] = [texts[i] + f'@{xs[i]}' for i in range(len(W)) if last_f < i < first_b] or \
                                    [texts[i] + f'@{xs[i]}' for i in range(max(0, first_b - 1), min(len(W), last_f + 2))]
    return out


def variants(t):
    v = []
    for i, ch in enumerate(t):
        for p in sorted(PARTNER.get(ch, ())):
            v.append((t[:i] + p + t[i + 1:], f'{ch}->{p}'))
    return v


def main():
    F = json.load(open(os.path.join(BASE, 'data', 'lot_frontages.json')))['faces']
    rep = dict(true={}, sim={})
    for scale_name in ('nominal 300 dpi', 'measured ft/in (scale_table)'):
        print(f'\n== px per ft: {scale_name}')
        for f in F:
            ftpi = SCALE[f['plate']]['ft_per_inch'] if scale_name.startswith('nominal') else (SCALE[f['plate']].get('measured_ft_per_inch') or SCALE[f['plate']]['ft_per_inch'])
            pxft = 300.0 / ftpi
            r = check_face(f, pxft)
            rep['true'][f"{f['id']} | {scale_name}"] = r
            print(f" {f['id']}: length {r['length_px']} px = {r['length_ft']} ft (px/ft {pxft:.3f}), tol {r['tol_ft']} ft, sum ok {r['sum_ok']}")
            for o in r['options']:
                print('    ', o)
            if 'suspect_labels' in r:
                print('     suspect:', r['suspect_labels'])
    # measured px per ft from the faces whose lots are all printed with a foot mark (an estimate of the scan scale)
    for f in F:
        ks = [parse(t) for t, _ in f['labels']]
        if all(k in ('ft', 'ditto') for k, _ in ks):
            last = None; tot = 0
            for k, v in ks:
                v = last if k == 'ditto' else v; last = v; tot += v
            L = float(np.linalg.norm(np.array(f['b']) - np.array(f['a'])))
            print(f" scale from {f['id']}: {L:.1f} px / {tot:.2f} ft = {L / tot:.3f} px per ft ({300 * tot / L:.1f} ft per inch at 300 dpi)")
    # mis-read simulation, measured px per ft
    print('\n== mis-read variants (one label at a time; px/ft from scale_table measured ft/in)')
    rows = []
    for f in F:
        pxft = 300.0 / (SCALE[f['plate']].get('measured_ft_per_inch') or SCALE[f['plate']]['ft_per_inch'])
        texts = [t for t, _ in f['labels']]
        base = check_face(f, pxft)
        for i, t in enumerate(texts):
            for v, why in variants(t):
                T = list(texts); T[i] = v
                k0, v0 = parse(t); k1, v1 = parse(v)
                if k0 == 'ditto':
                    continue
                r = check_face(f, pxft, T)
                change = (v1 - v0) if (k1 in ('ft', 'bare') and k0 in ('ft', 'bare') and v0 is not None and v1 is not None) else None
                hit = (not r['sum_ok']) or bool(r['format_bad'])
                loc = any(s.startswith(v + '@') for s in r.get('suspect_labels', []))
                rows.append(dict(face=f['id'], true=t, read=v, why=why, change_ft=change, flagged=bool(hit), localised=bool(loc),
                                 suspects=r.get('suspect_labels'), base_ok=base['sum_ok']))
    rep['sim'] = rows
    allft = {f['id'] for f in F if all(parse(t)[0] in ('ft', 'ditto') for t, _ in f['labels'])}
    print('   (faces with every lot printed with a foot mark:', sorted(allft), ')')
    S = [r for r in rows if r['base_ok'] and r['change_ft'] is not None and abs(r['change_ft']) > 0 and r['face'] in allft]
    U = [r for r in rows if r['base_ok'] and r['change_ft'] is not None and abs(r['change_ft']) > 0 and r['face'] not in allft]
    print(f'   face with an unlabelled lot (its width absorbs any error): {len(U)} variants, flagged {sum(r["flagged"] for r in U) / max(1, len(U)):.1%}')
    for lo, hi in ((0, 2), (2, 5), (5, 10), (10, 30), (30, 1000)):
        L = [r for r in S if lo < abs(r['change_ft']) <= hi]
        if L:
            print(f'   change {lo:>3}-{hi:<4} ft: {len(L):3d} variants, flagged {sum(r["flagged"] for r in L) / len(L):6.1%}, '
                  f'wrong label among the suspects {sum(r["localised"] for r in L if r["flagged"]) / max(1, sum(r["flagged"] for r in L)):6.1%} of the flagged')
    for p in ('38', '17'):
        L = [r for r in S if ''.join(sorted(r['why'][0] + r['why'][3])) == p]
        if L:
            print(f"   pair {p[0]}<->{p[1]}: {len(L)} variants, flagged {sum(r['flagged'] for r in L) / len(L):.1%}")
    json.dump(rep, open(os.path.join(BASE, 'out', 'frontage.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
