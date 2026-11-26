"""Gate scorer's own check of Ben's line ink called text, plates 44, 1A, 5 (26 Nov 2026).
    cd data/sanborn; python -B bench_2026-11-25/text_v1/gate/scripts/my_lines.py OUT.json
Ben's lines: 44 streetmap/22-44.json; 1A and 5 the line editor's lines with his edits applied (street_map.editor_lines on
unet_data/N_edges.json + picks22_guided/22-N/edges_ben.json; imported read-only, nothing written). Kinds printed, drawn,
sheet_edge. Own code for the rest: lines drawn 1 px wide with PIL, distance by scipy's exact Euclidean transform.
line ink (tol) = ink within tol px of a line (tol 1 and 3); share called text = text px / line-ink px.
cut = points every 2 px along his lines with ink within 2 px (5x5) where none of that ink is left once text is removed."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
Image.MAX_IMAGE_PIXELS = None
B = 'bench_2026-11-25'
TOOLS = os.path.abspath(os.path.join('..', '..', 'tools', 'sanborn', 'unet'))
METHODS = {'bin8': ('unet_data/{plate}_bins.png', (8,)), 'v1': (f'{B}/text/finder/out/{{plate}}_finder.png', (2, 3, 4)),
           'v2': (f'{B}/text_v1/finder2/out/final/{{plate}}_text.png', (2, 3)), 'v3': (f'{B}/text_v1/classifier/out/finder3/{{plate}}_text.png', (2, 3)),
           'handoff': (f'{B}/text_v1/handoff/masks/{{plate}}_text.png', (2, 3))}
KINDS = ('printed', 'drawn', 'sheet_edge')


def ben_lines(N, W, H):
    if N == '44':
        return json.load(open('streetmap/22-44.json', encoding='utf8'))['lines']
    sys.path.insert(0, TOOLS); import street_map
    E = json.load(open(f'unet_data/{N}_edges.json', encoding='utf8')); Bn = json.load(open(f'picks22_guided/22-{N}/edges_ben.json', encoding='utf8'))
    return street_map.editor_lines(N, W, H, E, Bn)[0]


out = {}
for N in ('44', '1A', '5'):
    ref = np.array(Image.open(METHODS['v2'][0].replace('{plate}', N))); H, W = ref.shape; ink = ref > 0
    L = [l for l in ben_lines(N, W, H) if l['kind'] in KINDS]
    im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
    for l in L: d.line([tuple(l['a']), tuple(l['b'])], fill=1, width=1)
    lm = np.array(im) > 0
    dist = ndi.distance_transform_edt(~lm)
    z = {t: ink & (dist <= t) for t in (1, 3)}
    # samples along the lines
    S = []
    for l in L:
        a, b = np.array(l['a'], float), np.array(l['b'], float); n = max(2, int(np.hypot(*(b - a)) / 2) + 1); S.append(a + np.linspace(0, 1, n)[:, None] * (b - a))
    q = np.vstack(S).round().astype(int); q = q[(q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H)]
    def near(mask): return ndi.maximum_filter(mask.astype(np.uint8), size=5)[q[:, 1], q[:, 0]] > 0
    has = near(ink)
    r = dict(lines=len(L), line_ink_1px=int(z[1].sum()), line_ink_3px=int(z[3].sum()), samples=int(has.sum()))
    for m, (pat, codes) in METHODS.items():
        p = pat.replace('{plate}', N)
        if not os.path.exists(p): continue
        code = np.array(Image.open(p)); code = code[..., 0] if code.ndim == 3 else code
        if m == 'bin8': r['bins_ink_equal'] = bool(((code > 0) == ink).all()); r['bins_ink_diff_px'] = int(((code > 0) != ink).sum())
        tx = np.isin(code, codes)
        cut = int((has & ~near(ink & ~tx)).sum())
        r[m] = dict(px_1=int((z[1] & tx).sum()), share_1=round(float((z[1] & tx).sum()) / z[1].sum(), 5),
                    px_3=int((z[3] & tx).sum()), share_3=round(float((z[3] & tx).sum()) / z[3].sum(), 5), cut=cut, cut_share=round(cut / max(1, has.sum()), 5))
        print(N, m, r[m], flush=True)
    out[N] = r
json.dump(out, open(sys.argv[1], 'w'), indent=1)
