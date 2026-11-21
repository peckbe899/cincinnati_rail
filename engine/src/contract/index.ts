// Engine contract v0. Everything a caller of the engine needs to type its messages, in one import:
//   import { SectionInput, VerticalRail, CONTRACTS } from "@cr/engine/contract";

import type { z } from "zod";
import { Flag } from "./flags.ts";
import { Hello, Request, Response } from "./protocol.ts";
import { SectionInput } from "./section_input.ts";
import { VerticalRail } from "./vertical_rail.ts";

export * from "./common.ts";
export * from "./flags.ts";
export * from "./protocol.ts";
export * from "./section_input.ts";
export * from "./vertical_rail.ts";

/** The contract major folder these schemas belong to (schema/v0). */
export const SCHEMA_VERSION = "v0";

/** Every schema exported to schema/v0/<name>.json, by file name. */
export const SCHEMAS: Record<string, z.ZodType> = {
  section_input: SectionInput,
  vertical_rail: VerticalRail,
  flag: Flag,
  hello: Hello,
  request: Request,
  response: Response,
};
