"""review-labels, 24 Nov 2026: hash every training array of the four labelled plates, loaded two ways (run each way in its own process).

    VPY -B load_hashes.py today  OUT.json     today's loaders: tools/sanborn/unet unet.load + load_edge (blank guide) and edgenet.load (--no-guide --area area_ng1)
    VPY -B load_hashes.py staged OUT.json     the staged trainers' own loaders on data/sanborn/train_v2: unet.load_data, edgenet.load_data + build (whole plate)

Each array: shape, dtype and the sha256 of its bytes. 'staged' also builds 40 random line-net windows per plate (as the
trainer builds crops) and hashes them; 'today' hashes the same windows sliced from edgenet.load's arrays (same seed).
Nothing is written but OUT.json.
"""
import hashlib, json, os, sys, time
import numpy as np
REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D'
STAGED = REPO + '/data/sanborn/bench_2026-11-23/train/staged/tools/sanborn/unet'
ROOT = REPO + '/data/sanborn/train_v2'
PLATES = ('43', '45', '80', '82A'); NWIN, C = 40, 448 + 2 * 24


def hx(a):
    a = np.ascontiguousarray(a); h = hashlib.sha256(f'{a.shape}|{a.dtype}|'.encode()); h.update(a.tobytes()); return dict(shape=list(a.shape), dtype=str(a.dtype), sha256=h.hexdigest())


def windows(H, W, plate):
    rng = np.random.default_rng(abs(hash(plate)) % 1000 if False else sum(map(ord, plate)))
    return [(int(rng.integers(0, H - C)), int(rng.integers(0, W - C))) for _ in range(NWIN)]


def main(mode, out):
    res = dict(mode=mode, made=time.strftime('%Y-%m-%d %H:%M:%S'), plates={})
    if mode == 'today':
        sys.path.insert(0, REPO + '/tools/sanborn/unet'); sys.path.insert(0, REPO + '/tools/sanborn')
        import unet as A, edgenet as E
        A.NOGUIDE = True; E.NOGUIDE = True; E.AREA = 'area_ng1'
        res['modules'] = dict(unet=A.__file__, edgenet=E.__file__)
    else:
        sys.path.insert(0, STAGED); sys.path.append(REPO + '/tools/sanborn')     # _ws from the repo (the staged tree has none)
        import unet as A, edgenet as E
        res['modules'] = dict(unet=A.__file__, edgenet=E.__file__)
    for N in PLATES:
        t0 = time.time(); r = {}
        if mode == 'today':
            x, lab = A.load(N); wm, et = A.load_edge(N, lab)
        else:
            x, lab, wm, et, known = A.load_data(ROOT, N); r['edge_known'] = bool(known)
        r['area_x'] = hx(x); r['area_label'] = hx(lab); r['area_edge_weights'] = hx(wm); r['area_edge_target'] = hx(et)
        del x, lab, wm, et
        if mode == 'today':
            X, T, G = E.load(N)
        else:
            S, has = E.load_data(ROOT, N); H, W = S.shape[:2]; X, T, G = E.build(S, 0, H, 0, W); r['area_in_present'] = bool(has)
        r['line_x'] = hx(X); r['line_t'] = hx(T); r['line_w'] = hx(G)
        r['line_x_channels'] = [hx(X[:, :, k])['sha256'][:16] for k in range(X.shape[2])]
        H, W = T.shape; wins = []
        for y, x0 in windows(H, W, N):
            if mode == 'today': xw, tw, gw = X[y:y + C, x0:x0 + C], T[y:y + C, x0:x0 + C], G[y:y + C, x0:x0 + C]
            else: xw, tw, gw = E.build(S, y, y + C, x0, x0 + C)
            wins.append(hashlib.sha256(np.ascontiguousarray(xw).tobytes() + np.ascontiguousarray(tw).tobytes() + np.ascontiguousarray(gw).tobytes()).hexdigest()[:16])
        r['windows'] = wins
        r['counts'] = dict(line_pos=int((T == 1).sum()), line_neg=int((T == 0).sum()), line_unscored=int((T == 255).sum()))
        r['seconds'] = round(time.time() - t0, 1)
        del X, T, G
        if mode != 'today': del S
        res['plates'][N] = r; print(N, json.dumps({k: (v['sha256'][:12] if isinstance(v, dict) and 'sha256' in v else v) for k, v in r.items() if k not in ('windows', 'line_x_channels')}), flush=True)
    json.dump(res, open(out, 'w', encoding='utf8', newline='\n'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
