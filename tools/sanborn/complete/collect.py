"""Part 1 of the complete-control fit (Ben, 6 November 2026; docs/sanborn/RULES.md rule 12): collate the two independent
reads of every named crossing not yet picked into data/sanborn/picks22_complete/.

    cd data/sanborn
    python ../../tools/sanborn/complete/collect.py JOBS_DIR

JOBS_DIR holds jobs.json and info.json (tools/sanborn/complete/prep.py) and reads/<group>.json (the readers' output;
groups A.. are the first read, B.. the second, every job in one group of each). A pick is kept only when both reads
found the crossing and their points lie within 60 px of each other (the readers' merge distance, sbg/picks22): the
pick is their mean. Crossings with Central Parkway (in 1922 the plates show the canal bed there, not a street) or with a
viaduct (a street meeting its own viaduct is a name change, not a crossing) are left out. A pick within 60 px of one
of the plate's current controls, or of another new pick, is a duplicate (one plate crossing under two names or two OSM
nodes) and left out.
A pick is also left out if, under the plate's current model, it falls more than 45 m from the OSM crossing it was read for (rule 4's first match radius: a different crossing of the same names, or a misread).

Writes data/sanborn/picks22_complete/<plate>/picks.json (the kept picks: names, pixel, the OSM crossing, both reads),
<plate>/reads.json (every job of the plate with both reads and its outcome), jobs.json and reads/ (the inputs, copied),
summary.csv and README.md (per plate: crossings picked before and after, the reads that disagreed).
"""
import collections, csv, datetime, glob, json, os, shutil, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _ws  # noqa: E402
import seams as S  # noqa: E402
from names import key, base  # noqa: E402

SP = _ws.DATA
OUT = 'picks22_complete'
AGREE_PX, OSM_M = 60.0, 45.0
NOT_1922 = ('Central Parkway', 'Viaduct')   # Central Parkway: built over the canal bed after 1922 (the plates show the canal); a viaduct: where a street meets its own viaduct is a name change, not a crossing, and the viaducts here postdate 1922


def controls_px(pid):
    """the plate's current controls (pixel), as its model uses them"""
    import pickle
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'joint'))
    import jointlib as J
    if pid == '22-35N':
        sys.path.insert(0, _ws.CODE + 'cuf')
        import common as C
        d = pickle.load(open(SP + 'cuf/corr.pkl', 'rb')); B = np.asarray(d['B'], float)
        x, y = C.ben2px(B[:, 0], B[:, 1]); return np.c_[x, y]
    return np.asarray(pickle.load(open(SP + J.base_path(pid), 'rb'))['X'], float)


def two_names(osm_names):
    out, seen = [], set()
    for n in osm_names:
        b = base(key(n))
        if b not in seen:
            seen.add(b); out.append(n)
    return out[:2]


def main(jd):
    jobs = json.load(open(os.path.join(jd, 'jobs.json'), encoding='utf8'))
    info = json.load(open(os.path.join(jd, 'info.json'), encoding='utf8'))
    reads = collections.defaultdict(dict)
    for f in sorted(glob.glob(os.path.join(jd, 'reads', '*.json'))):
        g = os.path.basename(f)[:-5]
        for r in json.load(open(f, encoding='utf8')):
            reads[r['job']][g[0]] = dict(r, group=g)
    os.makedirs(SP + OUT + '/reads', exist_ok=True)
    shutil.copy(os.path.join(jd, 'jobs.json'), SP + OUT + '/jobs.json')
    for f in glob.glob(os.path.join(jd, 'reads', '*.json')):
        shutil.copy(f, SP + OUT + '/reads/')
    W = {}
    per = collections.defaultdict(list)
    for j, v in sorted(jobs.items()):
        p = v['plate']; ra, rb = reads[j].get('A'), reads[j].get('B')
        fa = bool(ra and ra.get('found') and ra.get('x') is not None); fb = bool(rb and rb.get('found') and rb.get('x') is not None)
        rec = dict(job=j, osm=v['osm'], osm_names=v['osm_names'], predicted=v['predicted'], reads=[r for r in (ra, rb) if r])
        if any(w in n for n in v['osm_names'] for w in NOT_1922):
            out, why = 'not a 1922 street', ('Central Parkway: the canal bed in 1922 (not a street)' if any('Central Parkway' in n for n in v['osm_names']) else 'a viaduct: a name change along the street, not a crossing')
        elif ra is None or rb is None:
            out, why = 'unread', 'a read is missing'
        elif fa and fb:
            d = float(np.hypot(ra['x'] - rb['x'], ra['y'] - rb['y'])); rec['spread_px'] = round(d, 1)
            if d <= AGREE_PX:
                x, y = (ra['x'] + rb['x']) / 2, (ra['y'] + rb['y']) / 2
                if p not in W:
                    W[p] = S.plate_world(p)
                E, N = W[p](x, y); off = float(np.hypot(E - v['osm'][0], N - v['osm'][1])); rec['osm_off_m'] = round(off, 1)
                rec.update(x=round(x, 1), y=round(y, 1))
                out, why = ('picked', f'reads {d:.0f} px apart') if off <= OSM_M else ('far from OSM', f'{off:.0f} m from its OSM crossing under the current model')
            else:
                out, why = 'disagree', f'the reads are {d:.0f} px apart'
        elif fa or fb:
            out, why = 'disagree', f"read {'1' if fa else '2'} found it, read {'2' if fa else '1'} did not"
        else:
            out, why = 'not found', 'neither read found the two streets meeting'
        rec.update(outcome=out, why=why)
        per[p].append(rec)
    # duplicates: a new pick within 60 px of one of the plate's current controls (the same plate crossing, already a
    # control under another name or OSM node), or of another new pick (two OSM nodes for one plate crossing; the one
    # nearer its OSM point kept). A new pick near an existing pick that is not a control is kept: the existing pick's
    # printed names did not match OSM, and the new read supplies the OSM crossing.
    for p, R in per.items():
        Xc = controls_px(p)
        for r in R:
            if r['outcome'] == 'picked' and len(Xc):
                d = np.hypot(*(Xc - [r['x'], r['y']]).T); i = int(np.argmin(d))
                if d[i] <= AGREE_PX:
                    r.update(outcome='already picked', why=f"{d[i]:.0f} px from the current control at ({Xc[i][0]:.0f}, {Xc[i][1]:.0f})")
        new = sorted([r for r in R if r['outcome'] == 'picked'], key=lambda r: r['osm_off_m'])
        kept = []
        for r in new:
            k = next((q for q in kept if np.hypot(q['x'] - r['x'], q['y'] - r['y']) <= AGREE_PX), None)
            if k:
                r.update(outcome='duplicate', why=f"the same plate crossing as {k['job']} (nearer its OSM point)")
            else:
                kept.append(r)
    rows = []
    for p in S.plate_ids():
        R = per.get(p, [])
        picks = []
        for r in R:
            if r['outcome'] != 'picked':
                continue
            a, b = two_names(r['osm_names'])
            ra, rb = r['reads']
            picks.append(dict(a=a, b=b, x=r['x'], y=r['y'], kind=ra.get('kind') or rb.get('kind'), osm=r['osm'], osm_names=r['osm_names'],
                              printed=[ra.get('printed'), rb.get('printed')], spread_px=r['spread_px'], osm_off_m=r['osm_off_m'], job=r['job'],
                              confidence=[ra.get('confidence'), rb.get('confidence')], note=' | '.join(x for x in (ra.get('note'), rb.get('note')) if x)))
        os.makedirs(SP + f'{OUT}/{p}', exist_ok=True)
        json.dump(dict(sheet=p, made=datetime.datetime.now().isoformat(timespec='seconds'), by='tools/sanborn/complete/collect.py',
                       rule='two independent reads, kept when they agree within 60 px (their mean) and lie within 45 m of the OSM crossing under the current model',
                       intersections=picks), open(SP + f'{OUT}/{p}/picks.json', 'w', encoding='utf8', newline='\n'), indent=1)
        json.dump(R, open(SP + f'{OUT}/{p}/reads.json', 'w', encoding='utf8', newline='\n'), indent=1)
        c = collections.Counter(r['outcome'] for r in R)
        i = info.get(p, {})
        before = i.get('covered', 0)
        rows.append(dict(plate=p, crossings_on_plate=i.get('on_plate'), realigned=i.get('realigned'), picked_before=before, read=len(R),
                         picked_new=c['picked'], picked_after=before + c['picked'], not_found=c['not found'], disagree=c['disagree'],
                         far_from_osm=c['far from OSM'], not_1922=c['not a 1922 street'], duplicate=c['duplicate'] + c['already picked'], unread=c['unread']))
    with open(SP + f'{OUT}/summary.csv', 'w', newline='', encoding='utf8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)
    write_readme(rows, per)
    for r in rows:
        print(r)
    return rows, per


def write_readme(rows, per):
    T = {k: sum(r[k] or 0 for r in rows) for k in rows[0] if k != 'plate'}
    L = ['# The complete set of named crossings on the 1922 plates (Part 1, ' + datetime.date.today().isoformat() + ')', '',
         "Rule 12 (`docs/sanborn/RULES.md`): every plate is fitted on every named crossing it shows. The crossings were "
         "listed from OSM: every crossing of two differently named streets that falls on the plate under its current model, "
         "the realigned streets of rule 3 left out (renamed ones kept: rule 3 aliases them). A crossing counts as picked "
         "before when an existing pick (sbg/picks22) with the same names, aliased, lies within 45 m of it. Each of the others "
         "was read twice, by two readers working independently (`tools/sanborn/complete/READERS.md`), and kept when both "
         "found it within 60 px of each other and within 45 m of its OSM crossing under the plate's current model.", '',
         '| Plate | On the plate | Realigned | Picked before | Read | New picks | Picked after | Not found | Reads disagree | Over 45 m from OSM | Canal bed | Duplicate |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows + [dict(plate='**All**', **T)]:
        L.append(f"| {r['plate']} | {r['crossings_on_plate']} | {r['realigned']} | {r['picked_before']} | {r['read']} | {r['picked_new']} | "
                 f"{r['picked_after']} | {r['not_found']} | {r['disagree']} | {r['far_from_osm']} | {r['not_1922']} | {r['duplicate']} |")
    L += ['', '"Not found": neither reader found the two streets meeting near the crossing (most are streets laid out or '
          'joined after 1922). The reads that disagreed, and the picks left out as far from OSM:', '']
    for p in sorted(per):
        for r in per[p]:
            if r['outcome'] in ('disagree', 'far from OSM', 'unread'):
                L.append(f"- {p} `{r['job']}` {' & '.join(r['osm_names'])}: {r['why']}")
    open(SP + f'{OUT}/README.md', 'w', encoding='utf8', newline='\n').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main(sys.argv[1])
