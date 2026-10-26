"""Charts for the viewing-angle analysis (fs_views.py -> views_scored.csv): the overall score and each test, facing direction
against elevation, and the leading views drawn small."""
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

d = pd.read_csv('views_scored.csv')
F = sorted(d.facing.unique()); E = sorted(d.elev.unique())
fx = np.r_[np.array(F) - 7.5, F[-1] + 7.5]
ee = np.array(E, float); ey = np.r_[ee[0] - 2, (ee[:-1] + ee[1:]) / 2, ee[-1] + 2.5]
CMAP = 'Blues'
INK, MUTED = '#1f1f1f', '#6b6b6b'
PICK, RUNNER, LOW, NOW, EARLIER = (139, 12), (229, 32), (204, 28), (229, 26), [(19, 20), (19, 36)]
TICKS = [(0, 'N'), (45, 'NE'), (90, 'E'), (135, 'SE'), (180, 'S'), (225, 'SW'), (270, 'W'), (315, 'NW')]


def grid(col):
    return d.pivot(index='elev', columns='facing', values=col).loc[E, F].values


def frame(ax, small=False):
    ax.set_xticks([t for t, _ in TICKS]); ax.set_xticklabels([n for _, n in TICKS], fontsize=7 if small else 10, color=MUTED)
    ax.set_yticks(E if not small else [12, 24, 36, 45]); ax.tick_params(axis='y', labelsize=7 if small else 10, colors=MUTED)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)


def marks(ax, small=False):
    ms = 7 if small else 13
    ax.plot(*PICK, marker='*', ms=ms * 1.5, mfc='#f2a900', mec=INK, mew=0.8, ls='none', zorder=5)
    ax.plot(*RUNNER, marker='D', ms=ms * 0.8, mfc='white', mec=INK, mew=1.0, ls='none', zorder=5)
    ax.plot(*LOW, marker='s', ms=ms * 0.8, mfc='white', mec=INK, mew=1.0, ls='none', zorder=5)
    ax.plot(*NOW, marker='o', ms=ms * 0.8, mfc='none', mec='#c0303a', mew=1.8, ls='none', zorder=5)
    for p in EARLIER:
        ax.plot(*p, marker='x', ms=ms * 0.7, mec='#c0303a', mew=1.6, ls='none', zorder=5)


fig = plt.figure(figsize=(22, 23))
fig.text(0.02, 0.985, 'Fountain Square 3D view: which angle?', fontsize=22, weight='bold', va='top', color=INK)
fig.text(0.02, 0.962, 'Every facing direction in 15° steps (true compass, on the street grid and its diagonals) at nine elevations, drawn as fs_3d.py draws it: 1.4 times depth,\n'
         'deepest level first, joined floors as one slab, platforms 500 ft (Metro) and 670 ft (TRI). Each test is scaled 0 (worst view) to 1 (best view); the score weights them in your order of importance.',
         fontsize=11, color=MUTED, va='top')
# overall
ax = fig.add_axes([0.04, 0.62, 0.50, 0.31])
m = ax.pcolormesh(fx, ey, grid('score'), cmap=CMAP, vmin=d.score.min(), vmax=d.score.max(), shading='flat', edgecolors='white', linewidth=1.2)
frame(ax); marks(ax)
ax.set_xlabel('Facing direction (the way the viewer looks)', fontsize=11, color=INK)
ax.set_ylabel('Elevation above the horizontal (°)', fontsize=11, color=INK)
ax.set_title('Overall score', loc='left', fontsize=14, weight='bold', color=INK)
cb = fig.colorbar(m, ax=ax, fraction=0.03, pad=0.015); cb.outline.set_visible(False); cb.ax.tick_params(labelsize=9, colors=MUTED, length=0)
# key
kx = fig.add_axes([0.60, 0.62, 0.38, 0.31]); kx.axis('off'); kx.set_xlim(0, 1); kx.set_ylim(0, 1)
rows = [('*', '#f2a900', INK, 'Choice 1: facing SE (139°), 12°', 'score 0.776, best overall; 3.2 times as wide as tall'),
        ('D', 'white', INK, 'Choice 2: facing SW (229°), 32°', 'score 0.754; a plateau of 0.73 to 0.75 from 24 to 34° (right)'),
        ('s', 'white', INK, 'Choice 3: facing SSW (204°), 28°', 'score 0.731 in the 5° check; falls off fast either side'),
        ('o', 'none', '#c0303a', 'Drawn before: facing SW (229°), 26°', 'score 0.738 (labelled WSW 251° until the compass fix)'),
        ('x', 'none', '#c0303a', 'First drawn: facing NNE (19°), 20° and 36°', 'score 0.46 to 0.60')]
for i, (mk, fc, ec, a, b) in enumerate(rows):
    y = 0.95 - i * 0.085
    kx.plot(0.03, y, marker=mk, ms=14 if mk == '*' else 10, mfc=fc, mec=ec, mew=1.4 if ec != INK else 0.9, transform=kx.transAxes, clip_on=False)
    kx.text(0.08, y, a, fontsize=11.5, va='center', color=INK); kx.text(0.08, y - 0.035, b, fontsize=10, va='center', color=MUTED)
kx.text(0.0, 0.47, 'What the scores say', fontsize=12, weight='bold', color=INK)
notes = ['Platforms from your KMZ files. Facings are true compass; labels before the compass fix were 22° high.',
         'Heights has two halves: rises read true (how much of each flight\'s drawn drop is real rise, not plan depth) and',
         'levels read apart (a level step against the plan\'s depth, on a log).',
         'Choice 1 leads at 8 to 12° (0.75 to 0.78 in its 5° check) but falls to 0.66 by 16°, and is a wide strip.',
         'Choice 2 is the steadiest: 0.73 to 0.75 over 229 to 234° and 24 to 34°, 1.3 to 1.6 times as wide as tall.',
         'Choice 3 is a narrow peak: 0.52 to 0.73 within 5° of facing and 4° of elevation.']
for i, t in enumerate(notes):
    kx.text(0.0, 0.42 - i * 0.045, t, fontsize=10, color=INK)
# the tests
TESTS = [('platforms', '1. Platforms visible', 0.24, 'share of platform area not hidden'),
         ('stairs_read', '2. Stairs read as stairs', 0.12, 'at least 1.5 m wide on the page'),
         ('connections', '2. Stairs, escalators, elevators visible', 0.10, 'share not hidden'),
         ('heights', '3. Heights legible', 0.20, 'rises read true, and levels read apart'),
         ('deep', '4. TRI levels visible', 0.14, 'A/D and B floors and tracks not hidden'),
         ('crowd', '5. Uncrowded', 0.09, 'little piling up of shapes'),
         ('court', '6. Sunken court legible', 0.07, 'floor, stairs, escalators seen'),
         ('sheet', '7. Fits a sheet', 0.04, 'drawing near 16:10')]
for k, (col, title, w, sub) in enumerate(TESTS):
    r, c = divmod(k, 4)
    a = fig.add_axes([0.04 + c * 0.24, 0.445 - r * 0.165, 0.20, 0.105])
    a.pcolormesh(fx, ey, grid(col + '_n'), cmap=CMAP, vmin=0, vmax=1, shading='flat', edgecolors='white', linewidth=0.5)
    frame(a, small=True); marks(a, small=True)
    a.set_title('%s  (weight %.2f)\n' % (title, w), loc='left', fontsize=10.5, weight='bold', color=INK)
    a.text(0, 1.04, sub, transform=a.transAxes, fontsize=8.5, color=MUTED)
# thumbnails
fig.text(0.02, 0.215, 'The leading views, drawn', fontsize=13, weight='bold', color=INK, va='top')
for i, (fn, cap) in enumerate((('cand_139_12.png', 'Choice 1: SE 139°, 12°'), ('cand_229_32.png', 'Choice 2: SW 229°, 32°'),
                               ('cand_204_28.png', 'Choice 3: SSW 204°, 28°'))):
    im = Image.open(fn).convert('RGB'); im = im.crop((0, 295, im.width, im.height))      # drop the 1.9 in header (title, caption, arrow) at 150 dpi
    from PIL import ImageOps
    bb = ImageOps.invert(im).point(lambda v: 255 if v > 18 else 0).getbbox(); im = im.crop(bb)
    a = fig.add_axes([0.02 + i * 0.245, 0.01, 0.235, 0.17]); a.imshow(im); a.axis('off'); a.set_anchor('NW')
    a.set_title(cap, fontsize=10.5, loc='left', color=INK)
# the 5-degree check round the pick
fd = pd.read_csv('views_fine.csv'); FF = sorted(fd.facing.unique()); FE = sorted(fd.elev.unique())
fg = fd.pivot(index='elev', columns='facing', values='raw').loc[FE, FF].values
a = fig.add_axes([0.775, 0.035, 0.20, 0.13])
a.pcolormesh(np.r_[np.array(FF) - 2.5, FF[-1] + 2.5], np.r_[np.array(FE) - 1, FE[-1] + 1], fg, cmap=CMAP, vmin=0.55, vmax=0.80,
             shading='flat', edgecolors='white', linewidth=0.8)
for (r, e) in enumerate(FE):
    for (c, f) in enumerate(FF):
        a.text(f, e, '%.2f' % fg[r, c], ha='center', va='center', fontsize=7.5, color='white' if fg[r, c] > 0.70 else INK, weight='bold' if (f, e) == RUNNER else 'normal')
a.add_patch(plt.Rectangle((RUNNER[0] - 2.5, RUNNER[1] - 1), 5, 2, fill=False, ec='#f2a900', lw=2.5))
a.set_xticks(FF); a.set_xticklabels(['%d°' % f for f in FF], fontsize=8, color=MUTED); a.set_yticks(FE)
a.tick_params(axis='y', labelsize=8, colors=MUTED); a.tick_params(length=0)
for sp in a.spines.values():
    sp.set_visible(False)
a.set_title('Round choice 2, 5° and 2° steps', loc='left', fontsize=10.5, color=INK)
fig.savefig('fs_view_analysis.png', dpi=110)
print('fs_view_analysis.png')
