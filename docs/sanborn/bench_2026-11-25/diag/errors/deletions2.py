"""Ben's deleted lines on 5 and 1A: how much of their length lies within 5 px of a kept line running the same way
(20 deg): a line he replaced or trimmed, not 'no street here'; and the deleted lines mostly on text, by distance to the
nearest kept line.   python -B deletions2.py   (read-only; prints)"""
import json, sys
import numpy as np, cv2
from scipy.spatial import cKDTree
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
def sample(lines):
    P, D, ix = [], [], []
    for k, l in enumerate(lines):
        a = np.array(l['a'], float); b = np.array(l['b'], float); L = np.hypot(*(b - a))
        if L < 1: continue
        m = int(np.ceil(L)); t = (np.arange(m) + 0.5) / m; P.append(a + np.outer(t, b - a)); D.append(np.repeat(((b - a) / L)[None], m, 0)); ix.append(np.full(m, k))
    return np.vstack(P), np.vstack(D), np.concatenate(ix)
for n in ('5', '1A'):
    d = json.load(open(SP + f'picks22_guided/22-{n}/edges_ben.json', encoding='utf8'))['lines']
    bins = cv2.imread(SP + f'unet_data/{n}_bins.png', cv2.IMREAD_UNCHANGED)
    kept = [l for l in d if l.get('verdict') == 'ok']; wrong = [l for l in d if l.get('verdict') == 'wrong' and l.get('src') != 'sheet']
    Pk, Dk, _ = sample(kept); Pw, Dw, iw = sample(wrong); t = cKDTree(Pk)
    dd, jj = t.query(Pw, k=32, distance_upper_bound=5.0); ok = np.isfinite(dd); j2 = np.where(ok, jj, 0)
    par = (ok & (np.abs((Dk[j2] * Dw[:, None, :]).sum(2)) >= np.cos(np.radians(20)))).any(1)
    per = np.bincount(iw, par.astype(float), minlength=len(wrong)) / np.maximum(np.bincount(iw, minlength=len(wrong)), 1)
    # text per line
    x = np.clip(Pw[:, 0].round().astype(int), 3, bins.shape[1] - 4); y = np.clip(Pw[:, 1].round().astype(int), 3, bins.shape[0] - 4)
    tx = np.zeros(len(Pw), bool)
    for dy in range(-3, 4):
        for dx in range(-3, 4): tx |= bins[y + dy, x + dx] == 8
    pert = np.bincount(iw, tx.astype(float), minlength=len(wrong)) / np.maximum(np.bincount(iw, minlength=len(wrong)), 1)
    dk, _ = t.query(Pw, k=1)
    medd = np.array([np.median(dk[iw == k]) if (iw == k).any() else np.inf for k in range(len(wrong))])
    L = np.bincount(iw, minlength=len(wrong))
    print(n, f'deleted (not sheet) {len(wrong)} lines, {len(Pw)} px; length within 5 px of a kept line running the same way: {par.mean():.1%};',
          f'lines >= 80% so: {(per >= 0.8).sum()} ({L[per >= 0.8].sum()} px); lines < 20% so: {(per < 0.2).sum()} ({L[per < 0.2].sum()} px)')
    on = pert >= 0.5
    print('   lines >= 50% on text:', int(on.sum()), 'their median distance to the nearest kept line (px):', sorted(np.round(medd[on]).astype(int).tolist()), 'lengths:', sorted(L[on].tolist()))
