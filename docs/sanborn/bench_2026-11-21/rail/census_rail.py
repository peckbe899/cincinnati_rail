"""Batch-wide rail census (bench_2026-11-21/rail, 21 Nov 2026). Read-only on the repo.

    cd data/sanborn
    python bench_2026-11-21/rail/census_rail.py

Reads unet_data/run_plates.json, run_plates.log (last entry per plate), N_rail_rule.json, N_pred_area_ng1.png,
cufp/N/source.json, cufp/N/png_alpha_s4.npy. Writes bench_2026-11-21/rail/census/census.csv, census.json and
key_candidates.json / hook_candidates.json (tracks to look at)."""
import os, re, json, csv
import numpy as np, cv2
from scipy.spatial import cKDTree

OUT = 'bench_2026-11-21/rail/census'; os.makedirs(OUT, exist_ok=True)
S = json.load(open('unet_data/run_plates.json', encoding='utf8'))
order = lambda n: (int(re.match(r'\d+', n).group()), n)


def plen(p):
    p = np.asarray(p, float); return float(np.hypot(*np.diff(p, axis=0).T).sum()) if len(p) > 1 else 0.0


# last log entry per plate: tick counts
log = open('unet_data/run_plates.log', encoding='utf8', errors='replace').read()
ticks = {}
for m in re.finditer(r'===== plate (\S+) .*?\n(.*?)(?======|\Z)', log, re.S):
    t = re.search(r'clear ticks (\d+) faint ticks (\d+) ticks in rows (\d+) links added by carrying rows on (\d+)', m.group(2))
    if t: ticks[m.group(1)] = [int(v) for v in t.groups()]

rows = []; keyc = []; hookc = []
for N in sorted(S, key=order):
    s = S[N]; r = dict(plate=N, state=s.get('state'), ben_rail=s.get('ben_rail'), ink_px=s.get('ink_px'), railroad_px=s.get('railroad_px'), streetcar_px=s.get('streetcar_px'), secs=s.get('seconds'))
    src = f'cufp/{N}/source.json'; r['source'] = 'pdf' if os.path.exists(src) else 'cut'
    al = np.load(f'cufp/{N}/png_alpha_s4.npy'); H4, W4 = al.shape; r['paper_mpx'] = round(float((al > 0).sum()) * 16 / 1e6, 2)
    im = cv2.imread(f'cufp/22-{N}.jpg', cv2.IMREAD_REDUCED_GRAYSCALE_8); H, W = im.shape[0] * 8, im.shape[1] * 8; r['W'], r['H'] = W, H
    tk = ticks.get(N, [None] * 4); r['clear_ticks'], r['faint_ticks'], r['ticks_in_rows'], r['grown_links'] = tk
    T = json.load(open(f'unet_data/{N}_rail_rule.json', encoding='utf8'))['tracks']
    rr = [np.asarray(t['pts'], float) for t in T if t['kind'] == 'railroad']; sc = [np.asarray(t['pts'], float) for t in T if t['kind'] == 'streetcar']
    Lrr = [plen(p) for p in rr]; Lsc = [plen(p) for p in sc]
    r.update(n_rr=len(rr), len_rr=round(sum(Lrr)), n_rr_short=sum(l < 300 for l in Lrr), med_rr=round(float(np.median(Lrr))) if Lrr else 0,
             n_sc=len(sc), len_sc=round(sum(Lsc)), n_sc_short=sum(l < 300 for l in Lsc), med_sc=round(float(np.median(Lsc))) if Lsc else 0)
    r['rr_px_per_mpx'] = round(r['railroad_px'] / max(r['paper_mpx'], 1e-6)); r['sc_px_per_mpx'] = round(r['streetcar_px'] / max(r['paper_mpx'], 1e-6))
    # area net: share of rule railroad length lying where P(block) > 0.5, and isolated short tracks there
    A = cv2.imread(f'unet_data/{N}_pred_area_ng1.png', 0)
    allpts = np.vstack([p for p in rr]) if rr else np.zeros((0, 2))
    inblk = 0.0; iso = 0
    for i, p in enumerate(rr):
        L = Lrr[i]; S_ = np.vstack([p[k][None] + np.linspace(0, 1, max(2, int(np.hypot(*(p[k + 1] - p[k])) / 4) + 1))[:, None] * (p[k + 1] - p[k])[None] for k in range(len(p) - 1)])
        f = 0.0
        if A is not None:
            q = np.clip((S_ / 2).round().astype(int), 0, [A.shape[1] - 1, A.shape[0] - 1]); f = float((A[q[:, 1], q[:, 0]] > 127).mean()); inblk += f * L
        # isolated: no point of any other railroad track within 150 px
        others = [rr[j] for j in range(len(rr)) if j != i]
        d = min((cKDTree(S_).query(np.vstack([o for o in others]))[0].min() if others else 1e9), 1e9)
        lone = d > 150
        iso += lone and L < 600
        ang = np.degrees(np.arctan2(*(p[-1] - p[0])[::-1])) % 180; horiz = min(ang, 180 - ang) <= 3 or abs(ang - 90) <= 3
        x, y = S_.mean(0); edge = min(x / W, 1 - x / W, y / H, 1 - y / H)
        if lone and L < 600 and f >= 0.8: hookc.append(dict(plate=N, len=round(L), inblock=round(f, 2), a=[round(v) for v in p[0]], b=[round(v) for v in p[-1]]))
        if r['source'] == 'pdf' and L < 600 and horiz and edge < 0.25: keyc.append(dict(plate=N, kind='railroad', len=round(L), a=[round(v) for v in p[0]], b=[round(v) for v in p[-1]], lone=bool(lone)))
    for p, L in zip(sc, Lsc):
        ang = np.degrees(np.arctan2(*(p[-1] - p[0])[::-1])) % 180; horiz = min(ang, 180 - ang) <= 3
        x, y = p.mean(0); edge = min(x / W, 1 - x / W, y / H, 1 - y / H)
        if r['source'] == 'pdf' and L < 600 and horiz and edge < 0.25: keyc.append(dict(plate=N, kind='streetcar', len=round(L), a=[round(v) for v in p[0]], b=[round(v) for v in p[-1]]))
    r['rr_len_in_block_share'] = round(inblk / max(sum(Lrr), 1e-6), 3); r['rr_lone_short'] = int(iso)
    rows.append(r)

keys = list(rows[0].keys())
with open(f'{OUT}/census.csv', 'w', newline='', encoding='utf8') as f:
    w = csv.DictWriter(f, keys); w.writeheader(); [w.writerow(r) for r in rows]
json.dump(rows, open(f'{OUT}/census.json', 'w'), indent=1)
json.dump(keyc, open(f'{OUT}/key_candidates.json', 'w'), indent=1); json.dump(hookc, open(f'{OUT}/hook_candidates.json', 'w'), indent=1)
print(f'{len(rows)} plates; key candidates {len(keyc)}; lone short in-block railroad tracks {len(hookc)}')
for r in rows:
    print(f"{r['plate']:5s} {r['source']:3s} {r['W']:5d}x{r['H']:<5d} paper {r['paper_mpx']:5.1f}M ink {r['ink_px'] / 1e6:4.2f}M | rr {r['railroad_px']:7d} px ({r['rr_px_per_mpx']:5d}/M) {r['n_rr']:3d} tr {r['len_rr']:6d} px short {r['n_rr_short']:2d} lone {r['rr_lone_short']:2d} inblk {r['rr_len_in_block_share']:.2f} | sc {r['streetcar_px']:6d} px {r['n_sc']:3d} tr {r['len_sc']:6d} px short {r['n_sc_short']:2d} | ticks c{r['clear_ticks']} f{r['faint_ticks']} row{r['ticks_in_rows']}" + (' BEN' if r['ben_rail'] else ''))
