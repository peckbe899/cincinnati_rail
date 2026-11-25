"""Picture of the house-number checks: number against position along the street, one panel per street,
the two sides as two series; labels on the adjoining plate as triangles; labels the checks flag ringed and named.
usage: python -B plot_hn.py   (needs out/hn_true.json from hn_checks.py; writes out/house_numbers_checks.png)"""
import json, os, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import hn_checks as H

C = ['#2a78d6', '#eb6834']           # categorical slots 1-2 (dataviz reference palette, light mode)
INK, MUTED, GRID = '#1f1f1e', '#6b6a64', '#e4e2dc'


def main():
    T = {t['id']: t for t in json.load(open(os.path.join(BASE, 'out', 'hn_true.json')))}
    streets = H.load()
    fig, axs = plt.subplots(1, len(streets), figsize=(4.2 * len(streets), 4.6))
    for ax, st in zip(axs, streets):
        for c in st['sides'].values():
            H.expand_side(c)
        for i, (sd, L) in enumerate(sorted(st['sides'].items())):
            par = 'odd' if sum(n % 2 for r in L for n in (r['nums'] or [])) > len(L) / 2 else 'even'
            for mk, same in (('o', True), ('^', False)):
                P = [(r['s'], n) for r in L if r['nums'] and (r['plate'] == st['frame']) == same for n in r['nums']]
                if P:
                    ax.plot(*zip(*P), mk, ms=5 if mk == 'o' else 6, color=C[i], mec='white', mew=0.8,
                            label=f'{sd} side ({par})' + ('' if same else f', plate {L[[r["plate"] == st["frame"] for r in L].index(False)]["plate"]}'), zorder=3)
            k = 0
            for r in L:
                t = T.get(r['id'])
                if t and t['fails'] and r['nums']:
                    k += 1
                    ax.plot([r['s']], [r['nums'][0]], 'o', ms=13, mfc='none', mec=INK, mew=1.2, zorder=4)
                    ax.annotate(f"{r['text']}: {', '.join(t['fails'])}", (r['s'], r['nums'][0]), xytext=(10, 12 if k % 2 else -16), textcoords='offset points',
                                fontsize=8, color=INK)
        for n, s in st['cross'].items():
            ax.axvline(s, color=GRID, lw=1, zorder=1)
            ax.text(s, 1.0, f' {n}', transform=ax.get_xaxis_transform(), fontsize=7.5, color=MUTED, va='top', rotation=90)
        ax.set_title(f"{st['street']} (plate {st['frame']})", fontsize=10, color=INK, loc='left')
        ax.set_xlabel('feet along the street', fontsize=8, color=MUTED)
        ax.tick_params(labelsize=7.5, colors=MUTED)
        for sp in ('top', 'right'):
            ax.spines[sp].set_visible(False)
        for sp in ('left', 'bottom'):
            ax.spines[sp].set_color(GRID)
        ax.grid(axis='y', color=GRID, lw=0.6)
        ax.legend(fontsize=7, frameon=False, loc='best')
    axs[0].set_ylabel('house number', fontsize=8, color=MUTED)
    fig.suptitle('House numbers read by eye, checked by code: a ring marks a label the checks flag', fontsize=11, color=INK, x=0.01, ha='left')
    fig.tight_layout()
    fig.savefig(os.path.join(BASE, 'out', 'house_numbers_checks.png'), dpi=130, facecolor='white')


if __name__ == '__main__':
    main()
