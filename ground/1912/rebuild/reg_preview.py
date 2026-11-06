"""report/registration.png: sheet frames, control residuals (arrows x50) and seam rms."""
import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from common import load_paths, load_all
from sheets_index import load_sheet_model, frame_ring
from joint_georef import edge_points
from common import neighbours


def main(paths, outdir):
    P = load_paths(paths); ids, _ = load_all(P)
    rep = json.load(open(Path(P['work']) / 'registration_report.json'))
    fig, ax = plt.subplots(figsize=(14, 11))
    M = {}
    for sid, d in sorted(ids.items()):
        m, g = load_sheet_model(ids, sid, outdir); M[sid] = m
        ring = frame_ring(d); E, N = m.p2utm(ring[:, 0], ring[:, 1])
        ax.plot(np.r_[E, E[:1]] / 1000, np.r_[N, N[:1]] / 1000, color='0.6', lw=0.6)
        ax.text(E.mean() / 1000, N.mean() / 1000, f"{sid}\n{d['num']}", ha='center', va='center', fontsize=7, color='0.35')
        if g['controls']:
            px = np.array([c['px'] for c in g['controls']]); xy = np.array([c['xy'] for c in g['controls']])
            e, n = m.p2utm(px[:, 0], px[:, 1])
            ax.quiver(e / 1000, n / 1000, (xy[:, 0] - e) * 50 / 1000, (xy[:, 1] - n) * 50 / 1000, angles='xy', scale_units='xy', scale=1,
                      width=0.0012, color='tab:blue')
    for s in rep['seams']:
        a, b = s['a'], s['b']
        nb = [x for x in neighbours(ids) if x[0] == a and x[1] == b][0]
        gx, gy = edge_points(nb[2], nb[3], nb[4], nb[5], 200.0)
        E, N = M[a].g2utm(gx, gy)
        c = plt.cm.RdYlGn_r(min(s['rms_m'] / 0.5, 1.0))
        ax.plot(E / 1000, N / 1000, color=c, lw=3)
    ax.set_aspect('equal'); ax.set_xlabel('E (km, EPSG:26916)'); ax.set_ylabel('N (km)')
    allr = np.array([c['residual_m'] for sid in ids for c in json.load(open(Path(outdir) / 'georef' / f'{sid}.json'))['controls']])
    ax.set_title(f'1912 sheets, joint registration: {len(allr)} street controls, rms {np.sqrt(np.mean(allr ** 2)):.2f} m (arrows x50); '
                 f'seams coloured by rms, green 0 to red 0.5 m (worst {max(s["rms_m"] for s in rep["seams"]):.2f} m)', fontsize=9)
    (Path(outdir) / 'report').mkdir(exist_ok=True)
    fig.savefig(Path(outdir) / 'report' / 'registration.png', dpi=110, bbox_inches='tight')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'configs/ground_paths.json', sys.argv[2] if len(sys.argv) > 2 else 'ground/1912')
