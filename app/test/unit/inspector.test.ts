// @vitest-environment happy-dom
import { describe, expect, it } from "vitest";
import type { JsonPatch, JsonSchema } from "../../src/api/types.ts";
import { applyPatch } from "../../src/core/jsonpatch.ts";
import { Units } from "../../src/core/units.ts";
import { buildForm, check, defaultFor } from "../../src/plugins/inspector/form.ts";

const schema: JsonSchema = {
  type: "object",
  required: ["text", "level"],
  properties: {
    text: { type: "string" },
    level: { type: "number", "x-unit": "m", minimum: 0 },
    grade: { type: ["number", "null"], "x-unit": "permille" },
    owner: { type: "string", enum: ["legacy", "model"] },
    tags: { type: "array", items: { type: "string" } },
    st: { type: "object", additionalProperties: { type: ["number", "null"], "x-unit": "m" } },
  },
};

function form(value: Record<string, unknown>, units = new Units()) {
  const ops: JsonPatch[] = [];
  const el = buildForm(schema, value, { units, onPatch: (p) => ops.push(p), base: value });
  document.body.replaceChildren(el);
  return { el, ops };
}

const input = (label: string) => document.querySelector(`[aria-label="${label}"]`) as HTMLInputElement;

describe("inspector form", () => {
  it("writes one JSON Patch op per edit, in metres whatever the display unit", () => {
    const value = { text: "a", level: 30.48, grade: null, owner: "legacy", tags: ["x"], st: { PA: 200 } };
    const units = new Units("ft");
    const { ops } = form(value, units);
    // The level shows in feet and a typed 110 ft is stored in metres.
    expect(input("level").value).toBe("100");
    input("level").value = "110";
    input("level").dispatchEvent(new Event("change"));
    expect(ops[0]?.[0]?.op).toBe("replace");
    expect(ops[0]?.[0]?.path).toBe("/data/level");
    expect(ops[0]?.[0]?.value as number).toBeCloseTo(33.528, 9);
    // A value below the minimum is refused with a message and no op.
    input("level").value = "-1";
    input("level").dispatchEvent(new Event("change"));
    expect(ops.length).toBe(1);
    // Enum as a select.
    const sel = input("owner") as unknown as HTMLSelectElement;
    sel.value = JSON.stringify("model");
    sel.dispatchEvent(new Event("change"));
    expect(ops[1]).toEqual([{ op: "replace", path: "/data/owner", value: "model" }]);
    // A null is a value: the row offers Set, which adds a default.
    const set = [...document.querySelectorAll("button")].find((b) => b.textContent === "Set");
    set?.click();
    expect(ops[2]).toEqual([{ op: "replace", path: "/data/grade", value: 0 }]);
    // Map entries edit by key; the key is escaped as a pointer token.
    input("PA").value = "201.5";
    input("PA").dispatchEvent(new Event("change"));
    expect(ops[3]?.[0]?.path).toBe("/data/st/PA");
    // Every op applies cleanly to the record body.
    let body = { data: value, geom: null };
    for (const p of ops) body = applyPatch(body, p);
    expect(body.data).toMatchObject({ owner: "model", grade: 0 });
  });

  it("draws [c, z] pairs as one row of two unit-aware inputs", () => {
    const pvi: JsonSchema = {
      type: "object",
      properties: {
        pvi: {
          type: "array",
          items: {
            type: "array",
            prefixItems: [
              { type: "number", "x-unit": "m", title: "c" },
              { type: "number", "x-unit": "m", title: "z" },
            ],
          },
        },
      },
    };
    const ops: JsonPatch[] = [];
    document.body.replaceChildren(
      buildForm(pvi, { pvi: [[357, 168.5]] }, { units: new Units(), onPatch: (p) => ops.push(p) }),
    );
    expect(input("pvi 1 c").value).toBe("357");
    input("pvi 1 z").value = "169";
    input("pvi 1 z").dispatchEvent(new Event("change"));
    expect(ops[0]).toEqual([{ op: "replace", path: "/data/pvi/0/1", value: 169 }]);
    // Adding an item adds a default pair at the end.
    [...document.querySelectorAll("button")].find((b) => b.textContent === "+ item")?.click();
    expect(ops[1]).toEqual([{ op: "add", path: "/data/pvi/-", value: [0, 0] }]);
  });

  it("checks values and makes defaults from the schema", () => {
    expect(check({ type: "integer" }, 1.5)).toBe("a whole number");
    expect(check({ type: ["number", "null"] }, null)).toBeNull();
    expect(check({ type: "number" }, null)).toBe("a value is required");
    expect(check({ type: "string", pattern: "^[a-z]+$" }, "A")).toMatch(/must match/);
    expect(defaultFor(schema)).toEqual({ text: "", level: 0 });
    expect(defaultFor({ type: "array", prefixItems: [{ type: "number" }, { type: "number" }] })).toEqual([0, 0]);
  });

  it("shows references and id keys by name, keeps every stored digit, and asks before removing many values", () => {
    // A section as the kind file writes it: route through a local $ref, scale a ratio, path a long list.
    const section: JsonSchema = {
      type: "object",
      required: ["name", "scale"],
      $defs: { id: { type: ["string", "null"], pattern: "^[0-7][0-9A-HJKMNP-TV-Z]{25}$" } },
      properties: {
        name: { type: "string" },
        route: { description: "The route this section belongs to.", $ref: "#/$defs/id" },
        scale: { type: "number", "x-unit": "ratio" },
        lon: { type: "number", "x-unit": "deg" },
        path: { type: "array", items: { type: "array", prefixItems: [{ type: "number", "x-unit": "m" }] } },
        st: { type: "object", additionalProperties: { type: ["number", "null"], "x-unit": "m" } },
        del: { type: "array", items: { type: "string" } },
      },
    };
    const ROUTE = "01DXF6DT00BGVCFV19RSHKD3VH";
    const PB = "01DXF6DT00ZFVP0VMY5AH612Y8";
    const PL = "01DXF6DT00PJFDTH9QH6NEQMFX";
    const names: Record<string, string> = { [ROUTE]: "Line 6", [PB]: "Bond Hill", [PL]: "Lytle Park" };
    const value = {
      name: "Line 6",
      route: ROUTE,
      scale: 0.99983821,
      lon: -84.4781079,
      path: Array.from({ length: 759 }, (_, i) => [i]),
      st: { [PB]: 162.7 },
      del: [PL],
    };
    const ops: JsonPatch[] = [];
    const asked: string[] = [];
    const opened: string[] = [];
    document.body.replaceChildren(
      buildForm(section, value, {
        units: new Units(),
        onPatch: (p) => ops.push(p),
        refs: [{ path: "/route", kind: "route" }],
        name: (_k, id) => names[id] ?? id,
        open: (k, id) => opened.push(`${k}:${id}`),
        confirm: (t) => {
          asked.push(t);
          return false;
        },
      }),
    );
    // usability-5 (6): the route is a picker showing "Line 6", with Open; no quoted ULID in a JSON box.
    const route = input("route") as unknown as HTMLSelectElement;
    expect(route.tagName).toBe("SELECT");
    expect(route.selectedOptions[0]?.textContent).toBe("Line 6");
    expect(document.querySelector("textarea")).toBeNull();
    [...document.querySelectorAll("button")].find((b) => b.textContent === "Open")?.click();
    expect(opened).toEqual([`route:${ROUTE}`]);
    // usability-5 (7): a platform-keyed level is labelled by the platform's name; a platform id value shows its name.
    expect(input("Bond Hill").value).toBe("162.7");
    expect(document.body.textContent).toContain("Lytle Park");
    // usability-11: the stored digits, not three decimals.
    expect(input("scale").value).toBe("0.99983821");
    expect(input("lon").value).toBe("-84.4781079");
    // usability-17: 759 path points are folded, so no point has a remove button until asked for.
    expect(document.body.textContent).toContain("Show the 759 items");
    expect([...document.querySelectorAll("button")].filter((b) => b.textContent === "−").length).toBe(1);
    // Removing the whole path asks first, naming the count; a "no" sends nothing.
    const removePath = [...document.querySelectorAll("fieldset")]
      .find((f) => f.querySelector("legend")?.textContent === "path (759)")
      ?.querySelector('button[title="Remove this field"]') as HTMLButtonElement;
    removePath.click();
    expect(asked).toEqual(["Remove path, all 759 items of it?"]);
    expect(ops).toEqual([]);
  });

  it("keeps a reference that may name several kinds (a param's scope) a plain field, never a picker of none", () => {
    // /meta sends param.yaml's ref {path: /scope/id, kind: [route, section]}: there is no one list to pick from.
    const param: JsonSchema = {
      type: "object",
      properties: {
        scope: { type: "object", properties: { kind: { type: "string" }, id: { type: "string" } } },
      },
    };
    const asked: string[] = [];
    document.body.replaceChildren(
      buildForm(
        param,
        { scope: { kind: "section", id: "01DXF6DT00BGVCFV19RSHKD3VH" } },
        {
          units: new Units(),
          onPatch: () => {},
          refs: [{ path: "/scope/id", kind: ["route", "section"] }],
          choices: async (k) => {
            asked.push(k);
            return [];
          },
        },
      ),
    );
    const id = input("id");
    expect(id.tagName).toBe("INPUT");
    expect(id.value).toBe("01DXF6DT00BGVCFV19RSHKD3VH");
    expect(asked).toEqual([]);
  });
});
