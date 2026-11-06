"""Write ground/1912/MANIFEST.csv: every raw input on the build machine with bytes and sha256 (SPEC section 3).
Paths are written relative to the repository root ('..' is the folder that holds the repo on Ben's machine)."""
import csv, hashlib, json, os, sys, zipfile
from pathlib import Path


def sha(path=None, data=None):
    h = hashlib.sha256()
    if data is not None:
        h.update(data)
    else:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
    return h.hexdigest()


def rel(p, repo):
    return os.path.relpath(p, repo).replace(os.sep, '/')


def rows(P, repo):
    sheets = Path(P['sheets'])
    for f in sorted(sheets.glob('Sheet_*.jpg')):
        yield rel(f, repo), f.stat().st_size, sha(f), 'sheet', '1912 City Topographic Survey sheet scan (CHPL CONTENTdm p16998coll9/707)'
    for key, note in (('sheet_index', 'sheet grid extents (survey feet from the Hughes High School station) and border corners in scan pixels'),
                      ('georef_start', 'existing joint 1912 transform (Coons neatline + regional field + per-sheet shape, fitted to LiDAR 25 ft lines); starting registration')):
        f = Path(P[key]); yield rel(f, repo), f.stat().st_size, sha(f), 'transform', note
    z = Path(P['picks12'])
    yield rel(z, repo), z.stat().st_size, sha(z), 'picks', 'Topography workspace export zip; the 1912 picks are its sbg/picks12/*.json entries (rows below)'
    with zipfile.ZipFile(z) as zf:
        for n in sorted(x for x in zf.namelist() if x.startswith('sbg/picks12/') and x.endswith('.json')):
            b = zf.read(n); yield rel(z, repo) + '!' + n, len(b), sha(data=b), 'picks', 'named 1912 street intersections read off the georeferenced survey (UTM)'
    f = Path(P['osm_streets'])
    yield rel(f, repo), f.stat().st_size, sha(f), 'picks', "OpenStreetMap highway ways (Overpass, 7 Oct 2026): today's street centrelines, the ground side of the intersection controls"
    for f in sorted(Path(P['lidar_2m']).glob('DEM2m_*.tif')):
        yield rel(f, repo), f.stat().st_size, sha(f), 'lidar', 'USGS 3DEP 1 m DEM resampled to 2 m, int16 dm NAVD88, EPSG:26916; registration, datum fit and checks only'
    for f in sorted(Path(P['usgs1914']).glob('OH_*Cincinnati_*_1914_62500_geo.tif')):
        yield rel(f, repo), f.stat().st_size, sha(f), 'usgs1914', 'USGS 1:62,500 historical quadrangle GeoTIFF (TNM HTMC)'
    if P.get('i4_tiles'):
        for f in sorted(Path(P['i4_tiles']).rglob('*')):
            if f.is_file():
                yield rel(f, repo), f.stat().st_size, sha(f), 'i4_tile', ''


def main(paths, out):
    P = json.load(open(paths))
    repo = Path(paths).resolve().parent.parent
    with open(out, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['path', 'bytes', 'sha256', 'kind', 'note'])
        n = 0
        for r in rows(P, repo):
            w.writerow(r); n += 1
    print(f'MANIFEST.csv: {n} rows')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'configs/ground_paths.json', sys.argv[2] if len(sys.argv) > 2 else 'ground/1912/MANIFEST.csv')
