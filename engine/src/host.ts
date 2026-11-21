// The NDJSON host shared by the sidecar and the CLI (engine/PROTOCOL.md): one request line in, a reply line out,
// progress lines between. No Node imports here: the sidecar and the CLI own the streams.

import { Request } from "./contract/index.ts";
import { EngineFault, solve } from "./index.ts";
import { PROGRESS_STEP, STACK_LINES } from "./tol.ts";

type Id = number | null;

export interface Reply {
  id: Id;
  ok: boolean;
  result?: unknown;
  error?: { code: EngineFault["code"]; message: string; stack?: string; issues?: unknown[] };
}

/** One JSON line (no newline). Values JSON cannot hold become null, as JSON.stringify does. */
export const line = (msg: unknown): string => JSON.stringify(msg);

/** The error reply for a failure: protocol codes for EngineFault, internal (with the stack) for anything else. */
export function errorReply(id: Id, e: unknown): Reply {
  if (e instanceof EngineFault) {
    const error: NonNullable<Reply["error"]> = { code: e.code, message: e.message };
    if (e.issues !== undefined) error.issues = e.issues;
    return { id, ok: false, error };
  }
  const err = e instanceof Error ? e : new Error(String(e));
  const stack = (err.stack ?? "").split("\n").slice(0, STACK_LINES).join("\n");
  return { id, ok: false, error: { code: "internal", message: err.message, stack } };
}

/** The id of a request line that failed to parse, when one can be read: a positive integer, else null. */
function readableId(raw: unknown): Id {
  if (raw && typeof raw === "object" && "id" in raw) {
    const id = (raw as { id: unknown }).id;
    if (typeof id === "number" && Number.isInteger(id) && id > 0) return id;
  }
  return null;
}

/**
 * Handle one request line: parse it, call the method, and give every line to write back (progress lines, then the
 * reply). `replyId` replaces the request's id in the reply (the CLI answers with id 0).
 */
export async function handle(
  text: string,
  opts: { engineBuild: string; emit: (msg: unknown) => void; replyId?: number },
): Promise<Reply> {
  let raw: unknown;
  try {
    raw = JSON.parse(text);
  } catch (e) {
    return { id: null, ok: false, error: { code: "bad_request", message: `not JSON: ${(e as Error).message}` } };
  }
  const req = Request.safeParse(raw);
  if (!req.success) {
    return {
      id: opts.replyId ?? readableId(raw),
      ok: false,
      error: { code: "bad_request", message: "not a request: {id, method, params}", issues: req.error.issues },
    };
  }
  const id = opts.replyId ?? req.data.id;
  let last = -1;
  const progress = (f: number, stage: string): void => {
    if (!Number.isFinite(f)) return;
    const p = Math.max(0, Math.min(1, f));
    if (p - last < PROGRESS_STEP && p < 1) return;
    last = p;
    opts.emit({ id, progress: p, stage });
  };
  try {
    const result = await solve(req.data.method, req.data.params, { engineBuild: opts.engineBuild, progress });
    return { id, ok: true, result };
  } catch (e) {
    return errorReply(id, e);
  }
}
