// The old page's exports (claude/hub_maps/profiles_parity.md, section C: R16 to R19; profiles.html 3776-3893): the
// long section as a PNG, the profile as JSON with a sample every 10 m, the designed rail by structure and the
// stations as GeoJSON, and the rail and stations for Google Earth as a KMZ (one stored doc.kml in a zip). Built
// from the draft as it is now, saved or not, so what Ben exports is what he sees. Pure builders, and a download.

/** What an export reads: the line, its plan path, the rail and types of the draft's solves, the stations. */
export interface ExportModel {
  id: string;
  line: string;
  system: string;
  length: number;
  platform: number;
  /** [c, lon, lat] */
  path: readonly (readonly [number, number, number])[];
  railAt(c: number): number | null;
  groundAt(c: number): number | null;
  surveyedAt(c: number): number | null;
  typeAt(c: number): string | null;
  stations: {
    name: string;
    c: number;
    point_c: number;
    rail: number | null;
    ground: number | null;
    depth: number | null;
    type: string | null;
    sg: number;
  }[];
  /** the draft's profile fields as the old page saved them */
  profile: Record<string, unknown>;
  summary: { km_by_type: Record<string, number>; max_grade_permille: number; grades_over_limit: number } | null;
  /** the line's KML colour (aabbggrr), purple when it has none */
  colorKml?: string;
}

export const TYPE_LABEL: Record<string, string> = {
  elevated: "Elevated",
  atgrade: "At grade",
  trough: "Open trough",
  cutcover: "Cut & cover",
  shield: "Shield tunnel",
  deep: "Deep bore (TBM)",
  sunk: "Sunk box",
};

const r2 = (v: number | null): number | null => (v === null || !Number.isFinite(v) ? null : Math.round(v * 100) / 100);
const r7 = (v: number): number => Math.round(v * 1e7) / 1e7;

/** The plan position at c on a path of [c, lon, lat] (pathAt 617). */
export function pathAt(path: ExportModel["path"], c: number): [number, number] {
  let j = 1;
  while (j < path.length - 1 && ((path[j] as readonly number[])[0] as number) < c) j++;
  const a = path[j - 1] as readonly [number, number, number];
  const b = (path[j] ?? a) as readonly [number, number, number];
  const t = b[0] - a[0] > 0 ? Math.max(0, Math.min(1, (c - a[0]) / (b[0] - a[0]))) : 0;
  return [a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
}

/** Export JSON (3801-3806): the profile, the derived stations and summary, and a sample every 10 m. */
/** The profile's fields keyed by station (st, sg, so, stt, access by key; del and gapfill as lists) re-keyed from the
 * hub's platform ids to the old doc's station keys (name, or name#idx), as serialize (3213-3229) wrote them. A key
 * the line does not know is kept as it is. */
export function profileByKey(
  profile: Record<string, unknown>,
  keyOf: (platformId: string) => string | null,
): Record<string, unknown> {
  const k = (id: string) => keyOf(id) ?? id;
  const out: Record<string, unknown> = { ...profile };
  for (const f of ["st", "sg", "so", "stt", "access"]) {
    const v = profile[f];
    if (v && typeof v === "object" && !Array.isArray(v))
      out[f] = Object.fromEntries(Object.entries(v as Record<string, unknown>).map(([id, x]) => [k(id), x]));
  }
  for (const f of ["del", "gapfill"]) {
    const v = profile[f];
    if (Array.isArray(v)) out[f] = v.map((id) => (typeof id === "string" ? k(id) : id));
  }
  return out;
}

export function exportJson(m: ExportModel, now: string): string {
  const rows: [number, number | null, number | null, string | null, number | null][] = [];
  for (let c = 0; c <= m.length; c += 10) {
    rows.push([c, r2(m.groundAt(c)), r2(m.railAt(c)), m.typeAt(c), r2(m.surveyedAt(c))]);
  }
  const body = {
    v: 1,
    system: m.system,
    line: m.line,
    length_m: m.length,
    platform_m: m.platform,
    ...m.profile,
    stations: m.stations.map((s) => ({
      name: s.name,
      c: s.c,
      point_c: s.point_c,
      rail: s.rail,
      ground: r2(s.ground),
      depth: r2(s.depth),
      type: s.type,
    })),
    ...(m.summary ? { summary: m.summary } : {}),
    updated: now,
    samples_every_10m: { fields: ["chain_m", "ground_m", "rail_m", "structure", "ground_surveyed_m"], rows },
  };
  return JSON.stringify(body, null, 1);
}

const STEP = 10;
const WIDTH = 4;
const DEFAULT_KML = "ff800080";

function pts(m: ExportModel, a: number, b: number): [number, number, number][] {
  const out: [number, number, number][] = [];
  const at = (c: number): [number, number, number] => {
    const [lon, lat] = pathAt(m.path, c);
    return [r7(lon), r7(lat), r2(m.railAt(c)) ?? 0];
  };
  for (let c = a; c < b; c += STEP) out.push(at(c));
  out.push(at(b));
  return out;
}

/** The runs of one structure (found every 5 m) and the stations (exportModel 3818-3836). */
function exportModel(m: ExportModel) {
  const runs: { t: string; c0: number; c1: number; pts?: [number, number, number][] }[] = [];
  let cur: { t: string; c0: number; c1: number } | null = null;
  for (let c = 0; ; c = Math.min(c + 5, m.length)) {
    const t = m.typeAt(c) ?? "atgrade";
    if (!cur || cur.t !== t) {
      if (cur) cur.c1 = c;
      cur = { t, c0: c, c1: c };
      runs.push(cur);
    }
    cur.c1 = c;
    if (c >= m.length) break;
  }
  const kept = runs.filter((r) => r.c1 - r.c0 > 0.5);
  for (const r of kept) r.pts = pts(m, r.c0, r.c1);
  const half = m.platform / 2;
  const stations = m.stations.map((s) => {
    const [lon, lat] = pathAt(m.path, s.c);
    return {
      name: s.name,
      lon: r7(lon),
      lat: r7(lat),
      rail: r2(s.rail),
      c: r2(s.c),
      point_c: r2(s.point_c),
      ground: r2(s.ground),
      depth: r2(s.depth),
      structure: s.type ? (TYPE_LABEL[s.type] ?? s.type) : null,
      platform_m: r2(m.platform),
      platform_from: r2(s.c - half),
      platform_to: r2(s.c + half),
      platform_grade_permille: s.sg,
    };
  });
  return { line: pts(m, 0, m.length), runs: kept, stations };
}

const kmlColour = (m: ExportModel) =>
  /^[0-9a-f]{8}$/i.test(m.colorKml ?? "") ? (m.colorKml as string).toLowerCase() : DEFAULT_KML;
const kmlToHex = (k: string) => `#${k.slice(6, 8)}${k.slice(4, 6)}${k.slice(2, 4)}`;

function stamp(m: ExportModel, now: string) {
  return {
    line: m.line,
    id: m.id,
    system: m.system,
    length_m: r2(m.length),
    vertical_datum: "NAVD88 (m)",
    source: "Cincinnati Rail Profiles",
    exported: now,
  };
}

/** Export GeoJSON (3838-3851): the rail by structure (its type in the properties) and the stations, in 3D. */
export function exportGeoJson(m: ExportModel, now: string): string {
  const { runs, stations } = exportModel(m);
  const hex = kmlToHex(kmlColour(m));
  const fc = {
    type: "FeatureCollection",
    name: `${m.id}_profile`,
    properties: { ...stamp(m, now), color: hex },
    features: [
      ...runs.map((r) => ({
        type: "Feature",
        properties: {
          kind: "rail",
          line: m.line,
          structure: TYPE_LABEL[r.t] ?? r.t,
          type: r.t,
          from_m: r2(r.c0),
          to_m: r2(r.c1),
          length_m: r2(r.c1 - r.c0),
          rail_min_m: Math.min(...(r.pts ?? []).map((q) => q[2])),
          rail_max_m: Math.max(...(r.pts ?? []).map((q) => q[2])),
          stroke: hex,
          "stroke-width": WIDTH,
          "stroke-opacity": 1,
        },
        geometry: { type: "LineString", coordinates: r.pts },
      })),
      ...stations.map((st) => ({
        type: "Feature",
        properties: { kind: "station", line: m.line, ...st },
        geometry: { type: "Point", coordinates: [st.lon, st.lat, st.rail] },
      })),
    ],
  };
  return JSON.stringify(fc);
}

const xmlEsc = (t: unknown): string =>
  String(t).replace(
    /[&<>"']/g,
    (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;" })[ch] as string,
  );

/** The KML of the rail and the stations (buildKml 3853-3866). */
export function buildKml(m: ExportModel, now: string): string {
  const { line, stations } = exportModel(m);
  const meta = stamp(m, now);
  const c = kmlColour(m);
  const nm = `${meta.line} 3D`;
  const style =
    `<StyleMap id="rail"><Pair><key>normal</key><styleUrl>#rail_n</styleUrl></Pair><Pair><key>highlight</key><styleUrl>#rail_h</styleUrl></Pair></StyleMap>` +
    `<Style id="rail_n"><LineStyle><color>${c}</color><width>${WIDTH}</width></LineStyle></Style>` +
    `<Style id="rail_h"><LineStyle><color>${c}</color><width>${WIDTH}</width></LineStyle></Style>` +
    `<Style id="st"><IconStyle><scale>0.9</scale><Icon><href>http://maps.google.com/mapfiles/kml/shapes/rail.png</href></Icon></IconStyle><LineStyle><color>${c}</color><width>1</width></LineStyle></Style>`;
  const rail =
    `<Placemark><name>${xmlEsc(nm)}</name><styleUrl>#rail</styleUrl><LineString><extrude>1</extrude><altitudeMode>absolute</altitudeMode>` +
    `<coordinates>${line.map((q) => q.join(",")).join(" ")}</coordinates></LineString></Placemark>`;
  const sts = stations
    .map(
      (st) =>
        `<Placemark><name>${xmlEsc(st.name)}</name><styleUrl>#st</styleUrl><ExtendedData>` +
        Object.entries(st)
          .filter(([k]) => !["name", "lon", "lat"].includes(k))
          .map(([k, v]) => `<Data name="${k}"><value>${xmlEsc(v)}</value></Data>`)
          .join("") +
        `</ExtendedData><Point><extrude>1</extrude><altitudeMode>absolute</altitudeMode><coordinates>${st.lon},${st.lat},${st.rail}</coordinates></Point></Placemark>`,
    )
    .join("");
  return (
    `<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2"><Document><name>${xmlEsc(nm)}</name>` +
    `<description>${xmlEsc(`${meta.system} ${meta.line}: designed rail at rail level (absolute altitude, ${meta.vertical_datum}), extruded to the ground; stations at the platform centre. Exported ${meta.exported}.`)}</description>` +
    `${style}${rail}<Folder><name>Stations</name>${sts}</Folder></Document></kml>`
  );
}

const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

export function crc32(b: Uint8Array): number {
  let c = 0xffffffff;
  for (let i = 0; i < b.length; i++) c = (CRC_TABLE[(c ^ (b[i] as number)) & 0xff] as number) ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

/** A stored (uncompressed) zip of one file (zipBytes 3870-3883): a KMZ when the file is doc.kml. */
export function zipBytes(name: string, bytes: Uint8Array): Uint8Array {
  const nm = new TextEncoder().encode(name);
  const crc = crc32(bytes);
  const n = bytes.length;
  const put = (dv: DataView, fields: [number, number, number][]) => {
    for (const [o, v, w] of fields) {
      if (w === 4) dv.setUint32(o, v, true);
      else dv.setUint16(o, v, true);
    }
  };
  const local = new DataView(new ArrayBuffer(30));
  put(local, [
    [0, 0x04034b50, 4],
    [4, 20, 2],
    [6, 0, 2],
    [8, 0, 2],
    [10, 0, 2],
    [12, 0x21, 2],
    [14, crc, 4],
    [18, n, 4],
    [22, n, 4],
    [26, nm.length, 2],
    [28, 0, 2],
  ]);
  const cen = new DataView(new ArrayBuffer(46));
  put(cen, [
    [0, 0x02014b50, 4],
    [4, 20, 2],
    [6, 20, 2],
    [8, 0, 2],
    [10, 0, 2],
    [12, 0, 2],
    [14, 0x21, 2],
    [16, crc, 4],
    [20, n, 4],
    [24, n, 4],
    [28, nm.length, 2],
    [30, 0, 2],
    [32, 0, 2],
    [34, 0, 2],
    [36, 0, 2],
    [38, 0, 4],
    [42, 0, 4],
  ]);
  const end = new DataView(new ArrayBuffer(22));
  const cenOff = 30 + nm.length + n;
  put(end, [
    [0, 0x06054b50, 4],
    [4, 0, 2],
    [6, 0, 2],
    [8, 1, 2],
    [10, 1, 2],
    [12, 46 + nm.length, 4],
    [16, cenOff, 4],
    [20, 0, 2],
  ]);
  const parts = [new Uint8Array(local.buffer), nm, bytes, new Uint8Array(cen.buffer), nm, new Uint8Array(end.buffer)];
  const out = new Uint8Array(parts.reduce((a, x) => a + x.length, 0));
  let o = 0;
  for (const x of parts) {
    out.set(x, o);
    o += x.length;
  }
  return out;
}

/** The KMZ of a line: doc.kml stored in a zip. */
export const exportKmz = (m: ExportModel, now: string): Uint8Array =>
  zipBytes("doc.kml", new TextEncoder().encode(buildKml(m, now)));

/** Hand a file to the browser to save (a plain download; the hub has no downloads capability to ask). */
export function download(filename: string, data: Blob): void {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(data);
  a.download = filename;
  a.dataset.testid = "export-download";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}
