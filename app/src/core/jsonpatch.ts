// RFC 6902 JSON Patch: apply, and a diff that makes small patches. The store keeps nulls (no merge patch, 9.13), so
// a null here is a value like any other and only "remove" deletes a key. Paths are RFC 6901 pointers.

import type { JsonPatch, JsonPatchOp } from "../api/types.ts";

export class PatchError extends Error {
  readonly op: JsonPatchOp;
  constructor(message: string, op: JsonPatchOp) {
    super(message);
    this.op = op;
    this.name = "PatchError";
  }
}

export function escapeToken(t: string | number): string {
  return String(t).replace(/~/g, "~0").replace(/\//g, "~1");
}

export function pointer(...tokens: (string | number)[]): string {
  return tokens.map((t) => `/${escapeToken(t)}`).join("");
}

export function parsePointer(p: string): string[] {
  if (p === "") return [];
  if (!p.startsWith("/")) throw new Error(`${p} is not a JSON pointer`);
  return p
    .slice(1)
    .split("/")
    .map((t) => t.replace(/~1/g, "/").replace(/~0/g, "~"));
}

type Json = unknown;

export function clone<T>(v: T): T {
  return v === undefined ? v : (structuredClone(v) as T);
}

export function deepEqual(a: Json, b: Json): boolean {
  if (a === b) return true;
  if (typeof a !== typeof b || a === null || b === null || typeof a !== "object") return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  if (Array.isArray(a)) {
    const bb = b as Json[];
    return a.length === bb.length && a.every((v, i) => deepEqual(v, bb[i]));
  }
  const ao = a as Record<string, Json>;
  const bo = b as Record<string, Json>;
  const ak = Object.keys(ao);
  if (ak.length !== Object.keys(bo).length) return false;
  return ak.every((k) => Object.hasOwn(bo, k) && deepEqual(ao[k], bo[k]));
}

/** The value at a pointer, or undefined. */
export function getAt(doc: Json, path: string): Json {
  let cur: Json = doc;
  for (const t of parsePointer(path)) {
    if (cur === null || typeof cur !== "object") return undefined;
    cur = Array.isArray(cur) ? cur[Number(t)] : (cur as Record<string, Json>)[t];
  }
  return cur;
}

function parentOf(doc: Json, tokens: string[], op: JsonPatchOp): [Json, string] {
  let cur = doc;
  for (const t of tokens.slice(0, -1)) {
    if (cur === null || typeof cur !== "object") throw new PatchError(`no parent for ${op.path}`, op);
    cur = Array.isArray(cur) ? cur[Number(t)] : (cur as Record<string, Json>)[t];
  }
  if (cur === null || typeof cur !== "object") throw new PatchError(`no parent for ${op.path}`, op);
  return [cur, tokens[tokens.length - 1] as string];
}

function arrayIndex(arr: Json[], t: string, op: JsonPatchOp, forAdd: boolean): number {
  if (forAdd && t === "-") return arr.length;
  if (!/^(0|[1-9]\d*)$/.test(t)) throw new PatchError(`${t} is not an array index in ${op.path}`, op);
  const i = Number(t);
  if (i > arr.length || (!forAdd && i === arr.length))
    throw new PatchError(`index ${i} out of range in ${op.path}`, op);
  return i;
}

function addAt(doc: Json, path: string, value: Json, op: JsonPatchOp): Json {
  const tokens = parsePointer(path);
  if (tokens.length === 0) return value;
  const [parent, last] = parentOf(doc, tokens, op);
  if (Array.isArray(parent)) parent.splice(arrayIndex(parent, last, op, true), 0, value);
  else (parent as Record<string, Json>)[last] = value;
  return doc;
}

function removeAt(doc: Json, path: string, op: JsonPatchOp): [Json, Json] {
  const tokens = parsePointer(path);
  if (tokens.length === 0) throw new PatchError("cannot remove the whole document", op);
  const [parent, last] = parentOf(doc, tokens, op);
  if (Array.isArray(parent)) {
    const i = arrayIndex(parent, last, op, false);
    return [doc, parent.splice(i, 1)[0]];
  }
  const obj = parent as Record<string, Json>;
  if (!Object.hasOwn(obj, last)) throw new PatchError(`nothing at ${path}`, op);
  const old = obj[last];
  delete obj[last];
  return [doc, old];
}

/** Apply a patch to a copy of doc and return the copy. Throws PatchError; doc is never changed. */
export function applyPatch<T>(doc: T, patch: JsonPatch): T {
  let out: Json = clone(doc);
  for (const op of patch) {
    switch (op.op) {
      case "add":
        out = addAt(out, op.path, clone(op.value), op);
        break;
      case "remove":
        out = removeAt(out, op.path, op)[0];
        break;
      case "replace": {
        if (op.path !== "" && getAt(out, op.path) === undefined) throw new PatchError(`nothing at ${op.path}`, op);
        if (op.path === "") out = clone(op.value);
        else {
          out = removeAt(out, op.path, op)[0];
          out = addAt(out, op.path, clone(op.value), op);
        }
        break;
      }
      case "move": {
        if (op.from === undefined) throw new PatchError("move needs from", op);
        const [rest, v] = removeAt(out, op.from, op);
        out = addAt(rest, op.path, v, op);
        break;
      }
      case "copy": {
        if (op.from === undefined) throw new PatchError("copy needs from", op);
        out = addAt(out, op.path, clone(getAt(out, op.from)), op);
        break;
      }
      case "test":
        if (!deepEqual(getAt(out, op.path), op.value)) throw new PatchError(`test failed at ${op.path}`, op);
        break;
      default:
        throw new PatchError(`unknown op ${(op as JsonPatchOp).op}`, op);
    }
  }
  return out as T;
}

/**
 * A patch from a to b. Objects are compared key by key; arrays of the same length element by element, and
 * otherwise replaced whole (a profile's PVI list is short, so whole replacement is cheap and unambiguous).
 */
export function diff(a: Json, b: Json, base = ""): JsonPatch {
  if (deepEqual(a, b)) return [];
  const bothObjects =
    a !== null && b !== null && typeof a === "object" && typeof b === "object" && Array.isArray(a) === Array.isArray(b);
  if (!bothObjects) return [{ op: "replace", path: base, value: clone(b) }];
  if (Array.isArray(a)) {
    const bb = b as Json[];
    if (a.length !== bb.length) return [{ op: "replace", path: base, value: clone(b) }];
    return a.flatMap((v, i) => diff(v, bb[i], `${base}/${i}`));
  }
  const ao = a as Record<string, Json>;
  const bo = b as Record<string, Json>;
  const out: JsonPatch = [];
  for (const k of Object.keys(ao)) {
    const p = `${base}/${escapeToken(k)}`;
    if (!Object.hasOwn(bo, k)) out.push({ op: "remove", path: p });
    else out.push(...diff(ao[k], bo[k], p));
  }
  for (const k of Object.keys(bo)) {
    if (!Object.hasOwn(ao, k)) out.push({ op: "add", path: `${base}/${escapeToken(k)}`, value: clone(bo[k]) });
  }
  return out;
}
