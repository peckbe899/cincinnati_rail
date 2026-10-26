"""Ben's FS Layout.kmz, New RER A-D Platform.kmz and New RER B Platform.kmz (2026-10-05) turned into the drawing frame. Frame as warp_rot.py: lon/lat to local metres (spherical
Mercator, R 6378137, scaled by cos lat0) about (-84.5125, 39.1018), then turned so v runs up Vine (true bearing 349):
u = x cos11 + y sin11, v = -x sin11 + y cos11. True north is 11 degrees clockwise of frame north."""
import re, json, numpy as np
LON0, LAT0, R = -84.5125, 39.1018, 6378137.0
C, S = np.cos(np.radians(11.0)), np.sin(np.radians(11.0))


def to_frame(lon, lat):
    k = R * np.cos(np.radians(LAT0))
    x = k * np.radians(lon - LON0)
    y = k * (np.log(np.tan(np.pi / 4 + np.radians(lat) / 2)) - np.log(np.tan(np.pi / 4 + np.radians(LAT0) / 2)))
    return np.array([C * x + S * y, -S * x + C * y])


def load(path='kmz_fs/doc.kml'):
    s = open(path, encoding='utf-8').read()
    out = {}
    for nm, co in re.findall(r'<Placemark>.*?<name>(.*?)</name>.*?<coordinates>(.*?)</coordinates>', s, re.S):
        pts = [tuple(float(v) for v in c.split(',')[:2]) for c in co.split()]
        out[nm] = np.array([to_frame(*p) for p in pts])
    return out


if __name__ == '__main__':
    L = load()
    for extra in ('kmz_ad/doc.kml', 'kmz_b/doc.kml'):          # New RER A-D Platform.kmz, New RER B Platform.kmz (2026-10-05)
        L.update(load(extra))
    for nm, p in L.items():
        a, b = p[0], p[-1]; d = b - a
        print('%-20s (%7.1f,%7.1f) -> (%7.1f,%7.1f)  centre (%6.1f,%6.1f)  length %5.1f m = %5.1f ft  frame angle %6.2f deg'
              % (nm, *a, *b, *((a + b) / 2), np.hypot(*d), np.hypot(*d) / 0.3048, np.degrees(np.arctan2(d[1], d[0]))))
    json.dump({k: v.tolist() for k, v in L.items()}, open('fs_kmz_layout.json', 'w'), indent=1)
