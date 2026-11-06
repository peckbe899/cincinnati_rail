"""Today's 2 m LiDAR (int16 dm NAVD88): registration aid, datum fit and checks only, never written into the surface."""
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import from_bounds


def build_vrt(P):
    tiles = sorted(Path(P['lidar_2m']).glob('DEM2m_*.tif'))
    out = Path(P['work']) / 'lidar_2m.vrt'
    if out.exists():
        return out
    bounds = []
    for t in tiles:
        with rasterio.open(t) as d:
            bounds.append((t, d.bounds, d.width, d.height, d.crs.to_wkt()))
    x0 = min(b.left for _, b, *_ in bounds); x1 = max(b.right for _, b, *_ in bounds)
    y0 = min(b.bottom for _, b, *_ in bounds); y1 = max(b.top for _, b, *_ in bounds)
    W = int(round((x1 - x0) / 2)); H = int(round((y1 - y0) / 2))
    xml = [f'<VRTDataset rasterXSize="{W}" rasterYSize="{H}">', f'<SRS>{bounds[0][4]}</SRS>',
           f'<GeoTransform>{x0}, 2.0, 0.0, {y1}, 0.0, -2.0</GeoTransform>',
           '<VRTRasterBand dataType="Int16" band="1"><NoDataValue>-32768</NoDataValue>']
    for t, b, w, h, _ in bounds:
        xo = int(round((b.left - x0) / 2)); yo = int(round((y1 - b.top) / 2))
        xml.append(f'<SimpleSource><SourceFilename relativeToVRT="0">{t.as_posix()}</SourceFilename><SourceBand>1</SourceBand>'
                   f'<SrcRect xOff="0" yOff="0" xSize="{w}" ySize="{h}"/><DstRect xOff="{xo}" yOff="{yo}" xSize="{w}" ySize="{h}"/></SimpleSource>')
    xml.append('</VRTRasterBand></VRTDataset>')
    out.write_text('\n'.join(xml))
    return out


class Lidar:
    def __init__(self, P):
        self.ds = rasterio.open(build_vrt(P))
        self.x0, self.y1 = self.ds.transform.c, self.ds.transform.f

    def window(self, x0, y0, x1, y1):
        """Metres NAVD88 (NaN = no data) on the 2 m lattice covering the box, with its origin."""
        x0 = np.floor(x0 / 2) * 2; y1 = np.ceil(y1 / 2) * 2; x1 = np.ceil(x1 / 2) * 2; y0 = np.floor(y0 / 2) * 2
        a = self.ds.read(1, window=from_bounds(x0, y0, x1, y1, self.ds.transform), boundless=True, fill_value=-32768).astype(np.float32)
        a[a == -32768] = np.nan
        return a / 10.0, x0, y1

    def sample(self, E, N):
        E = np.asarray(E, float); N = np.asarray(N, float)
        if not len(E):
            return np.zeros(0)
        a, x0, y1 = self.window(E.min() - 4, N.min() - 4, E.max() + 4, N.max() + 4)
        from scipy.ndimage import map_coordinates
        r = (y1 - N) / 2 - 0.5; c = (E - x0) / 2 - 0.5
        bad = map_coordinates(np.isnan(a).astype(np.float32), [r, c], order=1, mode='nearest') > 0.01
        z = map_coordinates(np.nan_to_num(a), [r, c], order=1, mode='nearest')
        z[bad] = np.nan
        return z
