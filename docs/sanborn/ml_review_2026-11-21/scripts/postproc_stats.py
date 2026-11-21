"""What outlines.json holds per plate and what blocks_noguide.py keeps of it; what edit_server.clean() makes of N_edges.json."""
import json, sys, os, importlib.util
import numpy as np
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
# clean() copied verbatim from edit_server.py (importing the module would start nothing, but it imports _ws; copy is safer)
src = open('C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/edit_server.py', encoding='utf8').read()
i0 = src.index('def clean('); i1 = src.index('def plates(')
ns = dict(np=np); exec(src[i0:i1], ns); clean = ns['clean']
L = lambda s: float(np.hypot(s['b'][0] - s['a'][0], s['b'][1] - s['a'][1]))
plates = sys.argv[1:] or ['1A', '1B', '2', '3', '4', '5', '6', '7', '8A', '8B', '9', '10', '11', '12', '13', '14', '15A', '15B', '16', '43', '44']
print('plate blocks | kept_len short_len short_n paperedge_len | sides/block med | kept<130 share(len) | edges_json n -> after clean n | consecutive kept pairs <3deg')
for N in plates:
    f = SP + f'picks22_guided/22-{N}/outlines.json'
    if not os.path.exists(f): continue
    o = json.load(open(f, encoding='utf8'))
    kept = [s for p in o for s in p if s['state'] != 'short' and not s.get('paper_edge')]
    short = [s for p in o for s in p if s['state'] == 'short']; pe = [s for p in o for s in p if s['state'] != 'short' and s.get('paper_edge')]
    kl = sum(map(L, kept)); sl = sum(map(L, short)); pl = sum(map(L, pe))
    spb = np.median([sum(1 for s in p if s['state'] != 'short') for p in o]) if o else 0
    k130 = sum(L(s) for s in kept if L(s) < 130) / max(kl, 1)
    # consecutive kept sides that are nearly collinear (straighten split one straight side)
    col = 0; pairs = 0
    for p in o:
        ks = [s for s in p if s['state'] != 'short']
        for a_, b_ in zip(ks, ks[1:] + ks[:1]):
            if a_ is b_: continue
            d1 = np.subtract(a_['b'], a_['a']); d2 = np.subtract(b_['b'], b_['a'])
            c = abs(d1 @ d2) / (np.hypot(*d1) * np.hypot(*d2) + 1e-9); pairs += 1; col += c > np.cos(np.radians(3))
    ef = U + f'{N}_edges.json'; en = cn = '-'
    if os.path.exists(ef):
        e = json.load(open(ef, encoding='utf8')); en = len(e); cn = len(clean(e))
    print(f'{N:4s} {len(o):3d} | {kl:8.0f} {sl:8.0f} {len(short):5d} {pl:7.0f} | {spb:5.1f} | {k130:.2f} | {en} -> {cn} | {col}/{pairs}')
