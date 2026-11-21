"""outline-quality: table of a sweep file.  python show.py NAME [sort key: PQ|PQA|PQB|cl] [filter python expr on r]"""
import json, sys
f = sys.argv[1]; key = sys.argv[2] if len(sys.argv) > 2 else None; flt = sys.argv[3] if len(sys.argv) > 3 else None
R = [json.loads(l) for l in open(f'sweeps/{f}.jsonl')]
if flt: R = [r for r in R if eval(flt)]
K = dict(PQ=lambda r: r['pq']['all']['PQ'], PQA=lambda r: r['pq']['A']['PQ'], PQB=lambda r: r['pq']['B']['PQ'], cl=lambda r: r['closed']['snap10']['all'])
if key: R.sort(key=K[key], reverse=True)
const = {k for k in set().union(*[r['P'] for r in R]) if len({json.dumps(r['P'].get(k)) for r in R}) == 1 and all(k in r['P'] for r in R)} if len(R) > 1 else set()
print(f"{'params':70s} {'PQ':>6s} {'PQ_A':>6s} {'PQ_B':>6s} {'PQdec':>6s} {'m':>3s} {'fp':>3s} {'mrg':>3s} {'wsPQ':>6s} {'R':>6s} {'P':>6s} {'Pgrn':>6s} {'Porg':>6s} {'cl10':>4s} {'cl1.5':>5s} {'ring':>4s} {'del':>6s} {'draw':>6s} {'s':>5s}")
for r in R:
    p = json.dumps({k: v for k, v in r['P'].items() if k not in const}, sort_keys=True).replace('"', '')[1:-1] + ('' if r['step4'] == 'default' else ' |' + r['step4'])
    q, l, w = r['pq']['all'], r['lines']['all'], r['work']['all']
    print(f"{p[:70]:70s} {q['PQ']:6.3f} {r['pq']['A']['PQ']:6.3f} {r['pq']['B']['PQ']:6.3f} {q['PQ_decided']:6.3f} {q['matched']:3d} {q['fp']:3d} {q['merges']:3d} {r.get('pq_ws', {}).get('all', {}).get('PQ', float('nan')):6.3f} "
          f"{l['recall_interior']:6.3f} {l['precision']:6.3f} {(l['precision_green'] or 0):6.3f} {(l['precision_orange'] or 0):6.3f} {r['closed']['snap10']['all']:4d} {r['closed']['snap1.5']['all']:5d} {r['rings']['intact']:4d} {w['delete_len']:6d} {w['draw_len']:6d} {r['outline_s'] + r['score_s']:5.0f}")
