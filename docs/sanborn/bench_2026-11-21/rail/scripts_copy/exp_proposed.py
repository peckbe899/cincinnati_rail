"""The proposed tracing changes together, measured (bench_2026-11-21/rail). Read-only on the repo; writes exp/proposed/.
  P1 = batch railroad tracing + F1 (drop railroad tracks < 600 px with no other railroad track within 60 px)
       + F2 (drop tracks inside the printed KEY, census/key_boxes.json) + streetcar reach 300 px (V1)
  P2 = P1 with streetcar reach 400 px, across 25 px, a lone piece >= 250 px kept, curved pieces traced (V4)
On 44 (no-map bins, as an unplaced plate; and with-map bins) and 1A: scored. On every other batch plate (its own
unet_data/N_bins.png, rules only there): track counts and lengths before and after.
    cd data/sanborn
    python bench_2026-11-21/rail/exp_proposed.py [--census]"""
import sys, json, os, re
sys.path.insert(0, 'bench_2026-11-21/rail')
import numpy as np, cv2
import rail_tracks_copy as rt
from rail_variants import streetcar_tracks_v2, drop_lone_short, drop_in_box
from score_rail_bench import score, summary_lines
OUT = 'bench_2026-11-21/rail/exp/proposed'; os.makedirs(OUT, exist_ok=True)
KB = {k['plate']: k['box'] for k in json.load(open('bench_2026-11-21/rail/census/key_boxes.json')) if k.get('score') and k['score'] >= 0.5}
VARS = {'P1': dict(reach=300), 'P2': dict(reach=400, across=25, single=250, curved=True)}


def proposed(N, B, v, rr_tracks=None):
    """rr_tracks: the batch's railroad tracks for this plate (rail_tracks.railroad_tracks of the same bins, so identical
    on plates without Ben's tracks; passed in to save the slow thinning)"""
    if rr_tracks is None: rr_tracks = [dict(kind='railroad', src='rule', pts=p.tolist()) for p in rt.railroad_tracks((B == 4).astype(np.uint8))]
    car = streetcar_tracks_v2((B == 5).astype(np.uint8), **VARS[v])
    tr = list(rr_tracks) + [dict(kind='streetcar', src='rule', pts=p.tolist()) for p in car]
    tr, d1 = drop_lone_short(tr, 600, 60)
    d2 = []
    if N in KB: tr, d2 = drop_in_box(tr, KB[N])
    return tr, d1, d2


if '--census' not in sys.argv:
    for N, bp, tp, tag in (('44', 'bench_2026-11-21/rail/runs/44_nomap_bins.png', 'picks22_guided/22-44/rail_ben.page_2026-11-21.json', 'nomap'),
                           ('44', 'bench_2026-11-21/rail/runs/44_map_bins.png', 'picks22_guided/22-44/rail_ben.page_2026-11-21.json', 'map'),
                           ('1A', 'bench_2026-11-21/rail/runs/1A_bins.png', 'picks22_guided/22-1A/rail_ben.json', 'nomap')):
        B = cv2.imread(bp, 0); H, W = B.shape; TJ = json.load(open(tp, encoding='utf8'))
        for v in VARS:
            tr, d1, d2 = proposed(N, B, v); res = score(N, tr, TJ, H, W)
            json.dump(dict(plate=N, note=f'bench proposed {v} on {tag} bins', tracks=tr), open(f'{OUT}/{N}_{tag}_{v}_rail_rule.json', 'w'))
            json.dump(res, open(f'{OUT}/score_{N}_{tag}_{v}.json', 'w'), indent=1)
            print(f'== {N} {tag} {v} (F1 dropped {len(d1)}, KEY dropped {len(d2)})'); [print(l) for l in summary_lines(res)]
else:
    S = json.load(open('unet_data/run_plates.json', encoding='utf8')); order = lambda n: (int(re.match(r'\d+', n).group()), n); rows = []
    for N in sorted(S, key=order):
        if N in ('44', '1A'): continue
        B = cv2.imread(f'unet_data/{N}_bins.png', 0); old = json.load(open(f'unet_data/{N}_rail_rule.json', encoding='utf8'))['tracks']
        r = dict(plate=N)
        for k in ('railroad', 'streetcar'):
            r[f'batch_{k}_n'] = sum(t['kind'] == k for t in old); r[f'batch_{k}_px'] = round(sum(rt.plen(t['pts']) for t in old if t['kind'] == k))
        for v in VARS:
            tr, d1, d2 = proposed(N, B, v, [t for t in old if t['kind'] == 'railroad'])
            for k in ('railroad', 'streetcar'):
                r[f'{v}_{k}_n'] = sum(t['kind'] == k for t in tr); r[f'{v}_{k}_px'] = round(sum(rt.plen(t['pts']) for t in tr if t['kind'] == k))
            r[f'{v}_f1'] = len(d1); r[f'{v}_key'] = len(d2)
        rows.append(r); print(json.dumps(r), flush=True)
    json.dump(rows, open(f'{OUT}/census_proposed.json', 'w'), indent=1)
    tot = {k: sum(r[k] for r in rows) for k in rows[0] if k != 'plate'}; print('TOTALS', json.dumps(tot))
