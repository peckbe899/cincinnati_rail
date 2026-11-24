"""review-labels, 24 Nov 2026: how the line target treats the sides of Ben's alleys and narrow streets.

    python -B alley_sides.py LABEL_DIR N STREETMAP.json OUT.json

A printed or drawn line of Ben's is an 'alley side' when score_pseudo.py's narrow-street ground (at most 40 ft wide, or a
narrow face) lies within 4 half px of it along at least half its length; the rest are 'other'. For each group: length,
and the share taught positive at the centre, with a negative within 2 px of the centre, and left 255. Also: the share
of each group's length lying inside the area label's block (1), i.e. a block line the area label teaches as block interior.
"""
import json, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_pseudo as S


def main():
    d, N, smf, out = sys.argv[1:5]
    sm = json.load(open(smf, encoding='utf8')); lab = cv2.imread(f'{d}/{N}/label.png', cv2.IMREAD_UNCHANGED); t = cv2.imread(f'{d}/{N}/lines.png', cv2.IMREAD_UNCHANGED)
    meta = json.load(open(f'{d}/{N}/meta.json', encoding='utf8')); ftpi = meta.get('ft_per_inch') or 100
    h, w = lab.shape; H, W = t.shape; T = S.truth(N, sm, h, w, ftpi)
    nar = cv2.dilate(T['NAR'].astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    negnear = cv2.dilate((t == 0).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    blk = cv2.dilate((lab == 1).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0       # a block line lying in taught block (1 half px to spare)
    g = {k: dict(lines=0, len=0, pos=0, touched=0, unscored=0, in_block=0) for k in ('alley_side', 'other')}; listed = []
    for i, l in enumerate(sm['lines']):
        if l['kind'] not in ('printed', 'drawn'): continue
        a, b = np.array(l['a'], float), np.array(l['b'], float); n = max(2, int(np.hypot(*(b - a))) + 1); q = a + np.outer(np.linspace(0, 1, n), b - a)
        x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1)
        xh, yh = np.clip(x // 2, 0, w - 1), np.clip(y // 2, 0, h - 1)
        k = 'alley_side' if nar[yh, xh].mean() >= 0.5 else 'other'; v = t[y, x]; G = g[k]
        G['lines'] += 1; G['len'] += n; G['pos'] += int((v == 1).sum()); G['touched'] += int(negnear[y, x].sum()); G['unscored'] += int((v == 255).sum()); G['in_block'] += int(blk[yh, xh].sum())
        if k == 'alley_side': listed.append(dict(line=i, a=l['a'], b=l['b'], len=n, pos=round(float((v == 1).mean()), 3), neg_within_2px=round(float(negnear[y, x].mean()), 3), in_block=round(float(blk[yh, xh].mean()), 3)))
    res = dict(plate=N, labels=d, streetmap=smf, groups={k: dict(lines=G['lines'], length_px=G['len'], taught_positive=round(G['pos'] / max(1, G['len']), 4), negative_within_2px=round(G['touched'] / max(1, G['len']), 4),
                                                                  left_255=round(G['unscored'] / max(1, G['len']), 4), inside_taught_block=round(G['in_block'] / max(1, G['len']), 4)) for k, G in g.items()},
               alley_side_lines=listed)
    json.dump(res, open(out, 'w', encoding='utf8', newline='\n'), indent=1); print(N, d, json.dumps(res['groups']))


if __name__ == '__main__':
    main()
