// Where the end-to-end tests find a hub, and how they start one (see playwright.config.ts).

export const E2E_PORT = Number(process.env.CRHUB_E2E_PORT ?? 8799);

/** The command that serves a fixture database on a port, as an argument list (run from the repo root). */
export function serveCommand(db: string, port: number): string[] {
  const raw = process.env.CRHUB_E2E_SERVE;
  const tpl: string[] = raw
    ? (JSON.parse(raw) as string[])
    : ["python", "-m", "region", "serve", "--db", "{db}", "--port", "{port}", "--no-browser"];
  return tpl.map((a) => a.replace("{db}", db).replace("{port}", String(port)));
}
