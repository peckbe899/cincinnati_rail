"""Fit the character-or-not classifier on the CPU (classifier step, 26 Nov 2026). Run with the unet venv's python (torch
2.4.1 CPU); it only uses torch to fit, and writes plain numpy weights that model_np.py runs on the system python.

    cd data/sanborn
    "<venv>/python.exe" -B bench_2026-11-25/text_v1/classifier/scripts/train.py cnn|mlp [--train NAME] [--epochs 8] [--out FILE]

Reads data/NAME.npz (build_train.py; default train). Classes are every label in it: figures 0-9, capitals, small letters,
the marks ' " . - & , , 'pair' (two touching figures) and 'junk'. Text = every class but junk.
Weights per row: cluster 1, finder5 1, rail 3, synth 0.5; then junk rows are scaled so junk and text weigh the same
in all. Plain cross-entropy, AdamW (lr 2e-3, weight decay 1e-4), batch 256, cosine schedule, small random shifts and
scalings of the 32 x 32 image (+-2 px, x 0.9-1.1). Dev check after fitting on data/dev.npz (pieces inside T1-T7,
never trained on): pixel-weighted AUC of P(junk) for telling mostly-text from mostly-non-text pieces. Writes
out/model_<kind>.npz (or --out) and prints the timing. Seeds fixed (torch and numpy: 0)."""
import os, sys, time, json
sys.dont_write_bytecode = True
import numpy as np, torch, torch.nn as nn, torch.nn.functional as Fn
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from model_np import mlp_input, predict  # noqa
DATA = os.path.join(HERE, '..', 'data'); OUT = os.path.join(HERE, '..', 'out')
torch.manual_seed(0); np.random.seed(0); torch.set_num_threads(8)
SW = dict(cluster=1.0, finder5=1.0, rail=3.0, synth=0.5)


class CNN(nn.Module):
    def __init__(s, nc, ns=10):
        super().__init__()
        s.c = nn.ModuleList([nn.Conv2d(i, o, 3, padding=1) for i, o in ((1, 16), (16, 32), (32, 64))])
        s.b = nn.ModuleList([nn.BatchNorm2d(o) for o in (16, 32, 64)])
        s.f0 = nn.Linear(1024 + ns, 128); s.f1 = nn.Linear(128, nc); s.dr = nn.Dropout(0.3)
    def forward(s, x, q):
        for c, b in zip(s.c, s.b): x = Fn.max_pool2d(Fn.relu(b(c(x))), 2)
        return s.f1(s.dr(Fn.relu(s.f0(torch.cat([x.flatten(1), q], 1)))))


class MLP(nn.Module):
    def __init__(s, nin, nc):
        super().__init__(); s.f0 = nn.Linear(nin, 256); s.f1 = nn.Linear(256, nc); s.dr = nn.Dropout(0.3)
    def forward(s, x): return s.f1(s.dr(Fn.relu(s.f0(x))))


def wauc(p, y, w):
    """weighted AUC: probability that a random (weighted) positive scores above a random negative"""
    o = np.argsort(p); p, y, w = p[o], y[o], w[o]
    wn = np.cumsum(w * (y == 0)); tot_n = wn[-1]; tot_p = (w * (y == 1)).sum()
    return float((w * (y == 1) * (wn - 0.5 * w * (y == 0))).sum() / max(tot_n * tot_p, 1e-9))


def shift_scale(x):
    n = x.shape[0]; s = 1 + (torch.rand(n) * 0.2 - 0.1); t = (torch.rand(n, 2) * 4 - 2) / 16
    th = torch.zeros(n, 2, 3); th[:, 0, 0] = s; th[:, 1, 1] = s; th[:, :, 2] = t
    g = Fn.affine_grid(th, x.shape, align_corners=False); return Fn.grid_sample(x, g, align_corners=False)


def main():
    a = sys.argv; kind = a[1]; name = a[a.index('--train') + 1] if '--train' in a else 'train'
    ep = int(a[a.index('--epochs') + 1]) if '--epochs' in a else 8
    out = a[a.index('--out') + 1] if '--out' in a else os.path.join(OUT, f'model_{kind}.npz')
    t0 = time.time(); D = np.load(os.path.join(DATA, f'{name}.npz'))
    lab = D['label']; classes = sorted(set(lab.tolist())); ci = {c: i for i, c in enumerate(classes)}; y = np.array([ci[c] for c in lab])
    J = ci['junk']; w = np.array([SW[s] for s in D['source']], np.float32)
    wj = w[y == J].sum(); wt = w[y != J].sum(); w[y == J] *= wt / wj
    img = D['img'].astype(np.float32) / 255; scal = D['scal'].astype(np.float32)
    s_mu = scal.mean(0); s_sd = scal.std(0) + 1e-6
    if kind == 'mlp':
        X = mlp_input(img, scal); x_mu = X.mean(0); x_sd = X.std(0) + 1e-6; Xt = torch.tensor((X - x_mu) / x_sd); net = MLP(X.shape[1], len(classes))
    else:
        Xi = torch.tensor(img[:, None]); Q = torch.tensor((scal - s_mu) / s_sd); net = CNN(len(classes))
    Y = torch.tensor(y); W_ = torch.tensor(w)
    opt = torch.optim.AdamW(net.parameters(), lr=2e-3, weight_decay=1e-4); n = len(y); bs = 256; steps = ep * ((n + bs - 1) // bs)
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=2e-3, total_steps=steps, pct_start=0.15)
    print(f'{kind}: {n} rows, {len(classes)} classes, features ready {time.time() - t0:.0f} s', flush=True)
    for e in range(ep):
        net.train(); perm = torch.randperm(n); tl = 0
        for s in range(0, n, bs):
            b = perm[s:s + bs]
            if kind == 'mlp': z = net(Xt[b])
            else: z = net(shift_scale(Xi[b]), Q[b])
            loss = (Fn.cross_entropy(z, Y[b], reduction='none') * W_[b]).sum() / W_[b].sum()
            opt.zero_grad(); loss.backward(); opt.step(); sch.step(); tl += float(loss) * len(b)
        print(f'  epoch {e + 1}: loss {tl / n:.4f}  {time.time() - t0:.0f} s', flush=True)
    net.eval(); M = dict(kind=kind, classes=np.array(classes), s_mu=s_mu, s_sd=s_sd, sources=json.dumps(SW), train=name, epochs=ep,
                         exclude=str(D['exclude']) if 'exclude' in D.files else '{}')
    with torch.no_grad():
        if kind == 'mlp':
            M.update(x_mu=x_mu, x_sd=x_sd)
        else:
            for j, (c, b) in enumerate(zip(net.c, net.b)):
                g = (b.weight / torch.sqrt(b.running_var + b.eps)); M[f'c{j}_w'] = (c.weight * g[:, None, None, None]).numpy().astype(np.float32)
                M[f'c{j}_b'] = ((c.bias - b.running_mean) * g + b.bias).numpy().astype(np.float32)
        M['f0_w'] = net.f0.weight.numpy().astype(np.float32); M['f0_b'] = net.f0.bias.numpy().astype(np.float32)
        M['f1_w'] = net.f1.weight.numpy().astype(np.float32); M['f1_b'] = net.f1.bias.numpy().astype(np.float32)
    fit_s = time.time() - t0; M['fit_seconds'] = fit_s
    os.makedirs(os.path.dirname(out), exist_ok=True); np.savez_compressed(out, **M)
    # check the numpy pass against torch on 500 rows, then the dev AUC
    from model_np import load_model
    Mn = load_model(out); pn = predict(Mn, img[:500], scal[:500])
    with torch.no_grad():
        zt = net(Xt[:500]) if kind == 'mlp' else net(Xi[:500], Q[:500])
    print('numpy vs torch, max prob difference on 500 rows:', float(np.abs(pn - torch.softmax(zt, 1).numpy()).max()))
    V = np.load(os.path.join(DATA, 'dev.npz')); pv = predict(Mn, V['img'], V['scal']); pj = pv[:, J]
    t2, t1 = V['t2'], V['t1']; sc = (t2 + t1) > 0; yv = (t1 > t2).astype(int)
    print(f'fitted in {fit_s:.0f} s; dev pieces {int(sc.sum())}: pixel-weighted AUC of P(junk) {wauc(pj[sc], yv[sc], (t1 + t2)[sc].astype(float)):.4f}, '
          f'piece AUC {wauc(pj[sc], yv[sc], np.ones(int(sc.sum()))):.4f}')


if __name__ == '__main__':
    main()
