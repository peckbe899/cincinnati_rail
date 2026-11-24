"""review-leak: how much of Ben's 44 blocks (streetmap/22-44.json) is also on the paper of a training plate (43, 45), and is
it taught there (train_v2/N/label.png)? World grids from cufp/N/model.npz (2 m). Reads only.
cd data/sanborn; python -B bench_2026-11-23/train/review-leak/scripts/overlap44_blocks.py"""
import json
import numpy as np, cv2
OUT = 'bench_2026-11-23/train/review-leak/'


def grid(N):
    z = np.load(f'cufp/{N}/model.npz'); px, py = z['px'].astype(np.float64), z['py'].astype(np.float64)
    im = cv2.imread(f'cufp/22-{N}.jpg', cv2.IMREAD_REDUCED_GRAYSCALE_8); H, W = im.shape[0] * 8, im.shape[1] * 8
    al = np.load(f'cufp/{N}/png_alpha_s4.npy').astype(np.float32)
    return dict(E0=float(z['E0']), N1=float(z['N1']), st=float(z['step']), px=px, py=py, W=W, H=H, al=al)


def sample(G, E, Nn):
    """pixel (full) of world points E, Nn in plate G (nan where off its grid), and on-paper flag"""
    j = (E - G['E0']) / G['st']; i = (G['N1'] - Nn) / G['st']
    h, w = G['px'].shape; ok = (j >= 0) & (i >= 0) & (j <= w - 1) & (i <= h - 1)
    ji = np.clip(np.round(j).astype(int), 0, w - 1); ii = np.clip(np.round(i).astype(int), 0, h - 1)
    x = G['px'][ii, ji]; y = G['py'][ii, ji]; ok &= (x > -1e5) & (y > -1e5) & (x >= 0) & (y >= 0) & (x < G['W']) & (y < G['H'])
    ah, aw = G['al'].shape
    ax = np.clip((x / G['W'] * aw).astype(int), 0, aw - 1); ay = np.clip((y / G['H'] * ah).astype(int), 0, ah - 1)
    paper = ok & (G['al'][ay, ax] > 0.5)
    return x, y, paper


G44 = grid('44'); sm = json.load(open('streetmap/22-44.json', encoding='utf8'))
# 44's world points: every 2 m grid node of 44 that is on its paper
h, w = G44['px'].shape; ii, jj = np.mgrid[0:h, 0:w]; E = G44['E0'] + jj * G44['st']; Nn = G44['N1'] - ii * G44['st']
x44, y44, p44 = sample(G44, E, Nn)
# Ben's blocks, rasterised at full size of 44 (ids), read at those points
gt = np.zeros((G44['H'] // 4, G44['W'] // 4), np.int32)
for b in sm['blocks']:
    cv2.fillPoly(gt, [np.round(np.array(b['ring']) / 4).astype(np.int32)], int(b['id']))
bid = np.where(p44, gt[np.clip((y44 / 4).astype(int), 0, gt.shape[0] - 1), np.clip((x44 / 4).astype(int), 0, gt.shape[1] - 1)], 0)
res = {}
for N in ('43', '45'):
    G = grid(N); xn, yn, pn = sample(G, E, Nn)
    lab = cv2.imread(f'train_v2/{N}/label.png', 0); lh, lw = lab.shape
    lv = np.full(E.shape, 254, np.int32)
    k = pn
    lv[k] = lab[np.clip((yn[k] / G['H'] * lh).astype(int), 0, lh - 1), np.clip((xn[k] / G['W'] * lw).astype(int), 0, lw - 1)]
    both = p44 & pn
    blocks = {}
    for b in sm['blocks']:
        m = bid == b['id']; n = int(m.sum())
        if not n: continue
        s = int((m & pn).sum())
        if s: blocks[b['id']] = dict(block_nodes=n, on_N_paper=s, share=round(s / n, 4), taught_block_on_N=int((m & pn & (lv == 1)).sum()), taught_street_on_N=int((m & pn & (lv == 0)).sum()))
    res[N] = dict(nodes_44_paper=int(p44.sum()), nodes_shared=int(both.sum()), share_of_44_paper=round(both.sum() / p44.sum(), 5),
                  shared_taught_on_N=dict(block=int((both & (lv == 1)).sum()), street=int((both & (lv == 0)).sum()), not_taught=int((both & (lv == 255)).sum())),
                  ben44_blocks_touching=len(blocks), ben44_block_nodes_on_N_paper=int(sum(v['on_N_paper'] for v in blocks.values())),
                  ben44_block_nodes_taught_block_on_N=int(sum(v['taught_block_on_N'] for v in blocks.values())), ben44_block_nodes_total=int((bid > 0).sum()), blocks=blocks)
    print(N, json.dumps({k: v for k, v in res[N].items() if k != 'blocks'}))
    print('   blocks', json.dumps(blocks))
json.dump(res, open(OUT + 'overlap44_blocks.json', 'w'), indent=1)
