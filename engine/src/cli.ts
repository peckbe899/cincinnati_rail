// The one-shot CLI: node engine/src/cli.ts <method> <input.json | -> (engine/PROTOCOL.md).
//
// It reads the input (a file, or stdin for "-"), makes one call, writes one reply line to stdout (the sidecar's
// reply shape with "id": 0) and exits 0 when the reply is ok and 1 otherwise. A usage error also writes a
// bad_request reply, and exits 2.

import { readFileSync } from "node:fs";
import { engineBuild } from "./build.ts";
import { errorReply, handle, line, type Reply } from "./host.ts";
import { EngineFault } from "./index.ts";
import { ARGV_SKIP, EXIT_FAILED, EXIT_USAGE } from "./tol.ts";

const USAGE = "usage: node engine/src/cli.ts <method> <input.json | ->";

function finish(reply: Reply, code?: number): void {
  process.stdout.write(`${line(reply)}\n`);
  process.exitCode = code ?? (reply.ok ? 0 : EXIT_FAILED);
}

async function readStdin(): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) chunks.push(chunk as Buffer);
  return Buffer.concat(chunks).toString("utf8");
}

async function main(argv: string[]): Promise<void> {
  if (argv.length !== 2) {
    process.stderr.write(`${USAGE}\n`);
    finish(errorReply(0, new EngineFault("bad_request", USAGE)), EXIT_USAGE);
    return;
  }
  const [method, file] = argv as [string, string];
  let text: string;
  try {
    text = file === "-" ? await readStdin() : readFileSync(file, "utf8");
  } catch (e) {
    finish(errorReply(0, new EngineFault("bad_request", `cannot read ${file}: ${(e as Error).message}`)));
    return;
  }
  let params: unknown;
  try {
    params = JSON.parse(text.startsWith("\ufeff") ? text.slice(1) : text);
  } catch (e) {
    finish(errorReply(0, new EngineFault("bad_request", `${file} is not JSON: ${(e as Error).message}`)));
    return;
  }
  const request = line({ id: 1, method, params });
  const reply = await handle(request, { engineBuild: engineBuild(), emit: () => {}, replyId: 0 });
  finish(reply);
}

main(process.argv.slice(ARGV_SKIP)).catch((e: unknown) => {
  process.stderr.write(`engine cli failed: ${(e as Error)?.stack ?? String(e)}\n`);
  finish(errorReply(0, e));
});
