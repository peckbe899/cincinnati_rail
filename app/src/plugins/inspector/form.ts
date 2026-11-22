// A form generated from a kind's JSON Schema that writes JSON Patch (section 8: our own, because per-field patches
// and x-unit widgets fight a whole-form model). Each control edits one pointer: a change becomes one op, "replace"
// for a value that is there, "add" for one that is not, "remove" for an optional field cleared. Nulls are values
// (9.13): a nullable field shows a "null" state and a button to set it. Numbers with x-unit "m" show in the display
// unit and are stored in metres; every other number shows as stored (units.ts), so an edit never stores a rounded
// value.
//
// Ben's terms: a reference (the kind's refs, or a local $ref to an id) shows the record's name with a picker of the
// records of that kind and an Open button, never a quoted ULID; a key or a value that is a record id (a profile's
// st, sg, so, del and frame keys are platform ids) shows the record's name beside it. Removing a whole list or
// object asks first, naming how many items go, and a long list (a section's path) is folded until asked for.

import type { JsonPatch, JsonSchema } from "../../api/types.ts";
import { escapeToken, getAt } from "../../core/jsonpatch.ts";
import { ULID_RE } from "../../core/names.ts";
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
  /** The kind's references: a pointer in data ("/route", "/crossings/{star}/other") and the kind it names (or the
   * kinds it may name, as a param's scope: route or section). */
  refs?: { path: string; kind: string | string[] }[];
  /** A record's name by kind and id ("Line 6"); without a kind, any record's with that id. */
  name?(kind: string | null, id: string): string;
  /** The records a reference of a kind can name, for its picker. */
  choices?(kind: string): Promise<{ id: string; name: string }[]>;
  /** Show a record (the Open button of a reference). */
  open?(kind: string, id: string): void;
  /** Ask Ben to confirm a removal that takes many values at once (window.confirm by default). */
  confirm?(text: string): boolean;
}

/** A list longer than this is folded until Ben asks for its items. */
export const FOLD_ITEMS = 40;

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
  private defs: Record<string, JsonSchema> = {};
  /** Long lists Ben has unfolded in this form. */
  private readonly unfolded = new Set<string>();
  constructor(o: FormOptions) {
    this.o = o;
  }

  /** The whole form for value (a record's data) at pointer root ("/data"). */
  build(schema: JsonSchema, value: Json, root = "/data"): HTMLElement {
    this.defs = schema.$defs ?? {};
    const form = el("div", "form");
    form.append(this.node(schema, value, root, schema.title ?? "data", true));
    return form;
  }

  /** A schema node with a local $ref ("#/$defs/c") merged in; the node's own keys (its description) win. */
  private resolve(s: JsonSchema): JsonSchema {
    let out = s;
    for (let i = 0; i < 8 && typeof out.$ref === "string" && out.$ref.startsWith("#/$defs/"); i++) {
      const def = this.defs[out.$ref.slice("#/$defs/".length)];
      if (!def) break;
      const { $ref: _ref, ...own } = out;
      out = { ...def, ...own };
    }
    return out;
  }

  /** The kind a pointer of the form refers to, from the kind's refs ("/data/crossings/3/other" -> section). A ref
   * that may name one of several kinds (a param's scope) has no one list to pick from: it stays a plain field. */
  private refKind(path: string): string | null {
    const rel = path.replace(/^\/data/, "").replace(/\/\d+(?=\/|$)/g, "/*");
    const kind = this.o.refs?.find((r) => r.path === rel)?.kind;
    return typeof kind === "string" ? kind : null;
  }

  private nameOf(kind: string | null, id: string): string | null {
    const n = this.o.name?.(kind, id);
    return n && n !== id ? n : null;
  }

  private confirm(text: string): boolean {
    const ask = this.o.confirm ?? ((t: string) => globalThis.confirm?.(t) ?? false);
    return ask(text);
  }

  private set(path: string, present: boolean, value: Json): void {
    this.o.onPatch([{ op: present ? "replace" : "add", path, value }]);
  }

  private dirty(path: string, value: Json): boolean {
    if (this.o.base === undefined) return false;
    const rel = path.replace(/^\/data/, "");
    return JSON.stringify(getAt(this.o.base, rel)) !== JSON.stringify(value);
  }

  private node(raw: JsonSchema, v: Json, path: string, label: string, present: boolean, required = true): HTMLElement {
    const s = this.resolve(raw);
    const t = mainType(s);
    const rk = this.refKind(path);
    if (rk && (typeof v === "string" || v === null || v === undefined) && (t === "string" || t === "any"))
      if (v !== undefined || required) return this.ref(s, rk, (v ?? null) as string | null, path, label, present);
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

  private clearButtons(s: JsonSchema, path: string, required: boolean, v?: Json, label = "this field"): HTMLElement[] {
    if (this.o.readOnly) return [];
    const out: HTMLElement[] = [];
    // A list or an object holds many values: clearing or removing it asks first, saying how many go.
    const many = Array.isArray(v) ? v.length : v && typeof v === "object" ? Object.keys(v as object).length : 0;
    const what = Array.isArray(v) ? `${many} item${many === 1 ? "" : "s"}` : `${many} entr${many === 1 ? "y" : "ies"}`;
    const ok = (verb: string) => many <= 1 || this.confirm(`${verb} ${label}, all ${what} of it?`);
    if (nullable(s))
      out.push(button("∅", "Set to null", () => ok("Clear") && this.o.onPatch([{ op: "replace", path, value: null }])));
    if (!required)
      out.push(button("×", "Remove this field", () => ok("Remove") && this.o.onPatch([{ op: "remove", path }])));
    return out;
  }

  /** A reference: the record's name, a picker of the records of its kind, and Open. */
  private ref(
    s: JsonSchema,
    kind: string,
    v: string | null,
    path: string,
    label: string,
    present: boolean,
  ): HTMLElement {
    const sel = el("select");
    sel.setAttribute("aria-label", label);
    const option = (id: string | null, text: string) => {
      const o = el("option", "", text);
      o.value = JSON.stringify(id);
      return o;
    };
    const current = v === null ? "none" : (this.nameOf(kind, v) ?? `${kind} ${v.slice(-6)}`);
    sel.append(option(v, current));
    sel.value = JSON.stringify(v);
    sel.title = v === null ? `no ${kind}` : `${kind} ${v}`;
    let loaded = false;
    const load = async () => {
      if (loaded || !this.o.choices) return;
      loaded = true;
      const list = await this.o.choices(kind).catch(() => []);
      const keep = sel.value;
      sel.replaceChildren();
      if (nullable(s) || v === null) sel.append(option(null, "none"));
      if (v !== null && !list.some((c) => c.id === v)) sel.append(option(v, current));
      for (const c of [...list].sort((a, b) => a.name.localeCompare(b.name))) sel.append(option(c.id, c.name));
      sel.value = keep;
    };
    sel.addEventListener("focus", () => void load());
    sel.addEventListener("pointerdown", () => void load());
    sel.onchange = () => {
      const id = JSON.parse(sel.value) as string | null;
      if (id !== v) this.set(path, present, id);
    };
    sel.disabled = !!this.o.readOnly;
    if (this.dirty(path, v)) sel.classList.add("dirty");
    const open = button("Open", `Show this ${kind}`, () => v && this.o.open?.(kind, v), v === null || !this.o.open);
    return this.row(label, sel, "", [open], s.description);
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
    let hint: HTMLElement | null = null;
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
      const n = typeof v === "string" && ULID_RE.test(v) ? this.nameOf(null, v) : null;
      if (n) {
        i.title = v as string;
        hint = el("span", "muted ref-name", n);
      }
    } else {
      return this.json(s, v, path, label, present);
    }
    control.disabled = !!this.o.readOnly;
    control.setAttribute("aria-label", label);
    if (this.dirty(path, v)) control.classList.add("dirty");
    const extra = [...(hint ? [hint] : []), ...this.clearButtons(s, path, required), err];
    return this.row(label, control, units.label(xunit), extra, s.description);
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
    fs.append(legend, ...this.clearButtons(s, path, required, v, label));
    const req = new Set(s.required ?? []);
    const known = new Set(Object.keys(s.properties ?? {}));
    for (const [k, ps] of Object.entries(s.properties ?? {})) {
      fs.append(this.node(ps, v[k], `${path}/${escapeToken(k)}`, ps.title ?? k, Object.hasOwn(v, k), req.has(k)));
    }
    const extra = s.additionalProperties;
    if (extra && typeof extra === "object") {
      for (const k of Object.keys(v).filter((x) => !known.has(x))) {
        // A key that is a record id (a profile's st keys are platform ids) is labelled by the record's name.
        const n = ULID_RE.test(k) ? this.nameOf(null, k) : null;
        const row = this.node(extra, v[k], `${path}/${escapeToken(k)}`, n ?? k, true, false);
        if (n) row.title = k;
        fs.append(row);
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
      s.prefixItems.every((p) => ["number", "integer", "string", "boolean"].includes(mainType(this.resolve(p))))
    );
  }

  private tupleRow(s: JsonSchema, v: Json[], path: string, label: string, extra: HTMLElement[] = []): HTMLElement {
    const r = el("div", "field");
    const box = el("div", "tuple");
    for (const [j, raw] of (s.prefixItems ?? []).entries()) {
      const ps = this.resolve(raw);
      const cell = this.scalar(ps, v[j], `${path}/${j}`, `${label} ${ps.title ?? j}`, j < v.length, true);
      cell.querySelector("label")?.remove();
      cell.className = "tuple-cell";
      box.append(...cell.childNodes);
    }
    r.append(el("label", "", label), box, ...extra);
    return r;
  }

  private array(s: JsonSchema, v: Json[], path: string, label: string, required: boolean): HTMLElement {
    if (this.isScalarTuple(s)) return this.tupleRow(s, v, path, label, this.clearButtons(s, path, required, v, label));
    const fs = el("fieldset");
    fs.append(el("legend", "", `${label} (${v.length})`), ...this.clearButtons(s, path, required, v, label));
    const itemSchema = this.resolve(s.items ?? {});
    const minItems = s.minItems ?? 0;
    // A long list (a section's 759 path points) is folded: one stray click must not remove a point unseen.
    if (v.length > FOLD_ITEMS && !this.unfolded.has(path)) {
      const more = button(`Show the ${v.length} items`, `List every item of ${label}`, () => {
        this.unfolded.add(path);
        fs.replaceWith(this.array(s, v, path, label, required));
      });
      fs.append(more);
      return fs;
    }
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
