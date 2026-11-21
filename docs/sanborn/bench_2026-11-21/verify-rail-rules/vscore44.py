"""verify-rail-rules (21 Nov 2026): independent re-run of rail-rules' headline numbers on plate 44 (run as never placed)
and 1A. Read-only on the repo and on rail-rules/; writes only verify-rail-rules/score/.

Inputs: my own bins (runs/, made by vrun_ink_bins.py from orig/ = cp of the repo files and patched/ = that cp with
rail-rules/diffs/rail_rules.diff applied by `patch -p1`).
  batch     orig/rail_tracks.py: railroad_tracks + streetcar_tracks, as its run() does
  proposed  patched/rail_tracks.py tracks() (TRACKS as patched: rr_alone (600, 60), car_reach 350)
  also: reach 300 / 500 with the filter, and each change alone
Scores two ways:
  A. rail-rules/fold_score.fscore (their wrapper of the rail agent's score_rail_bench.py), imported, unchanged
  B. my own scorer, written here: both sets sampled every 1 px, exact nearest distance (cKDTree), same-kind only;
     recall = share of Ben's length within tol of a rule track; precision = share of rule length within tol of Ben's
     track (rule samples within 30 px of an unchecked src:'rule' truth track are left out, as theirs).
     Folds by sample position: A = (x < 2950 and y < 3560) or x >= 5400; B the rest.
Truth: 44 = rail_ben.page_2026-11-21.json (28 tracks, with the spur), 1A = rail_ben.json (10 checked + 3 unchecked)."""
import os, sys, json, importlib.util
import numpy as np, cv2
from scipy.spatial import cKDTree
HERE = os.path.dirname(os.path.abspath(__file__)); RR_DIR = os.path.join(os.path.dirname(HERE), 'rail-rules')
OUT = os.path.join(HERE, 'score'); os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, RR_DIR)
from fold_score import fscore   # their scorer, unchanged


def load(which):
    spec = importlib.util.spec_from_file_location('rt_' + which, os.path.join(HERE, which, 'rail_tracks.py')); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


RO, RP = load('orig'), load('patched')
J = lambda P, k: [dict(kind=k, src='rule', pts=[[round(float(x), 1), round(float(y), 1)] for x, y in p]) for p in P]


def dense(p, step=1.0):
    p = np.asarray(p, float); S = [p[:1]]
    for a, b in zip(p[:-1], p[1:]):
        n = max(2, int(np.ceil(np.hypot(*(b - a)) / step)) + 1); S.append(a[None] + np.linspace(0, 1, n)[1:, None] * (b - a)[None])
    S = np.vstack(S); d = np.hypot(*np.diff(S, axis=0).T); w = np.zeros(len(S)); w[:-1] += d / 2; w[1:] += d / 2
    return S, w


def fold(S, reg):
    if reg == 'all': return np.ones(len(S), bool)
    a = ((S[:, 0] < 2950) & (S[:, 1] < 3560)) | (S[:, 0] >= 5400); return a if reg == 'A' else ~a


def my_score(rule, truth, regs):
    T = truth['tracks']; out = {}
    unk = [dense(t['pts'])[0] for t in T if t.get('src') == 'rule']; U = cKDTree(np.vstack(unk)) if unk else None
    for k in ('railroad', 'streetcar'):
        ben = [dense(t['pts']) for t in T if t['kind'] == k and t.get('src') != 'rule']; rk = [dense(t['pts']) for t in rule if t['kind'] == k]
        if not ben: continue
        BS = np.vstack([s for s, _ in ben]); BW = np.concatenate([w for _, w in ben]); BT = cKDTree(BS)
        if rk:
            RS = np.vstack([s for s, _ in rk]); RW = np.concatenate([w for _, w in rk]); RT = cKDTree(RS)
            db = RT.query(BS)[0]; dr = BT.query(RS)[0]
            ig = (U.query(RS)[0] <= 30) if U is not None else np.zeros(len(RS), bool)
        for reg in regs:
            for tol in (10, 30):
                fb = fold(BS, reg); R = float((BW * fb * (db <= tol)).sum() / (BW * fb).sum()) if rk else 0.0
                if rk:
                    fr = fold(RS, reg) & ~ig; P = float((RW * fr * (dr <= tol)).sum() / (RW * fr).sum()) if (RW * fr).sum() else None
                else: P = None
                out.setdefault(reg, {}).setdefault(k, {})[f'tol{tol}'] = dict(recall=round(R, 4), precision=None if P is None else round(P, 4),
                                                                              f1=None if not P or not R else round(2 * P * R / (P + R), 4))
    return out


def main():
    T44 = json.load(open('picks22_guided/22-44/rail_ben.page_2026-11-21.json', encoding='utf8')); T1A = json.load(open('picks22_guided/22-1A/rail_ben.json', encoding='utf8'))
    res = {'bins_checks': {}}
    # bins: mine vs theirs vs the rail agent's
    pairs = {'44_nomap': ('runs/44_nomap_orig_bins.png', 'runs/44_nomap_patched_bins.png', ['rail-rules/runs/44_nomap_orig_bins.png', 'rail-rules/runs/44_nomap_prop_bins.png', 'rail/runs/44_nomap_bins.png']),
             '1A': ('runs/1A_orig_bins.png', 'runs/1A_patched_bins.png', ['rail-rules/runs/1A_prop_bins.png', 'rail/runs/1A_bins.png'])}
    if os.path.exists(os.path.join(HERE, 'runs/44_map_patched_bins.png')):
        pairs['44_map'] = ('runs/44_map_orig_bins.png', 'runs/44_map_patched_bins.png', ['rail-rules/runs/44_map_prop_bins.png', 'rail/runs/44_map_bins.png'])
    BINS = {}
    for name, (o, p, others) in pairs.items():
        Bo = cv2.imread(os.path.join(HERE, o), 0); Bp = cv2.imread(os.path.join(HERE, p), 0); BINS[name] = (Bo, Bp)
        c = res['bins_checks'][name] = dict(orig_vs_patched_px_differ=int((Bo != Bp).sum()))
        for f in others:
            fp = os.path.join(os.path.dirname(HERE), f); X = cv2.imread(fp, 0)
            c[f] = None if X is None else int((X != Bp).sum())
    cfgs = {}
    for name, (Bo, Bp) in BINS.items():
        N = '1A' if name == '1A' else '44'; truth = T1A if N == '1A' else T44; H, W = Bp.shape; regs = ('all',) if N == '1A' else ('all', 'A', 'B')
        rr_o = RO.railroad_tracks((Bo == 4).astype(np.uint8)); car_o = RO.streetcar_tracks((Bo == 5).astype(np.uint8))
        rr_p = RP.railroad_tracks((Bp == 4).astype(np.uint8)); rr_pf = RP.drop_alone(rr_p, *RP.TRACKS['rr_alone'])
        C = {'batch': J(rr_o, 'railroad') + J(car_o, 'streetcar'), 'proposed': RP.tracks(Bp),
             'filter_only': J(rr_pf, 'railroad') + J(RP.streetcar_tracks((Bp == 5).astype(np.uint8), reach=150), 'streetcar'),
             'reach350_only': J(rr_p, 'railroad') + J(RP.streetcar_tracks((Bp == 5).astype(np.uint8)), 'streetcar'),
             'prop_reach300': J(rr_pf, 'railroad') + J(RP.streetcar_tracks((Bp == 5).astype(np.uint8), reach=300), 'streetcar'),
             'prop_reach500': J(rr_pf, 'railroad') + J(RP.streetcar_tracks((Bp == 5).astype(np.uint8), reach=500), 'streetcar')}
        assert C['proposed'] == J(rr_pf, 'railroad') + J(RP.streetcar_tracks((Bp == 5).astype(np.uint8), reach=350), 'streetcar')
        # compare with rail-rules' saved final tracks
        for cn, theirs in (('batch', 'batch'), ('proposed', 'proposed')):
            fp = os.path.join(RR_DIR, 'final', f'{name}_{theirs}_rail_rule.json')
            if os.path.exists(fp): res.setdefault('tracks_equal_theirs', {})[f'{name}|{cn}'] = (json.load(open(fp))['tracks'] == C[cn])
        for cn, tr in C.items():
            o, full = fscore(N, tr, truth, H, W, regs)
            r = res.setdefault('scores', {})[f'{name}|{cn}'] = dict(n=dict(railroad=sum(t['kind'] == 'railroad' for t in tr), streetcar=sum(t['kind'] == 'streetcar' for t in tr)),
                                                                   theirs_scorer={reg: {k: {tl: {x: o[reg][k][tl][x] for x in ('recall', 'precision', 'f1', 'found', 'partial', 'missed', 'broken_interior', 'gaps', 'false_tracks', 'false_tracks_len')} for tl in ('tol10', 'tol30')} for k in ('railroad', 'streetcar')} for reg in regs},
                                                                   my_scorer=my_score(tr, truth, regs))
            s = r['theirs_scorer']; m = r['my_scorer']
            line = f'{name:9s} {cn:15s} n_rr {r["n"]["railroad"]:3d} n_car {r["n"]["streetcar"]:3d}'
            for reg in regs:
                a, b = s[reg]['railroad']['tol10'], s[reg]['streetcar']['tol30']; ma, mb = m.get(reg, {}).get('railroad', {}).get('tol10'), m[reg]['streetcar']['tol30']
                line += f' | {reg}: rr10 R{100 * (a["recall"] or 0):.1f} P{100 * (a["precision"] or 0):.1f} ft{a["false_tracks"]}' + (f' (mine R{100 * ma["recall"]:.1f} P{100 * (ma["precision"] or 0):.1f})' if ma else '')
                line += f' car30 R{100 * b["recall"]:.1f} P{100 * (b["precision"] or 0):.1f} F{100 * (b["f1"] or 0):.1f} g{b["gaps"]} (mine R{100 * mb["recall"]:.1f} P{100 * (mb["precision"] or 0):.1f})'
            print(line, flush=True)
        cfgs[name] = C
    # the spur Ben drew today (page file only): which railroad truth tracks are new, and are they found before / after
    old = json.load(open('picks22_guided/22-44/rail_ben.json', encoding='utf8'))['tracks']
    new = [t for t in T44['tracks'] if t not in old]
    res['spur'] = []
    for t in new:
        S, w = dense(t['pts'])
        for cn in ('batch', 'proposed'):
            R = [dense(x['pts'])[0] for x in cfgs['44_nomap'][cn] if x['kind'] == t['kind']]
            d = cKDTree(np.vstack(R)).query(S)[0]
            res['spur'].append(dict(kind=t['kind'], a=t['pts'][0], b=t['pts'][-1], len=round(float(w.sum())), config=cn, cov10=round(float((w * (d <= 10)).sum() / w.sum()), 3)))
    print('spur / new truth tracks:', json.dumps(res['spur']))
    # railroad tracks the group filter drops on 44 and 1A, with their distance to Ben's railroad
    for name in ('44_nomap', '1A'):
        Bp = BINS[name][1]; rr = RP.railroad_tracks((Bp == 4).astype(np.uint8)); kept = {id(p) for p in RP.drop_alone(rr, *RP.TRACKS['rr_alone'])}
        truth = T44 if name != '1A' else T1A; BR = [dense(t['pts'])[0] for t in truth['tracks'] if t['kind'] == 'railroad']
        BT = cKDTree(np.vstack(BR)) if BR else None; L = []
        for p in rr:
            if id(p) in kept: continue
            S, w = dense(p); near = (w * (BT.query(S)[0] <= 10)).sum() / w.sum() if BT else 0.0
            L.append(dict(len=round(RO.plen(p)), a=[round(float(v)) for v in p[0]], b=[round(float(v)) for v in p[-1]], share_near_ben_rr=round(float(near), 3)))
        res.setdefault('dropped', {})[name] = L; print(name, 'dropped railroad:', json.dumps(L))
    json.dump(res, open(os.path.join(OUT, 'vscore44.json'), 'w'), indent=1)
    print(json.dumps(dict(bins_checks=res['bins_checks'], tracks_equal_theirs=res.get('tracks_equal_theirs')), indent=1))


if __name__ == '__main__':
    main()
