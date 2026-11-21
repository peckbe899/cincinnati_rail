"""outline-quality: one outline-step setting, every step-4 policy of sweep.STEP4 scored on the same outlines.
    python step4_policies.py NAME '{"markers": true, ...}'
Appends one line per policy to sweeps/NAME.jsonl (same format as sweep.py)."""
import json, os, sys, time
sys.dont_write_bytecode = True
import sweep as S  # noqa: E402
B, O = S.B, S.O
name, P = sys.argv[1], json.loads(sys.argv[2])
S.init(B.U + '44_pred_area_ng1.png', B.U + '44_lines_lines_ng1.png')
t0 = time.time(); polys, rep, _, block, inst = O.outline(S.G['D'], P, vis_out=False); t1 = time.time()
for st in S.STEP4:
    t2 = time.time(); s, _, _ = S.score(polys, inst, st)
    r = dict(P=P, step4=st, rep=rep, mixed_pieces=S.G['D'].get('_mixed_pieces'), outline_s=round(t1 - t0, 1), score_s=round(time.time() - t2, 1), **s)
    open(S.HERE + f'sweeps/{name}.jsonl', 'a').write(json.dumps(r) + '\n')
    print(st, json.dumps(dict(PQ=r['pq']['all']['PQ'], R=r['lines']['all']['recall_interior'], Pr=r['lines']['all']['precision'], cl10=r['closed']['snap10'], cl1=r['closed']['snap1.5']['all'], work=r['work']['all'])), flush=True)
