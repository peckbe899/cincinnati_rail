"""outline-quality: pick settings on one fold of plate 44, report them on the other (held-out) fold.
    python fold_select.py SWEEP[,SWEEP...] [--objective pq|closed|f1] [--filter EXPR] [--ref '{params}']
Objective on the tuning fold (ties broken in this order):
  pq      PQ of the fold, then line F1 (recall x precision of what the editor shows), then Ben blocks closed (snap 10)
  closed  Ben blocks closed (snap 10), then line F1, then PQ
  f1      line F1, then PQ
For each direction (tune A -> test B, tune B -> test A) prints the chosen setting with its tuning-fold and held-out
numbers, beside the reference settings (--ref, default the untuned combined variant) and the batch (no switches).
Writes fold_select_<SWEEP>_<objective>.json."""
import argparse, json, os
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'


def f1(l): return 0.0 if not l['recall_interior'] or not l['precision'] else 2 * l['recall_interior'] * l['precision'] / (l['recall_interior'] + l['precision'])


def nums(r, f):
    q, l, w = r['pq'][f], r['lines'][f], r['work'][f]
    return dict(PQ=q['PQ'], matched=q['matched'], fp=q['fp'], merges=q['merges'], PQ_decided=q['PQ_decided'], recall=l['recall_interior'], precision=l['precision'],
                precision_green=l['precision_green'], F1=round(f1(l), 4), closed10=r['closed']['snap10'][f], closed1_5=r['closed']['snap1.5'][f], delete_len=w['delete_len'], draw_len=w['draw_len'])


def key(r, f, obj):
    q, l, c = r['pq'][f]['PQ'], f1(r['lines'][f]), r['closed']['snap10'][f]
    return {'pq': (q, l, c), 'closed': (c, l, q), 'f1': (l, q, c)}[obj]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('sweeps'); ap.add_argument('--objective', default='pq'); ap.add_argument('--filter', default=None); ap.add_argument('--ref', default=None)
    ap.add_argument('--step4', default=None)
    a = ap.parse_args(); R = []
    for s in a.sweeps.split(','):
        R += [json.loads(l) for l in open(HERE + f'sweeps/{s}.jsonl')]
    if a.step4: R = [r for r in R if r['step4'] == a.step4]
    if a.filter: R = [r for r in R if eval(a.filter)]
    allr = [json.loads(l) for s in os.listdir(HERE + 'sweeps') if s.endswith('.jsonl') for l in open(HERE + 'sweeps/' + s)]
    find = lambda P, st='default': next((r for r in allr if r['P'] == P and r['step4'] == st), None)
    ref = json.loads(a.ref) if a.ref else dict(markers=True, gate=True, rings=True, colin_off=12, join_slide=12, ring_corner=400)
    out = dict(sweeps=a.sweeps, objective=a.objective, n_settings=len(R), directions={})
    for tune, test in (('A', 'B'), ('B', 'A')):
        best = max(R, key=lambda r: key(r, tune, a.objective))
        ties = [r for r in R if key(r, tune, a.objective) == key(best, tune, a.objective)]
        d = dict(chosen=best['P'], step4=best['step4'], n_tied=len(ties), tune_fold=tune, test_fold=test, chosen_on_tune=nums(best, tune), chosen_on_test=nums(best, test), chosen_on_all=nums(best, 'all'))
        rr = find(ref, best['step4']) or find(ref); bb = find({'markers': False}) or find({})
        if rr: d['ref_on_test'] = nums(rr, test); d['ref_on_tune'] = nums(rr, tune)
        if bb: d['batch_on_test'] = nums(bb, test); d['batch_on_tune'] = nums(bb, tune)
        # rank of the held-out result among all settings on the test fold
        d['test_rank_of_chosen'] = 1 + sum(1 for r in R if key(r, test, a.objective) > key(best, test, a.objective)); d['test_best_possible'] = nums(max(R, key=lambda r: key(r, test, a.objective)), test)
        out['directions'][f'tune_{tune}_test_{test}'] = d
        print(f'\n== tune on fold {tune} ({a.objective}), test on fold {test}: {len(R)} settings, {len(ties)} tied at the top')
        print('chosen:', json.dumps(best['P']), best['step4'])
        for nm, k in (('chosen, tuning fold', 'chosen_on_tune'), ('chosen, HELD-OUT fold', 'chosen_on_test'), ('reference, held-out fold', 'ref_on_test'), ('batch, held-out fold', 'batch_on_test'), ('best possible on held-out fold', 'test_best_possible')):
            if k in d: print(f'  {nm:32s}', json.dumps(d[k]))
        print('  rank of the chosen setting on the held-out fold:', d['test_rank_of_chosen'], 'of', len(R))
    json.dump(out, open(HERE + f'fold_select_{a.sweeps.replace(",", "+")}_{a.objective}{"_" + a.step4 if a.step4 else ""}.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
