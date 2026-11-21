// A form generated from a kind's JSON Schema that writes JSON Patch (section 8: our own, because per-field patches
// and x-unit widgets fight a whole-form model). Each control edits one pointer: a change becomes one op, "replace"
// for a value that is there, "add" for one that is not, "remove" for an optional field cleared. Nulls are values
// (9.13): a nullable field shows a "null" state and a button to set it. Numbers with x-unit "m" show in the display
// unit and are stored in metres.

import type { JsonPatch, JsonSchema } from "../../api/types.ts";
import { escapeToken, getAt } from "../../core/jsonpatch.ts";
import type { Units } from "../../core/units.ts";

export interface FormOptions {
  units: Units;
  /** Called with the ops of one edit. */
  onPatch(ops: JsonPatch): void;
  /** The value the draft started from, to mark changed fields. */
  base?: unknown;
  /** Vocabularies for x-vocab, when /meta sends them. */
  vocab?: Record<string, string[]>;
  readOnly?: boolean;
}

type Json = unknown;

function types(s: JsonSchema): string[] {
  if (Array.isArray(s.type)) return s.type;
  if (typeof s.type === "string") return [s.type];
  if (s.properties) return ["object"];
  if (s.items || s.prefixItems) return ["array"];
  if (s.enum) return [...new Set(s.enum.map((v) => (v === null ? "null" : typeof v)))];
  return [];
}

const mainType = (s: JsonSchema) => types(s).find((t) => t !== "null") ?? "any";
const nullable = (s: JsonSchema) => types(s).includes("null");

/** A starting value for a new item or a field set from null. */
export function defaultFor(s: JsonSchema): Json {
  if (s.default !== undefined) return structuredClone(s.default);
  if (s.const !== undefined) return s.const;
  if (s.enum?.length) return s.enum[0];
  switch (mainType(s)) {
    case "object": {
      const o: Record<string, Json> = {};
      for (const k of s.required ?? []) {
        const p = s.properties?.[k];
        if (p) o[k] = nullable(p) ? null : defaultFor(p);
      }
      return o;
    }
    case "array":
      return s.prefixItems ? s.prefixItems.map(defaultFor) : [];
    case "number":
    case "integer":
      return typeof s.minimum === "number" && s.minimum > 0 ? s.minimum : 0;
    case "boolean":
      return false;
    case "string":
      return "";
    default:
      return null;
  }
}

/** The problems with a value against its schema node (one level: type, range, pattern, enum). */
export function check(s: JsonSchema, v: Json): string | null {
  if (v === null) return nullable(s) ? null : "a value is required";
  const t = mainType(s);
  if (t === "number" || t === "integer") {
    if (typeof v !== "number" || !Number.isFinite(v)) return "not a number";
    if (t === "integer" && !Number.isInteger(v)) return "a whole number";
    if (typeof s.minimum === "number" && v < s.minimum) return `at least ${s.minimum}`;
    if (typeof s.maximum === "number" && v > s.maximum) return `at most ${s.maximum}`;
    if (typeof s.exclusiveMinimum === "number" && v <= s.exclusiveMinimum) return `more than ${s.exclusiveMinimum}`;
    if (typeof s.exclusiveMaximum === "number" && v >= s.exclusiveMaximum) return `less than ${s.exclusiveMaximum}`;
  }
  if (t === "string" && typeof v === "string" && s.pattern && !new RegExp(s.pattern, "u").test(v))
    return `must match ${s.pattern}`;
  if (s.enum && !s.enum.some((e) => e === v)) return `one of ${s.enum.join(", ")}`;
  return null;
}

function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls?: string, text?: string): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function button(label: string, title: string, run: () => void, disabled = false): HTMLButtonElement {
  const b = el("button", "", label);
  b.type = "button";
  b.title = title;
  b.disabled = disabled;
  b.onclick = run;
  return b;
}

export class FormBuilder {
  private readonly o: FormOptions;
  constructor(o: FormOptions) {
    this.o = o;
  }

  /** The whole form for value (a record's data) at pointer root ("/data"). */
  build(schema: JsonSchema, value: Json, root = "/data"): HTMLElement {
    const form = el("div", "form");
    form.append(this.node(schema, value, root, schema.title ?? "data", true));
    return form;
  }

  private set(path: string, present: boolean, value: Json): void {
    this.o.onPatch([{ op: present ? "replace" : "add", path, value }]);
  }

  private dirty(path: string, value: Json): boolean {
    if (this.o.base === undefined) return false;
    const rel = path.replace(/^\/data/, "");
    return JSON.stringify(getAt(this.o.base, rel)) !== JSON.stringify(value);
  }

  private node(s: JsonSchema, v: Json, path: string, label: string, present: boolean, required = true): HTMLElement {
    const t = mainType(s);
    if (v === null && nullable(s)) return this.nullRow(s, path, label, present);
    if (v === undefined && !required) return this.absentRow(s, path, label);
    if (t === "object" && (s.properties || s.additionalProperties))
      return this.object(s, (v ?? {}) as Record<string, Json>, path, label, required);
    if (t === "array") return this.array(s, (Array.isArray(v) ? v : []) as Json[], path, label, required);
    return this.scalar(s, v, path, label, present, required);
  }

  private row(
    label: string,
    control: HTMLElement,
    unit: string,
    extra: HTMLElement[] = [],
    title?: string,
  ): HTMLElement {
    const r = el("div", "field");
    const l = el("label", "", label);
    if (title) l.title = title;
    const u = el("span", "unit", unit);
    r.append(l, control, u, ...extra);
    return r;
  }

  private nullRow(s: JsonSchema, path: string, label: string, present: boolean): HTMLElement {
    const span = el("span", "muted", "null");
    const set = button(
      "Set",
      "Give this field a value",
      () => this.set(path, present, defaultFor({ ...s, type: mainType(s) })),
      this.o.readOnly,
    );
    return this.row(label, span, "", [set], s.description);
  }

  private absentRow(s: JsonSchema, path: string, label: string): HTMLElement {
    const span = el("span", "muted", "not set");
    const add = button(
      "Add",
      "Add this field",
      () => this.set(path, false, nullable(s) ? null : defaultFor(s)),
      this.o.readOnly,
    );
    return this.row(label, span, "", [add], s.description);
  }

  private clearButtons(s: JsonSchema, path: string, required: boolean): HTMLElement[] {
    if (this.o.readOnly) return [];
    const out: HTMLElement[] = [];
    if (nullable(s)) out.push(button("∅", "Set to null", () => this.o.onPatch([{ op: "replace", path, value: null }])));
    if (!required) out.push(button("×", "Remove this field", () => this.o.onPatch([{ op: "remove", path }])));
    return out;
  }

  private scalar(
    s: JsonSchema,
    v: Json,
    path: string,
    label: string,
    present: boolean,
    required: boolean,
  ): HTMLElement {
    const t = mainType(s);
    const xunit = s["x-unit"];
    const units = this.o.units;
    const err = el("span", "error");
    let control: HTMLInputElement | HTMLSelectElement;
    const choices = s.enum ?? (s["x-vocab"] ? this.o.vocab?.[s["x-vocab"]] : undefined);
    const commit = (value: Json) => {
      const problem = check(s, value);
      err.textContent = problem ?? "";
      control.classList.toggle("bad", problem !== null);
      if (problem === null && JSON.stringify(value) !== JSON.stringify(v)) this.set(path, present, value);
    };
    if (s.const !== undefined) {
      const i = el("input");
      i.value = String(s.const);
      i.readOnly = true;
      return this.row(label, i, "", [], s.description);
    }
    if (choices) {
      const sel = el("select");
      for (const c of choices) {
        const o = el("option", "", String(c));
        o.value = JSON.stringify(c);
        o.selected = c === v;
        sel.append(o);
      }
      if (!choices.some((c) => c === v)) {
        const o = el("option", "", `${String(v)} (not in the list)`);
        o.selected = true;
        o.value = JSON.stringify(v);
        sel.prepend(o);
      }
      sel.onchange = () => commit(JSON.parse(sel.value));
      control = sel;
    } else if (t === "boolean") {
      const i = el("input");
      i.type = "checkbox";
      i.checked = v === true;
      i.onchange = () => commit(i.checked);
      control = i;
    } else if (t === "number" || t === "integer") {
      const i = el("input");
      i.inputMode = "decimal";
      i.value = typeof v === "number" ? units.format(v, xunit) : "";
      i.dataset.path = path;
      i.onchange = () => {
        const n = units.parse(i.value, xunit);
        if (n === null) {
          err.textContent = "not a number";
          i.classList.add("bad");
          return;
        }
        commit(t === "integer" ? Math.round(n) : n);
      };
      control = i;
    } else if (t === "string") {
      const i = el("input");
      i.value = typeof v === "string" ? v : "";
      i.onchange = () => commit(i.value);
      control = i;
    } else {
      return this.json(s, v, path, label, present);
    }
    control.disabled = !!this.o.readOnly;
    control.setAttribute("aria-label", label);
    if (this.dirty(path, v)) control.classList.add("dirty");
    return this.row(label, control, units.label(xunit), [...this.clearButtons(s, path, required), err], s.description);
  }

  /** A schema the form cannot map field by field (oneOf, anyOf, untyped) is edited as JSON. */
  private json(s: JsonSchema, v: Json, path: string, label: string, present: boolean): HTMLElement {
    const ta = el("textarea");
    ta.rows = 3;
    ta.value = JSON.stringify(v ?? null, null, 1);
    const err = el("span", "error");
    ta.onchange = () => {
      try {
        this.set(path, present, JSON.parse(ta.value));
        err.textContent = "";
      } catch {
        err.textContent = "not valid JSON";
      }
    };
    ta.disabled = !!this.o.readOnly;
    return this.row(label, ta, "", [err], s.description);
  }

  private object(s: JsonSchema, v: Record<string, Json>, path: string, label: string, required: boolean): HTMLElement {
    const fs = el("fieldset");
    const legend = el("legend", "", label);
    if (s.description) legend.title = s.description;
    fs.append(legend, ...this.clearButtons(s, path, required));
    const req = new Set(s.required ?? []);
    const known = new Set(Object.keys(s.properties ?? {}));
    for (const [k, ps] of Object.entries(s.properties ?? {})) {
      fs.append(this.node(ps, v[k], `${path}/${escapeToken(k)}`, ps.title ?? k, Object.hasOwn(v, k), req.has(k)));
    }
    const extra = s.additionalProperties;
    if (extra && typeof extra === "object") {
      for (const k of Object.keys(v).filter((x) => !known.has(x))) {
        fs.append(this.node(extra, v[k], `${path}/${escapeToken(k)}`, k, true, false));
      }
      if (!this.o.readOnly) {
        const key = el("input");
        key.placeholder = "new key";
        key.setAttribute("aria-label", `New key in ${label}`);
        const add = button("Add", "Add an entry", () => {
          const name = key.value.trim();
          if (name && !Object.hasOwn(v, name))
            this.set(`${path}/${escapeToken(name)}`, false, nullable(extra) ? null : defaultFor(extra));
        });
        fs.append(this.row("", key, "", [add]));
      }
    }
    return fs;
  }

  /** Whether a schema is a fixed tuple of scalars ([c, z]), drawn as one row. */
  private isScalarTuple(s: JsonSchema): boolean {
    return (
      !!s.prefixItems?.length &&
      s.prefixItems.every((p) => ["number", "integer", "string", "boolean"].includes(mainType(p)))
    );
  }

  private tupleRow(s: JsonSchema, v: Json[], path: string, label: string, extra: HTMLElement[] = []): HTMLElement {
    const r = el("div", "field");
    const box = el("div", "tuple");
    for (const [j, ps] of (s.prefixItems ?? []).entries()) {
      const cell = this.scalar(ps, v[j], `${path}/${j}`, `${label} ${ps.title ?? j}`, j < v.length, true);
      cell.querySelector("label")?.remove();
      cell.className = "tuple-cell";
      box.append(...cell.childNodes);
    }
    r.append(el("label", "", label), box, ...extra);
    return r;
  }

  private array(s: JsonSchema, v: Json[], path: string, label: string, required: boolean): HTMLElement {
    if (this.isScalarTuple(s)) return this.tupleRow(s, v, path, label, this.clearButtons(s, path, required));
    const fs = el("fieldset");
    fs.append(el("legend", "", `${label} (${v.length})`), ...this.clearButtons(s, path, required));
    const itemSchema = s.items ?? {};
    const minItems = s.minItems ?? 0;
    v.forEach((item, i) => {
      const p = `${path}/${i}`;
      const remove = this.o.readOnly
        ? []
        : [button("−", "Remove this item", () => this.o.onPatch([{ op: "remove", path: p }]), v.length <= minItems)];
      if (this.isScalarTuple(itemSchema) && Array.isArray(item)) {
        fs.append(this.tupleRow(itemSchema, item, p, `${label} ${i + 1}`, remove));
        return;
      }
      const inner = this.node(itemSchema, item, p, `${i + 1}`, true);
      inner.append(...remove);
      fs.append(inner);
    });
    if (!this.o.readOnly && (s.maxItems === undefined || v.length < s.maxItems)) {
      const item = defaultFor(itemSchema);
      fs.append(
        button("+ item", "Add an item at the end", () =>
          this.o.onPatch([{ op: "add", path: `${path}/-`, value: item }]),
        ),
      );
    }
    return fs;
  }
}

/** Build a form; a convenience over FormBuilder. */
export function buildForm(schema: JsonSchema, value: Json, o: FormOptions): HTMLElement {
  return new FormBuilder(o).build(schema, value);
}
