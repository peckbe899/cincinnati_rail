// The NDJSON messages between Python and a sidecar (engine/PROTOCOL.md).

import { z } from "zod";
import { Sha256 } from "./common.ts";

/** A method name: "vertical.rail". */
export const MethodName = z.string().regex(/^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$/);

/** A method with its version: "vertical.rail@1". The version rises whenever outputs change meaning. */
export const MethodRef = z.string().regex(/^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+@[1-9][0-9]*$/);

/** A request id: a positive integer, unique among the requests open on one connection. */
export const RequestId = z.int().positive();

export const Hello = z
  .strictObject({
    hello: z.strictObject({
      engine_version: z.string().min(1).meta({ description: "The version in engine/package.json." }),
      engine_build: Sha256.meta({ description: "sha256 of engine/src/** and engine/package.json." }),
      contracts: z
        .record(z.string(), z.int().nonnegative())
        .meta({ description: "Contract name to major: {section_input: 0, vertical_rail: 0}." }),
      methods: z.array(MethodRef),
    }),
  })
  .meta({ title: "Hello", description: "The first line a sidecar writes." });
export type Hello = z.infer<typeof Hello>;

export const Request = z
  .strictObject({
    id: RequestId,
    method: z.union([MethodName, MethodRef]).meta({ description: "A bare name takes the version the hello lists." }),
    params: z.unknown().meta({ description: "The method's input contract (SectionInput for vertical.rail)." }),
  })
  .meta({ title: "Request", description: "One call, written by Python to the sidecar's stdin." });
export type Request = z.infer<typeof Request>;

export const Progress = z
  .strictObject({
    id: RequestId,
    progress: z.number().min(0).max(1).meta({ "x-unit": "ratio" }),
    stage: z.string(),
  })
  .meta({ title: "Progress", description: "Optional progress of an open request." });
export type Progress = z.infer<typeof Progress>;

export const ReplyOk = z
  .strictObject({
    id: z.int().nonnegative(),
    ok: z.literal(true),
    result: z.unknown().meta({ description: "The method's output contract (VerticalRail for vertical.rail)." }),
  })
  .meta({ title: "ReplyOk" });
export type ReplyOk = z.infer<typeof ReplyOk>;

export const ErrorCode = z.enum(["bad_request", "unknown_method", "invalid_input", "internal"]).meta({
  description:
    "bad_request: the line is not a request; unknown_method: no such method or version; invalid_input: params fail the input contract; internal: the method threw.",
});
export type ErrorCode = z.infer<typeof ErrorCode>;

export const ReplyError = z
  .strictObject({
    id: z.int().nonnegative().nullable().meta({ description: "null when the request line could not be read." }),
    ok: z.literal(false),
    error: z.strictObject({
      code: ErrorCode,
      message: z.string(),
      stack: z.string().optional(),
      issues: z.array(z.unknown()).optional().meta({ description: "zod issues, for invalid_input." }),
    }),
  })
  .meta({ title: "ReplyError" });
export type ReplyError = z.infer<typeof ReplyError>;

export const Response = z
  .union([Progress, ReplyOk, ReplyError])
  .meta({ title: "Response", description: "Any line a sidecar writes after its hello." });
export type Response = z.infer<typeof Response>;
