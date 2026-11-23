// The old page's proposers on the seed, for engine/test/port/propose.test.ts: Lower and Raise on every issue that
// offers them (regradeDrive), Fix unbuildable, Solve levels with crossings, Reset this line and the paint review,
// each from the line as loaded and each put back at once (the page's state restored, its dirty flag cleared before
// its autosave can run). Written as engine/test/golden/old_page/proposers/<Line>.json.
//
// Drives the same SCRATCH copy of the old hub as old_page_dump.mjs (README.md in the golden folder): its patched
// profiles.html hands the page's functions to the harness as window.__P. Never run it against the old hub in the
// repository.
//
//   node engine/scripts/old_page_proposers.mjs --url http://localhost:8791/profiles/ --out engine/test/golden/old_page/proposers

import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, all) => {
    if (a.startsWith("--")) acc.push([a.slice(2), all[i + 1] && !all[i + 1].startsWith("--") ? all[i + 1] : true]);
    return acc;
  }, []),
);
const URL_ = args.url || "http://localhost:8791/profiles/";
const OUT = args.out || "engine/test/golden/old_page/proposers";
const LINES = (
  typeof args.lines === "string"
    ? args.lines
    : "Line_1,Line_2,Line_2b,Line_3,Line_4,Line_5,Line_6,Line_7,Line_8,Line_9,Line_10,Line_11,Line_12,Line_13,Line_14,CVG_Express"
).split(",");

async function probe(id) {
  const P = window.__P;
  const S = P.S;
  await P.selectLine(id);
  const $ = (q) => document.querySelector(q);
  const keys = () => S.stations.map((_, i) => P.stKey(i));
  const snap = JSON.stringify(S.align);
  const restore = () => {
    S.align = JSON.parse(snap);
    S.stations = P.deriveStations(S.align.del || [], S.align.so || []);
    P.changed(false);
    S.dirty = false;
  };
  const r2 = (v) => (Number.isFinite(v) ? Math.round(v * 1000) / 1000 : null);
  const state = () => {
    const ks = keys();
    return {
      pvi: S.align.pvi.map((p) => [r2(p.c), r2(p.z)]),
      st: Object.fromEntries(ks.map((k, i) => [k, r2(S.align.st[i])])),
      sg: Object.fromEntries(ks.map((k, i) => [k, S.align.sg?.[i] || 0])),
      gnd: (S.align.gnd || []).map((L) => L.map((p) => [r2(p.c), r2(p.z)])),
    };
  };
  const plain = (t) =>
    String(t)
      .replace(/<[^>]+>/g, "")
      .replace(/&amp;/g, "&");
  const status = () => $("#statusText").textContent;
  const out = { line: id, before: state(), regrade: [], fix_all: null, solve_cross: null, reset: null, paints: [] };
  // Lower or Raise on every issue that offers it, each from the line as loaded
  const seen = new Set();
  for (const x of S.issues || []) {
    if (!x.fix) continue;
    const k = `${x.fix.c0}|${x.fix.c1}|${x.fix.mode}|${x.fix.t || ""}|${x.fix.why || ""}`;
    if (seen.has(k)) continue;
    seen.add(k);
    const lim = x.fix.why ? P.fitLim(x.fix.t, x.fix.why) : null;
    const msg = P.regradeDrive(x.fix.c0, x.fix.c1, x.fix.mode, lim);
    S.dirty = false;
    out.regrade.push({
      kind: x.kind,
      fix: { mode: x.fix.mode, c0: x.fix.c0, c1: x.fix.c1, t: x.fix.t ?? null, why: x.fix.why ?? null },
      msg: plain(msg),
      after: state(),
    });
    restore();
  }
  // the line's buttons
  const click = (sel) => {
    $(sel).click();
    S.dirty = false;
    const msg = status();
    const after = state();
    restore();
    return { msg, after };
  };
  out.fix_all = click("#fixAll");
  out.solve_cross = click("#solveCross");
  $("#resetLine").click();
  out.reset = click("#resetLine");
  // the paint review (its rows as the card writes them)
  const det = $("#paintDet");
  det.open = true;
  det.dispatchEvent(new Event("toggle"));
  out.paints = [...document.querySelectorAll("#paintList .paint-row")].map((r) => r.firstElementChild.textContent);
  det.open = false;
  return out;
}

const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  await page.goto(URL_);
  await page.waitForFunction(() => window.__P?.S.data, null, { timeout: 60000 });
  await page.waitForTimeout(1500);
  mkdirSync(OUT, { recursive: true });
  for (const id of LINES) {
    const t0 = Date.now();
    const out = await page.evaluate(probe, id);
    writeFileSync(join(OUT, `${id}.json`), `${JSON.stringify(out)}\n`);
    console.log(`${id}: ${out.regrade.length} regrades, ${out.paints.length} paints, ${Date.now() - t0} ms`);
  }
} finally {
  await browser.close();
}
