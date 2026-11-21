"""merge/v-eye: run the staged merged block step (and A, outline-quality's proposal, for the comparison) on the eye-check
plates from the batch's saved maps (21 Nov 2026). Every output in merge/v-eye/runs/{merged,A}/N/.

    python -B run_all.py [merged|A|both] [N ...]   (default both, all of common.PLATES; 4 at a time)
"""
import concurrent.futures as cf, json, os, sys, time
import common as C

what = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ('merged', 'A', 'both') else 'both'
pl = [a for a in sys.argv[1:] if a not in ('merged', 'A', 'both')] or C.PLATES
jobs = []
for n in pl:
    if what in ('merged', 'both'): jobs.append(('merged', n))
    if what in ('A', 'both'): jobs.append(('A', n))


def one(j):
    kind, n = j; out = C.ME + f'runs/{kind}/{n}/'; t = time.time()
    rc, so, se = (C.merged if kind == 'merged' else C.run_A)(n, out)
    os.makedirs(out, exist_ok=True)
    open(out + 'stdout.txt', 'w', encoding='utf8').write(so); open(out + 'stderr.txt', 'w', encoding='utf8').write(se)
    return kind, n, rc, round(time.time() - t, 1), (so.strip().splitlines() or [''])[-1][:300], se.strip()[-600:]


with cf.ThreadPoolExecutor(4) as ex:
    for kind, n, rc, s, last, err in ex.map(one, jobs):
        print(kind, n, 'rc', rc, s, 's |', last, ('| ERR ' + err) if rc else '', flush=True)
