"""Census step 1c: MEASURED scale (px per foot of ground) where a plate has been georeferenced (21 Nov 2026).

Two independent sources, read-only:
  * placement grids cufp/N/model.npz (plates 43, 44, 45, 80, 82A): plate px at ground points STEP m apart (UTM);
  * QGIS georeferencer points Sanborn/Maps/*.pdf.points, *.png.points and New Sanborn/PNG/*.png.points: sheet px
    against EPSG:3857 metres, fitted with an affine by least squares; Web-Mercator metres are divided by
    1/cos(latitude) to give ground metres (a file in UTM, such as New Sanborn/PNG/40.png.points, is used as it is). QGIS/GDAL opens a PDF by drawing it at 150 dpi, so a .pdf.points pixel is
    (page width in pt * 150/72) / (scan width in px) of a scan pixel, about 2 scan px: corrected here (render_factor).
px/ft -> ft per inch at the scan's 300 px per inch: 300 / (px/ft).
    python scale_measure.py  -> scale/measured.json
"""
import json, os, glob, math, re
import numpy as np
import fitz

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'scale'); os.makedirs(OUT, exist_ok=True)
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
res = {}
for n in ('43', '44', '45', '80', '82A'):
    z = np.load(D + f'cufp/{n}/model.npz'); step = float(z['step']); px, py = z['px'].astype(float), z['py'].astype(float)
    bad = (px < -1e5) | (py < -1e5); px[bad] = np.nan; py[bad] = np.nan
    dx = np.hypot(np.diff(px, axis=1), np.diff(py, axis=1)); dy = np.hypot(np.diff(px, axis=0), np.diff(py, axis=0))
    ppm = float(np.nanmedian(np.r_[dx[np.isfinite(dx)], dy[np.isfinite(dy)]])) / step
    res[n] = dict(source=f'cufp/{n}/model.npz (placement)', px_per_ft=round(ppm * 0.3048, 3), ft_per_inch=round(300 / (ppm * 0.3048), 1))

files = glob.glob('C:/Users/peckb/Documents/CS2/Sanborn/Maps/*.points') + glob.glob('C:/Users/peckb/Documents/CS2/New Sanborn/PNG/*.points')
for f in files:
    m = re.search(r'(?:Sanborn Cincinnati )?(\d+[ab]?)\.(pdf|png)\.points$', os.path.basename(f), re.I)
    if not m: continue
    rows = []; head = open(f, encoding='utf8', errors='replace').readline(); merc = 'Pseudo-Mercator' in head   # else a metric projected CRS (UTM)
    for line in open(f, encoding='utf8', errors='replace'):
        if line.startswith('#') or line.startswith('mapX'): continue
        p = line.strip().split(',')
        if len(p) >= 5 and p[4].strip() == '1': rows.append([float(v) for v in p[:4]])
    if len(rows) < 3: continue
    a = np.array(rows); X = np.c_[a[:, 2], a[:, 3], np.ones(len(a))]
    cx, *_ = np.linalg.lstsq(X, a[:, 0], rcond=None); cy, *_ = np.linalg.lstsq(X, a[:, 1], rcond=None)
    J = np.array([[cx[0], cx[1]], [cy[0], cy[1]]])            # merc m per px
    merc_per_px = math.sqrt(abs(np.linalg.det(J)))
    lat = math.degrees(2 * math.atan(math.exp(a[:, 1].mean() / 6378137.0)) - math.pi / 2) if merc else 0.0
    fac = 1.0
    if m.group(2).lower() == 'pdf':   # GDAL draws a PDF at 150 dpi: points are in that render's px, not the scan's
        doc = fitz.open(f[:-len('.points')]); x = doc.extract_image(doc[0].get_images(full=True)[0][0]); fac = x['width'] / (doc[0].rect.width * 150 / 72)
    m_per_px = merc_per_px * math.cos(math.radians(lat)) / fac; ppf = 0.3048 / m_per_px
    n = m.group(1).upper(); key = n + ('' if m.group(2).lower() == 'pdf' else ' (png)')
    res[key] = dict(source=f.replace('\\', '/'), points=len(rows), render_factor=round(fac, 3), px_per_ft=round(ppf, 3), ft_per_inch=round(300 / ppf, 1), crs='EPSG:3857' if merc else head[7:40])
json.dump(res, open(OUT + '/measured.json', 'w'), indent=1)
for k, v in sorted(res.items()): print(k, v['px_per_ft'], v['ft_per_inch'], v.get('points', ''), os.path.basename(v['source']))
