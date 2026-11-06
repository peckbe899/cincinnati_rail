"""Seam report rerun after the re-read of the 15 widest ties (Ben, 6 November): tools/sanborn/seams.py unchanged, run with
(a) each mis-pick replaced by its re-read (data/sanborn/picks22_reread/<plate>/*.json, verdict a) and (b) each wrong name
match dropped (verdict b). Plates on their own models; nothing refitted. Run from data/sanborn:

    python reports/2026-11-06_seams_reread/rerun.py
"""
import glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'sanborn'))
import _ws  # noqa: E402
import seams as S  # noqa: E402

SP = _ws.DATA
V = json.load(open(os.path.join(HERE, 'verdicts.json'), encoding='utf8'))
REC = {}
for f in glob.glob(SP + 'picks22_reread/*/*.json'):
    r = json.load(open(f, encoding='utf8'))
    if r.get('round', 1) == 1:      # round-2 records (targeted reads) are reached through their verdict's 'record'
        REC[(r['tie'], r['plate'])] = (r, os.path.relpath(f, SP).replace('\\', '/'))

LATEST = {}
for v in V:                      # verdicts are appended (round 2: the targeted reads); the last one for a tie counts
    LATEST[v['n']] = v
REPLACE, DROP = {}, set()
for v in LATEST.values():
    if v['verdict'] == 'a':
        if v.get('record'):
            f = v['record']; r = json.load(open(SP + f, encoding='utf8'))
        else:
            r, f = REC[(v['n'], v['mispick_plate'])]
        REPLACE[(r['plate'], round(r['old_pick']['x'], 1), round(r['old_pick']['y'], 1))] = (r['new_pick'], f)
    elif v['verdict'] == 'b':
        a, b = v['tie'].split(' / ')
        r, _ = REC[(v['n'], a)]
        DROP.add((a, b, S.k2(*r['old_pick']['names'])))
        DROP.add((a, b, S.k2(*v['crossing'].split(' & '))))

_pc = S.plate_crossings


def plate_crossings(pid):
    recs, nf = _pc(pid)
    for r in recs:
        hit = REPLACE.get((pid, round(r['x'], 1), round(r['y'], 1)))
        if hit:
            new, f = hit
            r.update(x=new['x'], y=new['y'], E=new['E'], N=new['N'], reread=f); S.READ.append(f)
    return recs, nf


_pairs = S.pairs


def pairs(recs):
    near, far = _pairs(recs)
    keep = lambda i, j: (recs[i]['src'], recs[j]['src'], recs[i]['k']) not in DROP and (recs[j]['src'], recs[i]['src'], recs[i]['k']) not in DROP
    return [t for t in near if keep(t[0], t[1])], [t for t in far if keep(t[0], t[1])]


S.plate_crossings, S.pairs = plate_crossings, pairs
if __name__ == '__main__':
    readme = os.path.join(HERE, 'README.md')
    saved = open(readme, encoding='utf8').read() if os.path.exists(readme) else None   # seams.py writes its own README.md here
    S.main([HERE])
    os.replace(readme, os.path.join(HERE, 'seams_detail.md'))
    if saved is not None:
        open(readme, 'w', encoding='utf8', newline='\n').write(saved)
    print('replaced', len(REPLACE), 'dropped', len(DROP))
