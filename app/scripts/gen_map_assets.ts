// Generate the map's offline assets under app/public/map (decision 9.30): signed-distance glyph PBFs for the label
// font, a sprite, and the local style. Without committed glyphs MapLibre's labels fail silently offline.
//
//   node scripts/gen_map_assets.ts [--font path/to/DejaVuSans.ttf] [--out public/map]
//
// The glyphs follow node-fontnik's format: 24 px, a 3 px buffer, an SDF radius of 8 px and a cutoff of 0.25, so a
// pixel value of 192 is the glyph's edge. Every range from 0-255 to 65280-65535 is written, empty where the font
// has no glyph in it, so MapLibre never meets a 404. The font is DejaVu Sans (Bitstream Vera licence, kept beside
// the glyphs). The script needs only Node: it parses the TrueType outlines and rasterises them itself.

import { copyFileSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { deflateSync } from "node:zlib";

const here = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const arg = (name: string, dflt: string) => {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? (args[i + 1] as string) : dflt;
};
const FONT = arg("--font", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf");
const LICENSE = arg("--license", "/usr/share/doc/fonts-dejavu-core/copyright");
const OUT = resolve(arg("--out", join(here, "..", "public", "map")));
const STACK = "dejavu-sans";

const SIZE = 24;
const BUFFER = 3;
const RADIUS = 8;
const CUTOFF = 0.25;
/** Ranges given real glyphs: Latin, Latin-1, Latin Extended A and B, IPA, spacing marks, combining marks, Greek,
 * Latin Extended Additional, punctuation (dashes, quotes, per mille), letterlike, arrows, maths. */
const FILLED = [0, 256, 512, 768, 7680, 8192, 8448, 8704];

// ----------------------------------------------------------------------------------------------- TrueType parse

type Pt = { x: number; y: number; on: boolean };
type Contour = Pt[];

class Font {
  private readonly dv: DataView;
  private readonly tables = new Map<string, number>();
  readonly unitsPerEm: number;
  readonly ascender: number;
  private readonly locLong: boolean;
  private readonly numGlyphs: number;
  private readonly numHMetrics: number;
  readonly cmap = new Map<number, number>();

  constructor(buf: Buffer) {
    this.dv = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
    const n = this.u16(4);
    for (let i = 0; i < n; i++) {
      const rec = 12 + i * 16;
      const tag = String.fromCharCode(this.u8(rec), this.u8(rec + 1), this.u8(rec + 2), this.u8(rec + 3));
      this.tables.set(tag, this.u32(rec + 8));
    }
    const head = this.t("head");
    this.unitsPerEm = this.u16(head + 18);
    this.locLong = this.i16(head + 50) === 1;
    const hhea = this.t("hhea");
    this.ascender = this.i16(hhea + 4);
    this.numHMetrics = this.u16(hhea + 34);
    this.numGlyphs = this.u16(this.t("maxp") + 4);
    this.readCmap();
  }

  private t(tag: string): number {
    const o = this.tables.get(tag);
    if (o === undefined) throw new Error(`font has no ${tag} table`);
    return o;
  }
  private u8(o: number) {
    return this.dv.getUint8(o);
  }
  private u16(o: number) {
    return this.dv.getUint16(o);
  }
  private i16(o: number) {
    return this.dv.getInt16(o);
  }
  private u32(o: number) {
    return this.dv.getUint32(o);
  }

  private readCmap(): void {
    const cmap = this.t("cmap");
    const n = this.u16(cmap + 2);
    let best = -1;
    let bestFormat = 0;
    for (let i = 0; i < n; i++) {
      const pid = this.u16(cmap + 4 + i * 8);
      const eid = this.u16(cmap + 6 + i * 8);
      const off = cmap + this.u32(cmap + 8 + i * 8);
      const format = this.u16(off);
      if (pid === 3 && (eid === 1 || eid === 10) && (format === 4 || format === 12) && format >= bestFormat) {
        best = off;
        bestFormat = format;
      }
    }
    if (best < 0) throw new Error("font has no Unicode cmap");
    if (bestFormat === 12) {
      const groups = this.u32(best + 12);
      for (let g = 0; g < groups; g++) {
        const o = best + 16 + g * 12;
        const start = this.u32(o);
        const end = this.u32(o + 4);
        const gid = this.u32(o + 8);
        for (let c = start; c <= end; c++) this.cmap.set(c, gid + c - start);
      }
      return;
    }
    const segX2 = this.u16(best + 6);
    const ends = best + 14;
    const starts = ends + segX2 + 2;
    const deltas = starts + segX2;
    const offsets = deltas + segX2;
    for (let s = 0; s < segX2 / 2; s++) {
      const end = this.u16(ends + s * 2);
      const start = this.u16(starts + s * 2);
      const delta = this.i16(deltas + s * 2);
      const ro = this.u16(offsets + s * 2);
      for (let c = start; c <= end && c !== 0xffff; c++) {
        let gid: number;
        if (ro === 0) gid = (c + delta) & 0xffff;
        else {
          const g = this.u16(offsets + s * 2 + ro + (c - start) * 2);
          gid = g === 0 ? 0 : (g + delta) & 0xffff;
        }
        if (gid) this.cmap.set(c, gid);
      }
    }
  }

  advance(gid: number): number {
    const i = Math.min(gid, this.numHMetrics - 1);
    return this.u16(this.t("hmtx") + i * 4);
  }

  private glyphOffset(gid: number): [number, number] {
    const loca = this.t("loca");
    if (gid >= this.numGlyphs) return [0, 0];
    const a = this.locLong ? this.u32(loca + gid * 4) : this.u16(loca + gid * 2) * 2;
    const b = this.locLong ? this.u32(loca + gid * 4 + 4) : this.u16(loca + gid * 2 + 2) * 2;
    return [this.t("glyf") + a, b - a];
  }

  contours(gid: number, depth = 0): Contour[] {
    const [o, len] = this.glyphOffset(gid);
    if (len === 0 || depth > 8) return [];
    const nContours = this.i16(o);
    if (nContours < 0) return this.composite(o, depth);
    const endPts: number[] = [];
    for (let i = 0; i < nContours; i++) endPts.push(this.u16(o + 10 + i * 2));
    const nPts = (endPts[endPts.length - 1] ?? -1) + 1;
    let p = o + 10 + nContours * 2;
    p += 2 + this.u16(p);
    const flags: number[] = [];
    while (flags.length < nPts) {
      const f = this.u8(p++);
      flags.push(f);
      if (f & 8) {
        let r = this.u8(p++);
        while (r-- > 0) flags.push(f);
      }
    }
    const xs: number[] = [];
    let v = 0;
    for (const f of flags) {
      if (f & 2) {
        const d = this.u8(p++);
        v += f & 16 ? d : -d;
      } else if (!(f & 16)) {
        v += this.i16(p);
        p += 2;
      }
      xs.push(v);
    }
    const ys: number[] = [];
    v = 0;
    for (const f of flags) {
      if (f & 4) {
        const d = this.u8(p++);
        v += f & 32 ? d : -d;
      } else if (!(f & 32)) {
        v += this.i16(p);
        p += 2;
      }
      ys.push(v);
    }
    const out: Contour[] = [];
    let s = 0;
    for (const e of endPts) {
      const c: Contour = [];
      for (let i = s; i <= e; i++) c.push({ x: xs[i] ?? 0, y: ys[i] ?? 0, on: ((flags[i] ?? 0) & 1) === 1 });
      out.push(c);
      s = e + 1;
    }
    return out;
  }

  private composite(o: number, depth: number): Contour[] {
    let p = o + 10;
    const out: Contour[] = [];
    for (;;) {
      const flags = this.u16(p);
      const gid = this.u16(p + 2);
      p += 4;
      let dx: number;
      let dy: number;
      if (flags & 1) {
        dx = this.i16(p);
        dy = this.i16(p + 2);
        p += 4;
      } else {
        dx = (this.u8(p) << 24) >> 24;
        dy = (this.u8(p + 1) << 24) >> 24;
        p += 2;
      }
      let [a, b, c, d] = [1, 0, 0, 1];
      const f2 = (q: number) => this.i16(q) / 16384;
      if (flags & 8) {
        a = d = f2(p);
        p += 2;
      } else if (flags & 0x40) {
        a = f2(p);
        d = f2(p + 2);
        p += 4;
      } else if (flags & 0x80) {
        a = f2(p);
        b = f2(p + 2);
        c = f2(p + 4);
        d = f2(p + 6);
        p += 8;
      }
      for (const cont of this.contours(gid, depth + 1)) {
        out.push(cont.map((q) => ({ x: a * q.x + c * q.y + dx, y: b * q.x + d * q.y + dy, on: q.on })));
      }
      if (!(flags & 0x20)) break;
    }
    return out;
  }
}

// ------------------------------------------------------------------------------------------------ rasterise

type Seg = [number, number, number, number];

/** Line segments of the outline: quadratic B-splines flattened, implied on-curve points restored. */
function flatten(contours: Contour[], scale: number): Seg[] {
  const segs: Seg[] = [];
  for (const raw of contours) {
    if (raw.length < 2) continue;
    const pts: Pt[] = [];
    for (let i = 0; i < raw.length; i++) {
      const a = raw[i] as Pt;
      const b = raw[(i + 1) % raw.length] as Pt;
      pts.push(a);
      if (!a.on && !b.on) pts.push({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, on: true });
    }
    let start = pts.findIndex((q) => q.on);
    if (start < 0) start = 0;
    const ring = [...pts.slice(start), ...pts.slice(0, start)];
    let cur = ring[0] as Pt;
    const toPx = (q: Pt) => [q.x * scale, q.y * scale] as const;
    for (let i = 1; i <= ring.length; i++) {
      const q = ring[i % ring.length] as Pt;
      if (q.on) {
        const [x0, y0] = toPx(cur);
        const [x1, y1] = toPx(q);
        segs.push([x0, y0, x1, y1]);
        cur = q;
      } else {
        const end = ring[(i + 1) % ring.length] as Pt;
        const [x0, y0] = toPx(cur);
        const [cx, cy] = toPx(q);
        const [x1, y1] = toPx(end);
        const n = 8;
        let px = x0;
        let py = y0;
        for (let k = 1; k <= n; k++) {
          const t = k / n;
          const u = 1 - t;
          const x = u * u * x0 + 2 * u * t * cx + t * t * x1;
          const y = u * u * y0 + 2 * u * t * cy + t * t * y1;
          segs.push([px, py, x, y]);
          px = x;
          py = y;
        }
        cur = end;
        i++;
      }
    }
  }
  return segs;
}

function distToSeg(px: number, py: number, s: Seg): number {
  const [x0, y0, x1, y1] = s;
  const dx = x1 - x0;
  const dy = y1 - y0;
  const l2 = dx * dx + dy * dy;
  let t = l2 > 0 ? ((px - x0) * dx + (py - y0) * dy) / l2 : 0;
  t = Math.max(0, Math.min(1, t));
  const ex = x0 + t * dx - px;
  const ey = y0 + t * dy - py;
  return Math.sqrt(ex * ex + ey * ey);
}

function winding(px: number, py: number, segs: Seg[]): number {
  let w = 0;
  for (const [x0, y0, x1, y1] of segs) {
    if (y0 <= py) {
      if (y1 > py && (x1 - x0) * (py - y0) - (px - x0) * (y1 - y0) > 0) w++;
    } else if (y1 <= py && (x1 - x0) * (py - y0) - (px - x0) * (y1 - y0) < 0) w--;
  }
  return w;
}

interface Glyph {
  id: number;
  bitmap: Uint8Array | null;
  width: number;
  height: number;
  left: number;
  top: number;
  advance: number;
}

function renderGlyph(font: Font, code: number, ascenderPx: number): Glyph | null {
  const gid = font.cmap.get(code);
  if (gid === undefined) return null;
  const scale = SIZE / font.unitsPerEm;
  const advance = Math.round(font.advance(gid) * scale);
  const segs = flatten(font.contours(gid), scale);
  if (!segs.length) return { id: code, bitmap: null, width: 0, height: 0, left: 0, top: 0, advance };
  let xmin = Number.POSITIVE_INFINITY;
  let ymin = Number.POSITIVE_INFINITY;
  let xmax = Number.NEGATIVE_INFINITY;
  let ymax = Number.NEGATIVE_INFINITY;
  for (const [x0, y0, x1, y1] of segs) {
    xmin = Math.min(xmin, x0, x1);
    xmax = Math.max(xmax, x0, x1);
    ymin = Math.min(ymin, y0, y1);
    ymax = Math.max(ymax, y0, y1);
  }
  const left = Math.floor(xmin);
  const bottom = Math.floor(ymin);
  const top = Math.ceil(ymax);
  const width = Math.max(1, Math.ceil(xmax) - left);
  const height = Math.max(1, top - bottom);
  const bw = width + 2 * BUFFER;
  const bh = height + 2 * BUFFER;
  const bitmap = new Uint8Array(bw * bh);
  for (let y = 0; y < bh; y++) {
    for (let x = 0; x < bw; x++) {
      const px = left - BUFFER + x + 0.5;
      const py = top + BUFFER - y - 0.5;
      let d = Number.POSITIVE_INFINITY;
      for (const s of segs) d = Math.min(d, distToSeg(px, py, s));
      if (winding(px, py, segs) !== 0) d = -d;
      const v = 255 - 255 * (d / RADIUS + CUTOFF);
      bitmap[y * bw + x] = Math.max(0, Math.min(255, Math.round(v)));
    }
  }
  return { id: code, bitmap, width, height, left, top: top - ascenderPx, advance };
}

// ---------------------------------------------------------------------------------------------- protobuf

class Pb {
  private bytes: number[] = [];
  varint(v: number): void {
    let n = v >>> 0;
    while (n > 127) {
      this.bytes.push((n & 127) | 128);
      n >>>= 7;
    }
    this.bytes.push(n);
  }
  key(field: number, wire: number): void {
    this.varint((field << 3) | wire);
  }
  uint(field: number, v: number): void {
    this.key(field, 0);
    this.varint(v);
  }
  sint(field: number, v: number): void {
    this.key(field, 0);
    this.varint(((v << 1) ^ (v >> 31)) >>> 0);
  }
  bytesField(field: number, b: Uint8Array): void {
    this.key(field, 2);
    this.varint(b.length);
    for (const x of b) this.bytes.push(x);
  }
  string(field: number, s: string): void {
    this.bytesField(field, new TextEncoder().encode(s));
  }
  done(): Uint8Array {
    return Uint8Array.from(this.bytes);
  }
}

function encodeRange(name: string, range: string, glyphs: Glyph[]): Uint8Array {
  const stack = new Pb();
  stack.string(1, name);
  stack.string(2, range);
  for (const g of glyphs) {
    const m = new Pb();
    m.uint(1, g.id);
    if (g.bitmap) m.bytesField(2, g.bitmap);
    m.uint(3, g.width);
    m.uint(4, g.height);
    m.sint(5, g.left);
    m.sint(6, g.top);
    m.uint(7, g.advance);
    stack.bytesField(3, m.done());
  }
  const root = new Pb();
  root.bytesField(1, stack.done());
  return root.done();
}

// ------------------------------------------------------------------------------------------------ sprite

const CRC = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

function crc32(b: Uint8Array): number {
  let c = 0xffffffff;
  for (const x of b) c = (CRC[(c ^ x) & 255] as number) ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function png(w: number, h: number, rgba: Uint8Array): Buffer {
  const chunk = (type: string, data: Uint8Array) => {
    const len = Buffer.alloc(4);
    len.writeUInt32BE(data.length);
    const td = Buffer.concat([Buffer.from(type, "ascii"), Buffer.from(data)]);
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(crc32(td));
    return Buffer.concat([len, td, crc]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0);
  ihdr.writeUInt32BE(h, 4);
  ihdr[8] = 8;
  ihdr[9] = 6;
  const raw = Buffer.alloc(h * (w * 4 + 1));
  for (let y = 0; y < h; y++) {
    raw[y * (w * 4 + 1)] = 0;
    Buffer.from(rgba.buffer, rgba.byteOffset + y * w * 4, w * 4).copy(raw, y * (w * 4 + 1) + 1);
  }
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk("IHDR", ihdr),
    chunk("IDAT", deflateSync(raw, { level: 9 })),
    chunk("IEND", new Uint8Array(0)),
  ]);
}

type Shape = (x: number, y: number) => [number, number, number, number] | null;

/** Icons drawn as functions of a point in a unit box (0 to 1), anti-aliased by 4x4 supersampling. */
const ICONS: { name: string; size: number; shape: Shape }[] = [
  {
    name: "station",
    size: 12,
    shape: (x, y) => {
      const r = Math.hypot(x - 0.5, y - 0.5);
      if (r <= 0.32) return [255, 255, 255, 255];
      if (r <= 0.48) return [22, 24, 29, 255];
      return null;
    },
  },
  {
    name: "station-transfer",
    size: 14,
    shape: (x, y) => {
      const m = Math.max(Math.abs(x - 0.5), Math.abs(y - 0.5));
      if (m <= 0.3) return [255, 255, 255, 255];
      if (m <= 0.46) return [22, 24, 29, 255];
      return null;
    },
  },
  {
    name: "portal",
    size: 12,
    shape: (x, y) => (y > 0.15 && y < 0.88 && Math.abs(x - 0.5) < (y - 0.15) * 0.62 ? [240, 113, 120, 255] : null),
  },
  {
    name: "selected",
    size: 20,
    shape: (x, y) => {
      const r = Math.hypot(x - 0.5, y - 0.5);
      return r > 0.38 && r < 0.48 ? [90, 169, 230, 255] : null;
    },
  },
];

function sprite(ratio: number): { png: Buffer; json: Record<string, unknown> } {
  const pad = 2 * ratio;
  const sizes = ICONS.map((i) => i.size * ratio);
  const w = sizes.reduce((s, x) => s + x + pad, pad);
  const h = Math.max(...sizes) + 2 * pad;
  const rgba = new Uint8Array(w * h * 4);
  const json: Record<string, unknown> = {};
  let ox = pad;
  ICONS.forEach((icon, k) => {
    const s = sizes[k] as number;
    for (let y = 0; y < s; y++) {
      for (let x = 0; x < s; x++) {
        let r = 0;
        let g = 0;
        let b = 0;
        let a = 0;
        for (let sy = 0; sy < 4; sy++) {
          for (let sx = 0; sx < 4; sx++) {
            const c = icon.shape((x + (sx + 0.5) / 4) / s, (y + (sy + 0.5) / 4) / s);
            if (c) {
              r += c[0] * c[3];
              g += c[1] * c[3];
              b += c[2] * c[3];
              a += c[3];
            }
          }
        }
        const o = ((pad + y) * w + ox + x) * 4;
        if (a > 0) {
          rgba[o] = Math.round(r / a);
          rgba[o + 1] = Math.round(g / a);
          rgba[o + 2] = Math.round(b / a);
          rgba[o + 3] = Math.round(a / 16);
        }
      }
    }
    json[icon.name] = { x: ox, y: pad, width: s, height: s, pixelRatio: ratio };
    ox += s + pad;
  });
  return { png: png(w, h, rgba), json };
}

// -------------------------------------------------------------------------------------------------- main

const STYLE = {
  version: 8,
  name: "Cincinnati Rail hub, local",
  metadata: { about: "Generated by app/scripts/gen_map_assets.ts. Every URL is local (decision 9.30)." },
  glyphs: "/map/glyphs/{fontstack}/{range}.pbf",
  sprite: "/map/sprite",
  sources: {},
  layers: [{ id: "background", type: "background", paint: { "background-color": "#16181d" } }],
};

function main(): void {
  if (!existsSync(FONT)) throw new Error(`no font at ${FONT}; pass --font path/to/DejaVuSans.ttf`);
  const font = new Font(readFileSync(FONT));
  const ascenderPx = Math.round((font.ascender * SIZE) / font.unitsPerEm);
  const dir = join(OUT, "glyphs", STACK);
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });
  let glyphs = 0;
  let bytes = 0;
  for (let start = 0; start < 65536; start += 256) {
    const list: Glyph[] = [];
    if (FILLED.includes(start)) {
      for (let c = start; c < start + 256; c++) {
        const g = renderGlyph(font, c, ascenderPx);
        if (g) list.push(g);
      }
    }
    const range = `${start}-${start + 255}`;
    const buf = encodeRange(STACK, range, list);
    writeFileSync(join(dir, `${range}.pbf`), buf);
    glyphs += list.length;
    bytes += buf.length;
  }
  if (existsSync(LICENSE)) copyFileSync(LICENSE, join(OUT, "glyphs", "LICENSE-DejaVu.txt"));
  for (const ratio of [1, 2]) {
    const s = sprite(ratio);
    const suffix = ratio === 1 ? "" : "@2x";
    writeFileSync(join(OUT, `sprite${suffix}.png`), s.png);
    writeFileSync(join(OUT, `sprite${suffix}.json`), `${JSON.stringify(s.json, null, 1)}\n`);
  }
  writeFileSync(join(OUT, "style.json"), `${JSON.stringify(STYLE, null, 1)}\n`);
  console.log(
    `map assets: ${glyphs} glyphs in 256 ranges (${Math.round(bytes / 1024)} KiB), sprite 1x and 2x, style, in ${OUT}`,
  );
}

main();
