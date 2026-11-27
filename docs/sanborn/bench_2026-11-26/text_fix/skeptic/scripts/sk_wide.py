"""sk_wide.py (skeptic): finder4's changes on the sealed plates OUTSIDE every labelled area (scopes and full crops),
where no truth scores them. Counts them by step and draws a seeded random sample for the eye check.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/skeptic/scripts/sk_wide.py OUT.json SPOTS_PREFIX [--n 24]

New text = finder4 text (codes 2, 3) that finder3 did not call text (the gate's masks). Pieces: 8-connected.
Step of a piece: 'ditto' when it meets a box of finder4's ditto changes (N_text.json), 'B' when it meets a number box
of block step B, else 'A' (block step A, the only other step).
Sample (random.Random('skeptic-wide')): n pieces drawn with chance in proportion to their pixels (the share of wrong
pixels), and n pieces drawn evenly (the share of wrong pieces). Pieces under 4 px are left out of the draws.
Writes SPOTS_PREFIX_{px,even}_k.json (8 spots per sheet) for sk_pic.py --panels 2.
"""
import json, random, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
from scipy import ndimage as ndi
TR = 'bench_2026-11-26/text_fix/sealed_final'; G = 'bench_2026-11-26/text_fix/gate/out'


def main():
    a = sys.argv[1:]; outp, pref = a[0], a[1]; n = int(a[a.index('--n') + 1]) if '--n' in a else 24
    crops = json.load(open(f'{TR}/crops.json')); pieces = []; per = {}
    plates = sorted({c['plate'] for c in crops.values()}, key=lambda s: (len(s), s))
    for N in plates:
        A = cv2.imread(f'{G}/finder3/{N}_text.png', cv2.IMREAD_UNCHANGED); B = cv2.imread(f'{G}/finder4/{N}_text.png', cv2.IMREAD_UNCHANGED)
        H, W = A.shape; lab_area = np.zeros((H, W), bool)
        for c in crops.values():
            if c['plate'] != N: continue
            if c.get('kind') == 'full': x0, y0, x1, y1 = c['win']; lab_area[y0:y1, x0:x1] = True
            else:
                for x0, y0, x1, y1 in c['scope']: lab_area[y0:y1 + 1, x0:x1 + 1] = True
        new = np.isin(B, (2, 3)) & ~np.isin(A, (2, 3))
        J = json.load(open(f'{G}/finder4/{N}_text.json'))
        dmask = np.zeros((H, W), bool); bmask = np.zeros((H, W), bool)
        for ch in J['ditto']['changes']:
            x0, y0, x1, y1 = ch['box']; dmask[y0:y1 + 1, x0:x1 + 1] = True
        for ch in J['block']['B']['changes']:
            x0, y0, x1, y1 = [int(round(v)) for v in ch['box']]; bmask[max(0, y0 - 8):y1 + 9, max(0, x0 - 8):x1 + 9] = True
        lab, nl = ndi.label(new, structure=np.ones((3, 3)))
        cnt = dict(new_px=int(new.sum()), new_px_in_labelled=int((new & lab_area).sum()), by_step={})
        for j, sl in enumerate(ndi.find_objects(lab), 1):
            m = lab[sl] == j; px = int(m.sum())
            inl = bool((lab_area[sl] & m).any())
            step = 'ditto' if (dmask[sl] & m).any() else ('B' if (bmask[sl] & m).any() else 'A')
            if not inl:
                d = cnt['by_step'].setdefault(step, dict(pieces=0, px=0)); d['pieces'] += 1; d['px'] += px
                pieces.append(dict(plate=N, box=[int(sl[1].start), int(sl[0].start), int(sl[1].stop), int(sl[0].stop)], px=px, step=step,
                                   from_codes={str(int(k)): int(v) for k, v in zip(*np.unique(A[sl][m], return_counts=True))}))
        per[N] = cnt; print(N, json.dumps(cnt), flush=True)
    rng = random.Random('skeptic-wide')
    pool = [p for p in pieces if p['px'] >= 4]
    w = [p['px'] for p in pool]
    px_draw = []
    seen = set()
    while len(px_draw) < n:
        p = rng.choices(range(len(pool)), weights=w, k=1)[0]
        if p in seen: continue
        seen.add(p); px_draw.append(p)
    even = [i for i in rng.sample(range(len(pool)), n + len(seen)) if i not in seen][:n]
    O = dict(per_plate=per, total_by_step={}, n_pieces=len(pieces), n_pool=len(pool),
             draw_px=[dict(pool[i], k=k) for k, i in enumerate(px_draw)], draw_even=[dict(pool[i], k=k) for k, i in enumerate(even)])
    for c in per.values():
        for s, d in c['by_step'].items():
            t = O['total_by_step'].setdefault(s, dict(pieces=0, px=0)); t['pieces'] += d['pieces']; t['px'] += d['px']
    O['new_px_total'] = sum(c['new_px'] for c in per.values()); O['new_px_in_labelled'] = sum(c['new_px_in_labelled'] for c in per.values())
    json.dump(O, open(outp, 'w'), indent=1)
    for nm in ('px', 'even'):
        D = O[f'draw_{nm}']
        for k in range(0, len(D), 8):
            spots = []
            for p in D[k:k + 8]:
                x0, y0, x1, y1 = p['box']; cx, cy = (x0 + x1) // 2, (y0 + y1) // 2; h = max(35, (x1 - x0) // 2 + 20, (y1 - y0) // 2 + 20)
                spots.append(dict(plate=p['plate'], box=[max(0, cx - h), max(0, cy - h), cx + h, cy + h], zoom=3 if h <= 60 else 2,
                                  label=f"{nm[0].upper()}{p['k']:02d} step {p['step']} {p['px']}px from {p['from_codes']}"))
            json.dump(spots, open(f'{pref}_{nm}_{k // 8}.json', 'w'))
    print('total new px', O['new_px_total'], 'in labelled areas', O['new_px_in_labelled'], 'outside by step', O['total_by_step'])


if __name__ == '__main__':
    main()
