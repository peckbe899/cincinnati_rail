// Shared steps of the end-to-end tests: offline routing (9.30: every non-local request is aborted), console and
// 404 collection, and API helpers that find Line 6 and make a scenario layer of the test's own.

import { type APIRequestContext, test as base, expect, type Page } from "@playwright/test";

export const API = "/api/v1";
/** Endpoints whose 404 is an expected answer the app handles. */
export const EXPECTED_MISSES = [/\/api\/v1\/legacy\//, /\/api\/v1\/results\?/];
const LOCAL = new Set(["127.0.0.1", "localhost", "[::1]", "::1"]);

export interface Watch {
  consoleErrors: string[];
  failed: { url: string; status: number }[];
  aborted: string[];
}

/** Every test runs offline: a request to any host but this machine is aborted and recorded. */
export const test = base.extend<{ watch: Watch }>({
  watch: async ({ page }, use) => {
    const w: Watch = { consoleErrors: [], failed: [], aborted: [] };
    await page.route(
      (url) => !LOCAL.has(url.hostname) && url.protocol !== "data:" && url.protocol !== "blob:",
      (route) => {
        w.aborted.push(route.request().url());
        return route.abort("internetdisconnected");
      },
    );
    page.on("console", (m) => {
      if (m.type() !== "error") return;
      // Chromium logs every 4xx fetch as a console error. A 404 from an old-key lookup (Ctrl+K tries every legacy
      // kind) or from /results before a goal has one is an expected answer, not an error.
      if (m.text().startsWith("Failed to load resource") && EXPECTED_MISSES.some((re) => re.test(m.location().url)))
        return;
      w.consoleErrors.push(`${m.text()} (${m.location().url})`);
    });
    page.on("pageerror", (e) => w.consoleErrors.push(`pageerror: ${e.message}`));
    page.on("response", (r) => {
      if (r.status() >= 400) w.failed.push({ url: r.url(), status: r.status() });
    });
    await use(w);
  },
});

export { expect };

const json = async <T>(r: Awaited<ReturnType<APIRequestContext["get"]>>): Promise<T> => {
  expect(r.ok(), `${r.url()} answered ${r.status()}: ${await r.text()}`).toBeTruthy();
  return (await r.json()) as T;
};

const items = (r: unknown): Record<string, unknown>[] => {
  if (Array.isArray(r)) return r as Record<string, unknown>[];
  const o = r as Record<string, unknown>;
  for (const k of ["items", "records", "data"]) if (Array.isArray(o?.[k])) return o[k] as Record<string, unknown>[];
  return [];
};

/** The Line 6 section's id: through the legacy index, else by name. */
export async function line6Section(request: APIRequestContext): Promise<string> {
  for (const lkind of ["section", "route", "line"]) {
    const r = await request.get(`${API}/legacy/${lkind}/Line_6`);
    if (r.ok()) {
      const hit = (await r.json()) as { kind: string; id: string };
      if (hit.kind === "section") return hit.id;
      if (hit.kind === "route") {
        const s = items(await json(await request.get(`${API}/k/section?parent=${hit.id}`)));
        if (s[0]) return String(s[0].id);
      }
    }
  }
  for (const q of ["Line_6", "Line 6"]) {
    const s = items(await json(await request.get(`${API}/k/section?q=${encodeURIComponent(q)}`)));
    if (s[0]) return String(s[0].id);
  }
  throw new Error("Line 6's section is not in the fixture database");
}

/** The profile record of a section in a layer. */
export async function profileOf(
  request: APIRequestContext,
  sectionId: string,
  layer: string,
): Promise<Record<string, unknown>> {
  for (const f of [`parent=${sectionId}`, `ref=${sectionId}`]) {
    const p = items(await json(await request.get(`${API}/k/profile?${f}&layer=${encodeURIComponent(layer)}`)));
    if (p[0]) return p[0];
  }
  throw new Error(`no profile record for section ${sectionId}`);
}

export async function getRecord(
  request: APIRequestContext,
  kind: string,
  id: string,
  layer: string,
): Promise<Record<string, unknown>> {
  return json(await request.get(`${API}/k/${kind}/${id}?layer=${encodeURIComponent(layer)}`));
}

/** A scenario layer of this test's own under main, so tests never share versions. */
export async function scenario(request: APIRequestContext, name: string): Promise<string> {
  const slug = `e2e-${name}-${Date.now().toString(36)}`
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, "-")
    .slice(0, 60);
  const r = await request.post(`${API}/layers`, {
    data: { slug, tier: "scenario", parent: "main", title: slug },
    headers: { "X-CR-Client": "e2e", "Content-Type": "application/json" },
  });
  expect(r.ok(), `creating layer ${slug}: ${r.status()} ${await r.text()}`).toBeTruthy();
  return slug;
}

/** Open the design workspace on a selection, and wait for the shell. */
export async function openApp(page: Page, query: string): Promise<void> {
  await page.goto(`/w/design?${query}`);
  await expect(page.getByTestId("statusbar")).toBeVisible();
}

/** The line sheet's solve counter now, to pass to settled(). */
export async function solveRev(page: Page): Promise<number> {
  return Number((await page.getByTestId("solve-info").getAttribute("data-rev")) ?? 0);
}

/**
 * Wait until the line sheet has solved since rev and has no solve running or queued: the latest input is solved.
 * Returns that last solve's time in ms (the worker round trip as the page saw it).
 */
export async function settled(page: Page, rev: number): Promise<number> {
  const info = page.getByTestId("solve-info");
  await expect.poll(async () => Number((await info.getAttribute("data-rev")) ?? 0)).toBeGreaterThan(rev);
  await expect(info).toHaveAttribute("data-busy", "0");
  return Number(await info.getAttribute("data-ms"));
}

/** The level of the first PVI as the table shows it, in metres. */
export const firstPviLevel = (page: Page) => page.getByLabel("PVI 1 level");
