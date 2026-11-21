// The map works offline (9.30): the style names only local URLs, every glyph range a label can ask for exists, the
// glyphs decode as MapLibre's PBF format, and the sprite's JSON and PNG agree.

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { FONT } from "../../src/plugins/map/layers.ts";

const MAP = fileURLToPath(new URL("../../public/map/", import.meta.url));

/** A minimal protobuf reader for the glyphs message (fields as MapLibre's glyphs.proto). */
function readGlyphs(buf: Uint8Array) {
  let pos = 0;
  const varint = () => {
    let v = 0;
    let shift = 0;
    for (;;) {
      const b = buf[pos++] as number;
      v += (b & 127) * 2 ** shift;
      if (b < 128) return v;
      shift += 7;
    }
  };
  const fields = (end: number, on: (tag: number, wire: number) => void) => {
    while (pos < end) {
      const key = varint();
      on(key >> 3, key & 7);
    }
  };
  const stacks: { name: string; range: string; glyphs: Record<string, number | Uint8Array>[] }[] = [];
  fields(buf.length, (tag) => {
    const len = varint();
    const end = pos + len;
    if (tag !== 1) {
      pos = end;
      return;
    }
    const st = { name: "", range: "", glyphs: [] as Record<string, number | Uint8Array>[] };
    fields(end, (t) => {
      if (t === 1 || t === 2) {
        const n = varint();
        const s = new TextDecoder().decode(buf.subarray(pos, pos + n));
        pos += n;
        if (t === 1) st.name = s;
        else st.range = s;
      } else if (t === 3) {
        const gEnd = varint() + pos;
        const g: Record<string, number | Uint8Array> = {};
        fields(gEnd, (k) => {
          if (k === 2) {
            const n = varint();
            g.bitmap = buf.subarray(pos, pos + n);
            pos += n;
          } else {
            const v = varint();
            const names = ["", "id", "", "width", "height", "left", "top", "advance"];
            g[names[k] as string] = k === 5 || k === 6 ? (v >>> 1) ^ -(v & 1) : v;
          }
        });
        st.glyphs.push(g);
      }
    });
    stacks.push(st);
  });
  return stacks;
}

describe("offline map assets", () => {
  it("style, glyphs and sprite are all local and well formed", () => {
    const style = JSON.parse(readFileSync(join(MAP, "style.json"), "utf-8"));
    expect(style.version).toBe(8);
    expect(style.glyphs).toBe("/map/glyphs/{fontstack}/{range}.pbf");
    expect(style.sprite).toBe("/map/sprite");
    expect(JSON.stringify(style)).not.toMatch(/https?:\/\//);

    // Every range from 0-255 to 65280-65535 exists for the font the layers use.
    for (let start = 0; start < 65536; start += 256) {
      expect(existsSync(join(MAP, "glyphs", FONT.join(","), `${start}-${start + 255}.pbf`))).toBe(true);
    }
    const [stack] = readGlyphs(new Uint8Array(readFileSync(join(MAP, "glyphs", "dejavu-sans", "0-255.pbf"))));
    expect(stack?.name).toBe("dejavu-sans");
    expect(stack?.range).toBe("0-255");
    const a = stack?.glyphs.find((g) => g.id === 65);
    expect(a).toBeDefined();
    const w = a?.width as number;
    const h = a?.height as number;
    expect(w).toBeGreaterThan(10);
    expect(h).toBeGreaterThan(14);
    const bm = a?.bitmap as Uint8Array;
    expect(bm.length).toBe((w + 6) * (h + 6));
    // The SDF edge value 192 is crossed inside the bitmap: both inside and outside pixels exist.
    expect(Math.max(...bm)).toBeGreaterThan(192);
    expect(Math.min(...bm)).toBeLessThan(100);
    // The space has an advance and no bitmap; per mille (U+2030) is in the punctuation range.
    expect(stack?.glyphs.find((g) => g.id === 32)?.bitmap).toBeUndefined();
    const [punct] = readGlyphs(new Uint8Array(readFileSync(join(MAP, "glyphs", "dejavu-sans", "8192-8447.pbf"))));
    expect(punct?.glyphs.some((g) => g.id === 0x2030)).toBe(true);

    for (const s of ["sprite", "sprite@2x"]) {
      const json = JSON.parse(readFileSync(join(MAP, `${s}.json`), "utf-8"));
      const png = readFileSync(join(MAP, `${s}.png`));
      expect(png.subarray(1, 4).toString("ascii")).toBe("PNG");
      const pw = png.readUInt32BE(16);
      const ph = png.readUInt32BE(20);
      for (const icon of ["station", "station-transfer", "portal", "selected"]) {
        const r = json[icon];
        expect(r.x + r.width).toBeLessThanOrEqual(pw);
        expect(r.y + r.height).toBeLessThanOrEqual(ph);
      }
    }
  });
});
