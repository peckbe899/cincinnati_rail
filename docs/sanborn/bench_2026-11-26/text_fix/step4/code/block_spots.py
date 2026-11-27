"""block_spots.py (text_fix/step4, 27 Nov 2026): the hand-off's named misses, finder3 against finder4.
  1. Block 28 on plate 44 and block 15 on plate 1A: per figure box, the ink (LAB L < 140) and the share of it the mask calls
     text (codes 2,3), and the bins it lands in with the mask taken first (44: 44_map_ben_after and 44_map_after; 1A:
     1A_now_after). Figure boxes: 44 '2' and '8' from finder4's 44_blocks.json (block step B's read); 1A '1' from
     finder4's 1A_blocks.json (B saw it and rejected it as a lone 1), '5' by eye from the scan. A box also holds the
     lot and street lines that cross the figure, so a share of 1.0 is not expected.
  2. The streetcar error under the 15 on 1A: rule streetcar track length more than 10 px from every Ben streetcar track
     (samples every 2 px, as score_rail.py), inside the window round the 15 and on the whole plate, for every run of 1A_now.
  3. The same off-Ben streetcar length on 44_map and 5_now/5_nets21/5_none, for the record.
    cd data/sanborn; python -B bench_2026-11-26/text_fix/step4/code/block_spots.py
Writes step4/scores/block_spots.json and block_spots.txt."""
import json, os
import numpy as np, cv2
from scipy.spatial import cKDTree
SP = os.getcwd().replace('\\', '/') + '/'; ST = SP + 'bench_2026-11-26/text_fix/step4/'
FIGS = {'44': {'28': {'2': [1128, 4839, 1167, 4892], '8': [1169, 4841, 1204, 4892]}},
        '1A': {'15': {'1': [4026, 2102, 4060, 2224], '5': [4075, 2098, 4150, 2228]}}}
RUNS = {'44': ['44_map_ben_after', '44_map_after'], '1A': ['1A_now_after']}
WIN15 = (3990, 2080, 4180, 2260)
NAMES = {0: 'speck', 1: 'block line', 2: 'lot line', 3: 'bldg outline', 4: 'railroad', 5: 'streetcar', 6: 'pipe', 7: 'sewer', 8: 'text', 9: 'not sorted'}
out = {'figures': {}, 'streetcar_off_ben': {}}; L = []


def samp(p, step=2.0):
    p = np.asarray(p, float); S_ = [p[:1]]
    for a, b in zip(p[:-1], p[1:]):
        n = max(1, int(np.ceil(np.hypot(*(b - a)) / step))); S_.append(a + np.linspace(0, 1, n + 1)[1:, None] * (b - a))
    return np.vstack(S_)


for N, blocks in FIGS.items():
    im = cv2.imread(SP + f'cufp/22-{N}.jpg'); ink = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0] < 140
    tc = {S: cv2.imread(ST + f'masks/{S}/{N}_text.png', cv2.IMREAD_UNCHANGED) for S in ('f3', 'f4')}
    bins = {(S, r): cv2.imread(ST + f'runs/bins/{S}/{r}.png', 0) for S in ('f3', 'f4') for r in RUNS[N]}
    bins.update({('none', r.replace('_after', '_before')): cv2.imread(ST + f'runs/bins/f3/{r.replace("_after", "_before")}.png', 0) for r in RUNS[N]})
    for blk, figs in blocks.items():
        for fg, (x0, y0, x1, y1) in figs.items():
            k = ink[y0:y1, x0:x1]; n = int(k.sum()); o = dict(box=[x0, y0, x1, y1], ink_px=n)
            for S in ('f3', 'f4'): o[f'{S}_text_share'] = round(float((np.isin(tc[S][y0:y1, x0:x1], (2, 3)) & k).sum() / max(1, n)), 3)
            for (S, r), B in bins.items():
                b = B[y0:y1, x0:x1][k]; h = np.bincount(b, minlength=10)
                o[f'{S}:{r}'] = {NAMES[i]: round(float(h[i] / max(1, n)), 3) for i in range(10) if h[i]}
            out['figures'][f'{N} block {blk} figure {fg}'] = o
            L.append(f"{N} block {blk}, figure '{fg}' box {[x0, y0, x1, y1]}: ink {n} px | text share f3 {o['f3_text_share']} -> f4 {o['f4_text_share']}")
            for (S, r) in bins:
                if S != 'none': L.append(f"    {S} {r:18s} bins: {o[f'{S}:{r}']}")
            for (S, r) in bins:
                if S == 'none': L.append(f"    no mask {r:15s} bins: {o[f'{S}:{r}']}")
for N, runs in (('1A', ['1A_now']), ('44', ['44_map', '44_nomap', '44_nets44']), ('5', ['5_now', '5_nets21', '5_none'])):
    B = [samp(t['pts']) for t in json.load(open(SP + f'picks22_guided/22-{N}/rail_ben.json', encoding='utf8'))['tracks'] if t['kind'] == 'streetcar' and len(t['pts']) > 1]
    BT = cKDTree(np.vstack(B))
    for run in runs:
        for S, when, suf in (('f3', 'before', '_tracks.json'), ('f3', 'after', '_tracks.json'), ('f3', 'afterstrict', '_tracks.json'), ('f4', 'after', '_tracks.json'), ('f4', 'afterstrict', '_tracks.json')):
            f = ST + f'runs/bins/{S}/{run}_{when}{suf}'
            if not os.path.exists(f): continue
            tr = [samp(t['pts']) for t in json.load(open(f, encoding='utf8'))['tracks'] if t['kind'] == 'streetcar' and len(t['pts']) > 1]
            if not tr: continue
            A = np.vstack(tr); off = A[BT.query(A)[0] > 10]
            inw = off[(off[:, 0] >= WIN15[0]) & (off[:, 0] < WIN15[2]) & (off[:, 1] >= WIN15[1]) & (off[:, 1] < WIN15[3])] if N == '1A' else off[:0]
            tag = 'no mask' if when == 'before' else f'{S} {when}'
            o = dict(off_ben_px=int(len(off) * 2), off_ben_px_at_15=int(len(inw) * 2) if N == '1A' else None, rule_px=int(len(A) * 2))
            out['streetcar_off_ben'][f'{run} {tag}'] = o
            L.append(f"streetcar off Ben (> 10 px) {run:9s} {tag:16s}: {o['off_ben_px']:5d} px of {o['rule_px']:6d}" + (f" | under the 15 on 1A: {o['off_ben_px_at_15']} px" if N == '1A' else ''))
json.dump(out, open(ST + 'scores/block_spots.json', 'w', encoding='utf8', newline='\n'), indent=1)
open(ST + 'scores/block_spots.txt', 'w', encoding='utf8', newline='\n').write('\n'.join(L) + '\n'); print('\n'.join(L))
