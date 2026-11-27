"""Second round of NEGATIVE candidates (dev_ditto, 26 Nov 2026), after the v1 look (negatives/choose/verdicts_v1.txt:
26 of 124 kept; the 'isolated' and 'lineend' samplers drew mostly text, and two rail draws were double lines).

    cd data/sanborn; python -B bench_2026-11-26/text_fix/dev_ditto/scripts/neg_sample2.py

Stricter samplers, new seeds random.Random('neg2-' + SAMPLER + '-' + plate), same exclusions as neg_sample.py:
  rail2     plate 44 railroad tracks: the nearest crossing where the ink across the track is ONE contiguous run of
            11 px or more through the track line (a tick), not two parallel lines.
  dash2     a separate straight bar (6-200 px, 6-40 px long, length/width 3 or more) with a partner of 0.6-1.6x its
            length on BOTH sides along its own axis (to 12 deg), gaps 3-40 px: a dash inside a dashed line.
  lineend2  a skeleton end point of a large ink piece whose branch runs 25 px from the end without a junction and
            nearly straight (end to 25th pixel 22 px or more): the end of a straight line.
Writes negatives/choose/candidates_v2.json (cids D001 ...)."""
import json, math, os, random, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import neg_sample as ns

N2 = dict(rail2=16, dash2=3, lineend2=2)


def rail2():
    p = '44'; R = json.load(open(f'picks22_guided/22-{p}/rail_ben.json'))['tracks']; trk = [np.array(t['pts'], float) for t in R if t['kind'] == 'railroad']
    lens = [float(np.sum(np.hypot(*np.diff(t, axis=0).T))) for t in trk]; rng = random.Random('neg2-rail2-44'); I = ns.ink(p); H, W = I.shape; out = []
    for k in range(600):
        if sum(d['verdict'] == 'candidate' for d in out) >= N2['rail2']: break
        t = rng.choices(range(len(trk)), weights=lens)[0]; P = trk[t]; seg = np.hypot(*np.diff(P, axis=0).T); cs = np.cumsum(seg)
        s = rng.uniform(0, cs[-1]); i = min(int(np.searchsorted(cs, s)), len(seg) - 1); f = (s - (cs[i] - seg[i])) / max(seg[i], 1e-6)
        x, y = P[i] + f * (P[i + 1] - P[i]); u = (P[i + 1] - P[i]) / max(seg[i], 1e-6); v = np.array([-u[1], u[0]])
        d = dict(sampler='rail2', plate=p, draw=k, at=[round(float(x), 1), round(float(y), 1)]); best = None
        for step in range(0, 120):
            for sgn in (1, -1):
                q = np.array([x, y]) + sgn * step * u
                col = []
                for o in range(-16, 17):
                    X, Y = int(round(q[0] + o * v[0])), int(round(q[1] + o * v[1])); col.append(I[Y, X] if 0 <= X < W and 0 <= Y < H else 0)
                col = np.array(col); c0 = 16
                # the run through the line: start at the inked offset nearest 0 and extend both ways
                on = np.nonzero(col)[0]
                if not len(on): continue
                j = on[np.argmin(np.abs(on - c0))]
                if abs(j - c0) > 3: continue
                a = j
                while a > 0 and col[a - 1]: a -= 1
                b = j
                while b < len(col) - 1 and col[b + 1]: b += 1
                if b - a + 1 >= 11 and col.sum() <= (b - a + 1) + 2: best = q; break
            if best is not None: break
        if best is None: d['verdict'] = 'no single-run crossing within 120 px'; out.append(d); continue
        if not ns.ok_place(p, *best): d['verdict'] = 'too near a ditto word or H1-H4'; out.append(d); continue
        d.update(centre=[int(round(best[0])), int(round(best[1]))], verdict='candidate'); out.append(d)
    return out


def dash2(p):
    n, lb, st, cen = ns.comps(p); rng = random.Random(f'neg2-dash2-{p}'); out = []
    A = st[:, 4]; side = np.maximum(st[:, 2], st[:, 3]); pool = np.nonzero((A >= 6) & (A <= 200) & (side >= 6) & (side <= 40))[0]; pool = pool[pool > 0]
    tries = 0
    while sum(d['verdict'] == 'candidate' for d in out) < N2['dash2'] and tries < 6000:
        tries += 1; k = int(rng.choice(pool)); d = dict(sampler='dash2', plate=p, draw=tries)
        L, el, ang = ns.shape(lb, st, k)
        if el < 3.0: d['verdict'] = 'not a straight bar'; out.append(d); continue
        a = math.radians(ang); sides = set()
        x0, y0 = int(cen[k][0]) - 70, int(cen[k][1]) - 70; sub = lb[max(0, y0):y0 + 141, max(0, x0):x0 + 141]
        for k2 in np.unique(sub):
            if k2 in (0, k) or not (6 <= st[k2, 4] <= 250): continue
            dv = cen[k2] - cen[k]; dist = float(np.hypot(*dv)); L2, el2, ang2 = ns.shape(lb, st, k2)
            if el2 < 2.5 or not (0.6 <= L2 / max(L, 1) <= 1.6): continue
            gap = dist - (L + L2) / 2
            if not (3 <= gap <= 40): continue
            da = abs((ang2 - ang + 90) % 180 - 90); along = abs((math.degrees(math.atan2(dv[1], dv[0])) - ang + 90) % 180 - 90)
            if da <= 12 and along <= 12: sides.add(1 if (dv[0] * math.cos(a) + dv[1] * math.sin(a)) > 0 else -1)
        if len(sides) < 2: d['verdict'] = 'not inside a dashed line'; out.append(d); continue
        if not ns.ok_place(p, *cen[k]): d['verdict'] = 'too near a ditto word or H1-H4'; out.append(d); continue
        d.update(centre=[int(round(cen[k][0])), int(round(cen[k][1]))], verdict='candidate'); out.append(d)
    return out


def lineend2(p):
    n, lb, st, cen = ns.comps(p); rng = random.Random(f'neg2-lineend2-{p}'); out = []
    pool = np.nonzero(st[:, 4] >= 1000)[0]; pool = pool[pool > 0]; tries = 0
    while sum(d['verdict'] == 'candidate' for d in out) < N2['lineend2'] and tries < 400:
        tries += 1; k = int(rng.choice(pool)); d = dict(sampler='lineend2', plate=p, draw=tries)
        ys_, xs_ = np.nonzero(lb[st[k, 1]:st[k, 1] + st[k, 3], st[k, 0]:st[k, 0] + st[k, 2]] == k); j = rng.randrange(len(xs_))
        px_, py_ = st[k, 0] + xs_[j], st[k, 1] + ys_[j]; x, y = max(0, px_ - 60), max(0, py_ - 60)
        m = (lb[y:y + 121, x:x + 121] == k); sk = ns.skeletonize(m).astype(np.uint8); sk[:4, :] = 0; sk[-4:, :] = 0; sk[:, :4] = 0; sk[:, -4:] = 0
        nb = cv2.filter2D(sk, -1, np.ones((3, 3), np.float32), borderType=cv2.BORDER_CONSTANT)
        ends = [tuple(e) for e in np.argwhere((sk > 0) & (nb == 2))]; rng.shuffle(ends); hit = None
        for e in ends:
            path = [e]; prev = None; cur = e; okb = True
            for _ in range(25):
                nbrs = [(cur[0] + dy, cur[1] + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy or dx) and 0 <= cur[0] + dy < sk.shape[0] and 0 <= cur[1] + dx < sk.shape[1] and sk[cur[0] + dy, cur[1] + dx] and (cur[0] + dy, cur[1] + dx) != prev and (cur[0] + dy, cur[1] + dx) not in path]
                if len(nbrs) != 1: okb = False; break
                prev, cur = cur, nbrs[0]; path.append(cur)
            if okb and math.hypot(path[-1][0] - e[0], path[-1][1] - e[1]) >= 22: hit = e; break
        if hit is None: d['verdict'] = 'no straight line end in the window'; out.append(d); continue
        cx, cy = x + hit[1], y + hit[0]
        if not ns.ok_place(p, cx, cy): d['verdict'] = 'too near a ditto word or H1-H4'; out.append(d); continue
        d.update(centre=[int(cx), int(cy)], verdict='candidate'); out.append(d)
    return out


def main():
    allc = rail2()
    for p in ns.PLATES:
        allc += dash2(p); allc += lineend2(p); ns._ink.pop(p, None); ns._cc.pop(p, None)
    cand = [d for d in allc if d['verdict'] == 'candidate']
    for i, d in enumerate(cand): d['cid'] = f'D{i + 1:03d}'
    json.dump(dict(note=__doc__, draws=allc), open(os.path.join(ns.OUT, 'candidates_v2.json'), 'w'), indent=1)
    import collections; print(len(allc), 'draws,', len(cand), 'candidates', collections.Counter(d['sampler'] for d in cand))


if __name__ == '__main__':
    main()
