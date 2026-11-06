"""Street-intersection control points for the 1912 sheets.

Ground side: today's named-street intersections from OpenStreetMap (two or more different street names meeting at one
OSM node). Sheet side: the same intersection found on the scan by fitting today's centreline network (within 60 m)
into the sheet's street corridors (the space between the double black street lines), searching +-25 m around the
start model's prediction. Only intersections whose streets still run where the 1912 sheet drew them fit well; the
rest (new, widened or moved streets) are rejected by the fit score, the peak's uniqueness and agreement with
neighbouring controls.
"""
import json, math
import numpy as np, cv2
from scipy import ndimage as ndi
from scipy.ndimage import map_coordinates
from pyproj import Transformer

KEEP = {'primary', 'secondary', 'tertiary', 'residential', 'unclassified', 'living_street', 'trunk',
        'primary_link', 'secondary_link', 'tertiary_link'}
K = 2                      # work at half resolution (about 0.67 m per pixel)
WIN_M = 40.0               # template radius
SEARCH_M = 8.0             # search radius around the start model's prediction
CORR_M = 14.0              # closing radius that fills street corridors (up to about 28 m wide) but not blocks
FINE_M = 4.0               # fine search radius around the coarse peak


def osm_network(path):
    """Named street centrelines (UTM) and their intersections: (lines, inter) with inter = [(E, N, names)]."""
    tr = Transformer.from_crs(4326, 26916, always_xy=True)
    gj = json.load(open(path, encoding='utf-8'))
    lines = []; node = {}
    for f in gj['features']:
        p = f['properties']
        if p.get('highway') not in KEEP or not p.get('name') or p.get('bridge') or p.get('tunnel'):
            continue
        c = f['geometry']['coordinates']
        E, N = tr.transform([x for x, _ in c], [y for _, y in c])
        lines.append((np.c_[E, N], p['name']))
        for (x, y) in c:
            node.setdefault((x, y), set()).add(p['name'])
    inter = []
    for (x, y), names in node.items():
        if len(names) >= 2:
            E, N = tr.transform(x, y); inter.append((E, N, tuple(sorted(names))))
    return lines, inter


def densify(xy, step):
    out = [xy[:1]]
    for a, b in zip(xy[:-1], xy[1:]):
        n = max(1, int(math.ceil(np.hypot(*(b - a)) / step)))
        t = np.arange(1, n + 1)[:, None] / n
        out.append(a + (b - a) * t)
    return np.vstack(out)


def street_edges(img_bgr):
    """Half-resolution mask of long black strokes (street edges); letters and short marks removed."""
    im = cv2.resize(img_bgr, (img_bgr.shape[1] // K, img_bgr.shape[0] // K), interpolation=cv2.INTER_AREA)
    lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)
    L = lab[..., 0].astype(np.int16); a = lab[..., 1].astype(np.int16) - 128
    bgL = cv2.medianBlur(lab[..., 0], 41).astype(np.int16)
    black = ((bgL - L) > 45) & (a < 12)                   # dark and not red
    n, lab_, st, _ = cv2.connectedComponentsWithStats(black.astype(np.uint8), connectivity=8)
    big = np.maximum(st[:, cv2.CC_STAT_WIDTH], st[:, cv2.CC_STAT_HEIGHT]) >= 45   # about 30 m
    big[0] = False
    return big[lab_]


class SheetMatcher:
    def __init__(self, img_bgr, start_sheet, frame_px):
        self.edges = street_edges(img_bgr)
        self.D = cv2.distanceTransform((~self.edges).astype(np.uint8), cv2.DIST_L2, 5)   # half-res px
        self.st = start_sheet
        # street corridors: gaps between edge lines narrow enough to close with a 14 m disc; block interiors stay open
        E, N = start_sheet.p2utm(np.array([4000.0, 4100.0]), np.array([3500.0, 3500.0]))
        r = int(round(CORR_M / (float(np.hypot(E[1] - E[0], N[1] - N[0]) / 100 * K))))
        disc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
        closed = cv2.morphologyEx(self.edges.astype(np.uint8), cv2.MORPH_CLOSE, disc).astype(bool)
        self.corr = closed & ~self.edges
        self.corr_f = cv2.GaussianBlur(self.corr.astype(np.float32), (0, 0), 1.0)
        self.Dc = np.where(self.corr, self.D, 0).astype(np.float32)
        fr = np.zeros(self.edges.shape, np.uint8)
        cv2.fillPoly(fr, [(np.float32(frame_px) / K).astype(np.int32)], 1)
        self.frame = cv2.erode(fr, np.ones((25, 25), np.uint8)).astype(bool)
        # metres per half-res pixel, from the start model
        E, N = start_sheet.p2utm(np.array([4000.0, 4100.0]), np.array([3500.0, 3500.0]))
        self.mpp = float(np.hypot(E[1] - E[0], N[1] - N[0]) / 100 * K)

    def match(self, E, N, lines_near):
        """Locate one intersection. lines_near: [(xy, name)]. Returns dict or None."""
        mpp = self.mpp
        pts = []; wts = []
        for xy, nm in lines_near:
            d = densify(xy, 1.0); keep = np.hypot(d[:, 0] - E, d[:, 1] - N) <= WIN_M
            if keep.sum() >= 3:
                pts.append(d[keep]); wts.append(np.full(keep.sum(), 1.0 / keep.sum()))   # every street weighs the same
        if len(pts) < 2:
            return None
        P = np.vstack(pts); wt = np.concatenate(wts); wt /= wt.sum()
        u, v = self.st.utm2p(P[:, 0], P[:, 1]); u = u / K; v = v / K
        cu, cv_ = self.st.utm2p(np.array([E]), np.array([N])); cu = cu[0] / K; cv_ = cv_[0] / K
        H, W = self.D.shape
        rs = (WIN_M + SEARCH_M) / mpp + 2
        if not (rs < cu < W - rs and rs < cv_ < H - rs) or not self.frame[int(cv_), int(cu)]:
            return None
        if np.average(self.frame[np.clip(v.astype(int), 0, H - 1), np.clip(u.astype(int), 0, W - 1)], weights=wt) < 0.95:
            return None
        # centring score on a quarter-pixel lattice over +-SEARCH_M
        f = int(round(SEARCH_M / mpp * 2)); fs = np.arange(-f, f + 1) / 2.0
        sc = np.empty((len(fs), len(fs)), np.float32)
        for i, dy in enumerate(fs):
            vv = v + dy
            for j, dx in enumerate(fs):
                sc[i, j] = map_coordinates(self.Dc, [vv, u + dx], order=1, mode='nearest') @ wt
        a, b = np.unravel_index(np.argmax(sc), sc.shape)
        if a in (0, len(fs) - 1) or b in (0, len(fs) - 1):
            return None
        # refine to 0.1 px with a local quadratic; its curvature says how well the peak is pinned in each direction
        Z = sc[a - 1:a + 2, b - 1:b + 2].astype(float)
        gx = (Z[1, 2] - Z[1, 0]) / 2; gy = (Z[2, 1] - Z[0, 1]) / 2
        hxx = Z[1, 2] - 2 * Z[1, 1] + Z[1, 0]; hyy = Z[2, 1] - 2 * Z[1, 1] + Z[0, 1]
        hxy = (Z[2, 2] - Z[2, 0] - Z[0, 2] + Z[0, 0]) / 4
        Hm = np.array([[hxx, hxy], [hxy, hyy]]); ev = np.linalg.eigvalsh(Hm)
        step = 0.5
        try:
            off = -np.linalg.solve(Hm, [gx, gy]) if ev.max() < 0 else np.zeros(2)
        except np.linalg.LinAlgError:
            off = np.zeros(2)
        off = np.clip(off, -1, 1) * step
        dx = fs[b] + off[0]; dy = fs[a] + off[1]
        inside = float(map_coordinates(self.corr.astype(np.float32), [v + dy, u + dx], order=0, mode='nearest') @ wt)
        # curvature in (corridor px) per (m of shift)^2, the weaker direction
        curv = float(-ev.max() / (step * mpp) ** 2)
        return dict(px=[float((cu + dx) * K), float((cv_ + dy) * K)], shift_m=[float(dx * mpp), float(dy * mpp)],
                    inside=inside, curv=curv, peak=float(sc[a, b] * mpp), n_streets=len(pts))
