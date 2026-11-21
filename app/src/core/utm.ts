// UTM zone 16N on GRS80 (EPSG:26916, NAD83), both ways, by the series in Snyder's "Map Projections: A Working
// Manual" (USGS 1395, pages 61 to 64). Good to well under a millimetre across the region, which is far more than the
// map needs: the server sends GeoJSON in EPSG:4326, and the app projects only image corners and readouts.

const A = 6378137;
const F = 1 / 298.257222101;
const E2 = F * (2 - F);
const EP2 = E2 / (1 - E2);
const K0 = 0.9996;
const LON0 = (-87 * Math.PI) / 180;
const FALSE_E = 500000;

const E4 = E2 * E2;
const E6 = E4 * E2;
const M1 = 1 - E2 / 4 - (3 * E4) / 64 - (5 * E6) / 256;
const M2 = (3 * E2) / 8 + (3 * E4) / 32 + (45 * E6) / 1024;
const M3 = (15 * E4) / 256 + (45 * E6) / 1024;
const M4 = (35 * E6) / 3072;

function meridian(phi: number): number {
  return A * (M1 * phi - M2 * Math.sin(2 * phi) + M3 * Math.sin(4 * phi) - M4 * Math.sin(6 * phi));
}

/** [lon, lat] in degrees for an EPSG:26916 easting and northing in metres. */
export function utmToLonLat(e: number, n: number): [number, number] {
  const x = e - FALSE_E;
  const mu = n / K0 / (A * M1);
  const e1 = (1 - Math.sqrt(1 - E2)) / (1 + Math.sqrt(1 - E2));
  const phi1 =
    mu +
    ((3 * e1) / 2 - (27 * e1 ** 3) / 32) * Math.sin(2 * mu) +
    ((21 * e1 ** 2) / 16 - (55 * e1 ** 4) / 32) * Math.sin(4 * mu) +
    ((151 * e1 ** 3) / 96) * Math.sin(6 * mu) +
    ((1097 * e1 ** 4) / 512) * Math.sin(8 * mu);
  const s = Math.sin(phi1);
  const c = Math.cos(phi1);
  const t = Math.tan(phi1);
  const c1 = EP2 * c * c;
  const t1 = t * t;
  const n1 = A / Math.sqrt(1 - E2 * s * s);
  const r1 = (A * (1 - E2)) / (1 - E2 * s * s) ** 1.5;
  const d = x / (n1 * K0);
  const lat =
    phi1 -
    ((n1 * t) / r1) *
      ((d * d) / 2 -
        ((5 + 3 * t1 + 10 * c1 - 4 * c1 * c1 - 9 * EP2) * d ** 4) / 24 +
        ((61 + 90 * t1 + 298 * c1 + 45 * t1 * t1 - 252 * EP2 - 3 * c1 * c1) * d ** 6) / 720);
  const lon =
    LON0 +
    (d -
      ((1 + 2 * t1 + c1) * d ** 3) / 6 +
      ((5 - 2 * c1 + 28 * t1 - 3 * c1 * c1 + 8 * EP2 + 24 * t1 * t1) * d ** 5) / 120) /
      c;
  return [(lon * 180) / Math.PI, (lat * 180) / Math.PI];
}

/** [easting, northing] in EPSG:26916 metres for a longitude and latitude in degrees. */
export function lonLatToUtm(lonDeg: number, latDeg: number): [number, number] {
  const phi = (latDeg * Math.PI) / 180;
  const lam = (lonDeg * Math.PI) / 180;
  const s = Math.sin(phi);
  const c = Math.cos(phi);
  const t = Math.tan(phi);
  const n = A / Math.sqrt(1 - E2 * s * s);
  const tt = t * t;
  const cc = EP2 * c * c;
  const a = c * (lam - LON0);
  const m = meridian(phi);
  const e =
    FALSE_E +
    K0 * n * (a + ((1 - tt + cc) * a ** 3) / 6 + ((5 - 18 * tt + tt * tt + 72 * cc - 58 * EP2) * a ** 5) / 120);
  const north =
    K0 *
    (m +
      n *
        t *
        ((a * a) / 2 +
          ((5 - tt + 9 * cc + 4 * cc * cc) * a ** 4) / 24 +
          ((61 - 58 * tt + tt * tt + 600 * cc - 330 * EP2) * a ** 6) / 720));
  return [e, north];
}
