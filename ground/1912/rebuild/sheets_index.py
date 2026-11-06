"""Write / update ground/1912/sheets_index.json (SPEC 4.1)."""
import csv, json, sys
from pathlib import Path
import numpy as np
from PIL import Image

from common import load_paths, load_all, frame_px
from georef_model import TPS, Sheet

DATUM_NOTE = "1912 city datum; fitted offset to NAVD88 in report/fit_report.json"


def load_sheet_model(ids, sid, outdir):
    g = json.load(open(Path(outdir) / 'georef' / f'{sid}.json'))
    c = g['forward']['correction']
    t = TPS(c['centres'], c['weights'], c['affine'], c['scale_m'])
    return Sheet(ids[sid]['start'], t), g


def frame_ring(d, n=40):
    fr = np.array(frame_px(d) + [frame_px(d)[0]], float)
    pts = []
    for a, b in zip(fr[:-1], fr[1:]):
        t = np.linspace(0, 1, n, endpoint=False)[:, None]; pts.append(a + (b - a) * t)
    return np.vstack(pts)


def write(paths, outdir, contours=None, notes=None):
    P = load_paths(paths); ids, _ = load_all(P)
    out = Path(outdir) / 'sheets_index.json'
    old = {s['id']: s for s in json.load(open(out))['sheets']} if out.exists() else {}
    sha = {}
    for r in csv.DictReader(open(Path(outdir) / 'MANIFEST.csv')):
        if r['kind'] == 'sheet':
            sha[Path(r['path']).name] = r['sha256']
    sheets = []
    for sid, d in sorted(ids.items()):
        M, g = load_sheet_model(ids, sid, outdir)
        ring = frame_ring(d); E, N = M.p2utm(ring[:, 0], ring[:, 1])
        with Image.open(Path(P['sheets']) / d['file']) as im:
            w, h = im.size
        o = old.get(sid, {})
        n = (notes or {}).get(sid) or (
            f"survey sheet {int(d['num'])} ({d['file'][9:-4].replace('_', ' ')}); grid x {d['x_w']}..{d['x_e']} ft, y {d['y_s']}..{d['y_n']} ft; "
            + (f"{len(g['controls'])} street controls" if g['controls'] else 'no street controls (start model plus the survey-wide correction)'))
        sheets.append(dict(id=sid, file=d['file'], sha256=sha[d['file']], px_w=int(w), px_h=int(h),
                           bounds_26916=[round(float(E.min()), 2), round(float(N.min()), 2), round(float(E.max()), 2), round(float(N.max()), 2)],
                           georef='fitted', contours=(contours or {}).get(sid, o.get('contours', 'none')), note=n))
    json.dump(dict(crs='EPSG:26916', contour_interval_ft=5, datum_note=DATUM_NOTE, sheets=sheets), open(out, 'w'), indent=1)
    return sheets


if __name__ == '__main__':
    write(sys.argv[1] if len(sys.argv) > 1 else 'configs/ground_paths.json', sys.argv[2] if len(sys.argv) > 2 else 'ground/1912')
