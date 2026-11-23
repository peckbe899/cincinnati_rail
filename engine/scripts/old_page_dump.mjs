// The old page's golden dump: everything data/profile/profiles.html computes for each Metro line, written as
// engine/test/golden/old_page/<Line>.json.gz (format old_page/1, read by engine/test/golden/old_page/load.ts).
//
// It drives a SCRATCH copy of the old hub whose profiles.html (and only that copy) carries one added line,
// `window.__P = { ... }`, that hands the page's own functions and state to the harness. The page is never edited in
// the repository and nothing here writes to its database: every call is a read, except the proposeFill probe, which
// clears the dirty flag at once and puts the drawn ground back (see README.md in the output folder).
//
//   node engine/scripts/old_page_dump.mjs --url http://localhost:8791/profiles/ --out engine/test/golden/old_page
//   node engine/scripts/old_page_dump.mjs --lines Line_6,Line_2b --out /tmp/x --plain
//
// Needs Node 22 and the repository's Playwright (node_modules/playwright, with its Chromium). No other tool.

import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";
import { chromium } from "playwright";

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, all) => {
    if (a.startsWith("--")) acc.push([a.slice(2), all[i + 1] && !all[i + 1].startsWith("--") ? all[i + 1] : true]);
    return acc;
  }, []),
);
const URL_ = args.url || "http://localhost:8791/profiles/";
const OUT = args.out || "engine/test/golden/old_page";
const ONLY = typeof args.lines === "string" ? args.lines.split(",") : null;
const PLAIN = !!args.plain;

// ---------------------------------------------------------------------------------------------------------------
// --patch <copy of profiles.html>: write the harness line into a scratch copy of the page, then stop. Refuses any
// file inside this repository: the page itself is never edited.
const NAMES =
  `sampleGround groundAt groundAt0 groundDemAt regradeGround gnds parseGnd normGnd gndLevel crossGround drawnGround
rebuildGround surfaceAt0 riverAt surfaceAt bedOf bedAt groundIdx baseStations keyOf stKey deriveStations vertices design railAt
gradeAt chords overrideAt effOvr sttFromDoc chainLL buildCanon fixedLevel lockAt lockedStation applyLocks refAt bridgeOf
viaductSpansNow riverBridges sunkBox navigable alongShore riverBand madeBedAt riverTubes defaultMode modeOf canonAt inStation
stationAt applyMS chrPhaseOfYear chrSegments phaseAt metroTube twinOf tubeKeyAt tubeFormAt drivenTube straightUnder
gradeLimitAt gradeLimitOver sustainedGrade gradeSeverity eraOf structFor reqCover sgMaxFor phaseRules methodAt pointType
platKind minRadiusAt approachExtra approachLen absorbShort openTypes stretchTypes solveTypes autoType fitOf fitLim
paintMisfits misfitText typeAt proposeFill gndChecks defaultAlign surfacePvis reframeDoc alignFromDoc computeSummary radii
radiusAt curveAllowance allowanceAt curveGradeRangesNow pathXY fitRadius platformCurve pathTurns pieceAt drawingFlags
platformTurns designChecks sevOf lineReady allIssues otherRail kindAt boredGap needSep contextClearancesNow
crossingClearancesNow roadChecksNow stationStreet streetAtC roadsIn subwayStreet dHall boxTopOf hallDims chrStationYear
complexOf stationAccess hallAt inPlatform selectLine withLine changed ensureJunctionPvis regradeDrive pool tubeOfKey openTop
setOf isRer`.split(/\s+/);
const LETS =
  "settings MS CHR CHR_LINES ST_PLAT ST_CPLX ST_ACCESS APX_EXTRA CONTEXT RER_CANON RIVERS LINKS VERTS MODEL_V sys DEFAULTS".split(
    " ",
  );
const CONSTS =
  "S METRO_ST ERA CANON TYPES STT OPEN_CLEAR METRO_DEFAULTS RER_DEFAULTS SYS DRAW BOX_COVER SEP_GAP BED_DEPTH MIN_RUN SLIDE_M VIA_SPAN VIA_CLEAR RIVER_SPAN GIRDER_MAX CAR_LEN END_DOOR PLAT_R_ERR PLAT_R_WARN GND_W DECK_ON JTOL ACCESS".split(
    " ",
  );
if (args.patch) {
  const file = realpathSync(resolve(String(args.patch)));
  const repo = realpathSync(resolve(dirname(fileURLToPath(import.meta.url)), "../.."));
  if (!relative(repo, file).startsWith("..")) throw new Error(`refusing to patch ${file}: it is inside the repository`);
  const src = readFileSync(file, "utf8");
  const anchor = "window.__api = { layout:";
  if (src.split(anchor).length !== 2) throw new Error("the page's window.__api hook was not found once");
  if (src.includes("window.__P = {")) throw new Error("already patched");
  const getters = LETS.map((k) => `get ${k}() { return ${k}; },`).join(" ");
  const line = `window.__P = { ${CONSTS.join(", ")}, ${getters} ${NAMES.join(", ")} };   // golden harness (scratch copy only)\n`;
  writeFileSync(file, src.replace(anchor, line + anchor));
  console.log(`patched ${file}: ${NAMES.length} functions, ${LETS.length + CONSTS.length} tables and state`);
  process.exit(0);
}

// ---------------------------------------------------------------------------------------------------------------
// Runs in the page. Reads window.__P (the patched scratch copy) and returns one line's dump. Self-contained: the
// function is serialised by Playwright, so it may use nothing from this module.
async function dumpLine(id) {
  const P = window.__P;
  const S = P.S;
  await P.selectLine(id);
  if (!S.data || S.data.id !== id) throw new Error(`selectLine(${id}) did not load`);
  const step = S.step || 2;
  const L = S.L;
  const n = Math.floor(L / step) + 1;
  const cAt = (i) => Math.min(i * step, L);
  const r4 = (v) => (Number.isFinite(v) ? Math.round(v * 1e4) / 1e4 : v);
  const rle = (arr) => {
    const out = [];
    for (const v of arr) {
      const last = out[out.length - 1];
      if (last && last[0] === v) last[1]++;
      else out.push([v, 1]);
    }
    return out;
  };
  // runs where `b` differs from `a` (both 2 m arrays): [[i0, [values]]]; NaN equals NaN
  const diffRuns = (a, b) => {
    const out = [];
    let cur = null;
    for (let i = 0; i < b.length; i++) {
      const x = a[i];
      const y = b[i];
      const same = (Number.isNaN(x) && Number.isNaN(y)) || Math.abs(x - y) <= 5e-5;
      if (!same) {
        if (!cur) {
          cur = [i, []];
          out.push(cur);
        }
        cur[1].push(y);
      } else cur = null;
    }
    return out;
  };
  const plain = (t) =>
    String(t)
      .replace(/<[^>]+>/g, "")
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"');
  const keyOf = (s) => P.keyOf(s);

  // ---- the grid (2 m, c_i = min(i * step, L)) ----
  const rail = [],
    grade = [],
    type = [],
    tubeKey = [],
    phase = [],
    point = [],
    ovr = [],
    canon = [],
    lock = [],
    tf = [],
    stIdx = [],
    glim = [];
  const surface = [],
    bed = [],
    madeBed = [],
    struct = [],
    limTube = [],
    limBox = [];
  const UND = new Set(["shield", "deep", "cutcover"]);
  for (let i = 0; i < n; i++) {
    const c = cAt(i);
    const z = P.railAt(c);
    rail.push(r4(z));
    grade.push(r4(P.gradeAt(c)));
    type.push(P.typeAt(c, z));
    tubeKey.push(P.tubeKeyAt(c));
    phase.push(P.phaseAt(c));
    const q = P.pointType(c, z);
    point.push(q.t ? (q.stn ? `${q.t}*` : q.t) : `cls:${q.cls}`);
    ovr.push(P.overrideAt(c));
    const sec = P.canonAt(c);
    canon.push(sec ? sec.m : null);
    const lk = P.lockAt(c);
    lock.push(lk ? lk.name || `${lk.lo}..${lk.hi}` : null);
    tf.push(P.tubeFormAt(c));
    const st = P.stationAt(c);
    stIdx.push(st ? S.stations.indexOf(st) : null);
    const gl = P.gradeLimitAt(c);
    glim.push(`${gl.lim}|${gl.warn ?? ""}`);
    surface.push(P.surfaceAt(c));
    bed.push(P.bedAt(c));
    madeBed.push(P.madeBedAt(c, z));
    // the structure drawn at the rail (structFor of the type) and the legal band's two dashed limits (drawing 2525-2532)
    const sc = P.structFor(type[i], c);
    struct.push(`${sc.k}|${r4(sc.below)}|${r4(sc.top)}`);
    const under = UND.has(type[i]) && !P.riverAt(c);
    const sh = P.structFor("shield", c);
    limTube.push(under ? r4(P.groundAt(c) - sh.top - sh.od) : Number.NaN);
    limBox.push(under ? r4(P.groundAt(c) - P.phaseRules(c).ccMax) : Number.NaN);
  }
  // the DEM exactly: decimetres as the line file has them (the page holds dm / 10 in single precision)
  const dem = Array.from(S.groundDem || []);
  const demDm = dem.map((v) => (Number.isNaN(v) ? null : Math.round(v * 10)));
  const reg = Array.from(S.groundReg || []);
  const fin = Array.from(S.ground || []);
  const T = P.stretchTypes();

  // ---- issues: allIssues, each tied to the source list it came from (to carry c0 and c1) ----
  const sm = P.computeSummary();
  const issues = P.allIssues(sm);
  const src = [];
  const push = (name, list, cOf) => {
    list.forEach((x, k) => {
      src.push({ name, k, c: cOf(x) });
    });
  };
  push("summary.over", sm.over, (o) => (o.c0 + o.c1) / 2);
  push("summary.clashes", sm.clashes, (x) => x.c);
  push("summary.shallowTubes", sm.shallowTubes || [], (t) => t.c);
  push("roads", P.roadChecksNow(), (x) => x.c);
  const acc = [];
  if (!P.isRer() && P.MS) for (const s of S.stations) for (const f of P.stationAccess(s).flags) acc.push({ s, f });
  push("access", acc, (a) => a.s.c);
  push("summary.deepShallow", sm.deepShallow, (f) => f.c);
  push("summary.checks", sm.checks || [], (x) => x.c);
  push("ground", P.gndChecks(), (x) => x.c);
  push("solve.flags", T ? T.flags : [], (f) => (f.c0 + f.c1) / 2);
  const mis = P.paintMisfits();
  push("misfits", mis, (m) => (m.c0 + m.c1) / 2);
  push("solve.bad", T?.bad ? T.bad : [], (b) => (b.c0 + b.c1) / 2);
  const order = src
    .map((x, i) => [x, i])
    .sort((a, b) => a[0].c - b[0].c || a[1] - b[1])
    .map((p) => p[0]);
  const range = (s) => {
    const lists = {
      "summary.over": sm.over,
      "summary.shallowTubes": sm.shallowTubes || [],
      "solve.flags": T ? T.flags : [],
      misfits: mis,
      "solve.bad": T?.bad ? T.bad : [],
    };
    const l = lists[s.name];
    return l ? [l[s.k].c0, l[s.k].c1] : null;
  };
  const half = P.settings.platform / 2;
  const iss = issues.map((x, k) => {
    const s = order[k];
    let c0 = null,
      c1 = null,
      from = null;
    const STN = new Set(["Platform grade", "Platform curve", "Platform slide", "Access", "Canon"]);
    if (s) {
      const r = range(s);
      if (r) {
        c0 = r[0];
        c1 = r[1];
        from = "source";
      }
    }
    if (from == null && STN.has(x.kind)) {
      c0 = x.c - half;
      c1 = x.c + half;
      from = "platform";
    }
    if (from == null) {
      // the range in the text (designChecks keeps it only there): "from 1+145 to 1+205", whole metres
      const m = /(\d+)\+(\d{3}) to (\d+)\+(\d{3})/.exec(plain(x.text));
      if (m) {
        c0 = +m[1] * 1000 + +m[2];
        c1 = +m[3] * 1000 + +m[4];
        from = "text";
      }
    }
    if (from == null && x.kind === "Drainage") {
      // "for 412 m from 3+120": the chord, centred on c
      const m = /for (\d+) m from/.exec(plain(x.text));
      if (m) {
        c0 = x.c - +m[1] / 2;
        c1 = x.c + +m[1] / 2;
        from = "text";
      }
    }
    if (from == null) {
      c0 = x.c;
      c1 = x.c;
      from = "point";
    }
    return {
      kind: x.kind,
      sev: P.sevOf(x),
      c: x.c,
      c0,
      c1,
      range_from: from,
      src: s ? [s.name, s.k] : null,
      grp: x.grp ?? null,
      text: x.text,
      plain: plain(x.text),
      fix: x.fix ?? null,
      clear: x.clear ?? null,
      propose: x.propose ?? null,
    };
  });
  const srcOk = issues.length === order.length && iss.every((x, k) => Math.abs(x.c - order[k].c) < 1e-9);

  // ---- stations ----
  const stations = S.stations.map((s, i) => {
    const a = P.stationAccess(s);
    const pc = P.platformCurve(i);
    const ss = P.stationStreet(s);
    return {
      i,
      name: s.name,
      key: keyOf(s),
      idx: s.idx,
      point_c: s.c0,
      c: s.c,
      trunk: s.trunk ?? null,
      rail: S.align.st[i],
      sg: (S.align.sg || [])[i] || 0,
      so: (S.align.so || [])[i] || 0,
      stt: (S.align.stt || [])[i] || "",
      ref: P.refAt(i),
      ground: P.groundAt(s.c),
      surface: P.surfaceAt(s.c),
      type: P.typeAt(s.c, S.align.st[i]),
      role: T?.stRole ? (T.stRole[keyOf(s)] ?? null) : null,
      platDef: T?.platDef ? (T.platDef[keyOf(s)] ?? null) : null,
      platKind: P.platKind(s),
      phase: P.phaseAt(s.c),
      year: P.chrStationYear(id, s.name),
      sgMax: P.sgMaxFor(),
      access: {
        ...a,
        others: a.others,
        flags: a.flags.map((f) => ({ sev: f.sev, text: f.text, plain: plain(f.text) })),
      },
      curve: { ...pc, R: Number.isFinite(pc.R) ? pc.R : null },
      street: { text: ss.text, street: ss.street, roads: ss.roads },
    };
  });

  // ---- crossings with the neighbour each was read from ----
  const crossings = P.crossingClearancesNow().map((x) => {
    const source = !x.wid
      ? null
      : S.saved[x.wid]
        ? "saved"
        : S.defaultDocs[x.wid]
          ? "default"
          : S.metroRails[x.wid]
            ? "metro_rails"
            : null;
    return { ...x, source };
  });
  const blocks = S.ctx?.blocks || [];
  const context = P.contextClearancesNow().map((x) => ({ ...x, block: blocks.indexOf(x.block) }));
  const strip = (sm0) => ({
    ...sm0,
    clashes: sm0.clashes.map((x) => (x.block ? { ...x, block: blocks.indexOf(x.block) } : x)),
  });

  // ---- levels: the default levels (defaultAlign as alignFromDoc calls it), reframeDoc on the saved doc ----
  const saved = S.saved[id] || null;
  const defaultAlign = P.defaultAlign(null, [], S.align.stt);
  let reframe = null;
  if (saved) {
    const copy = JSON.parse(JSON.stringify(saved));
    const changed = P.reframeDoc(copy);
    reframe = {
      changed,
      ...(changed
        ? {
            length_m: copy.length_m,
            pvi: copy.pvi,
            ovr: copy.ovr,
            tf: copy.tf ?? null,
            shafts: copy.shafts ?? null,
            gnd: copy.gnd ?? null,
            so: copy.so,
          }
        : {}),
    };
  }

  const out = {
    format: "old_page/1",
    line: id,
    system: S.data.system,
    L,
    step,
    n,
    settings: { ...P.settings },
    era: P.ERA[id] ?? null,
    canon_record: P.CANON[id] ?? null,
    had_doc: !!saved,
    stations_file: S.data.stations.map((s, i) => ({ i, name: s.name, c: s.c0 ?? s.c, key: keyOf(s) })),
    align: S.align,
    stations,
    grid: {
      rail,
      grade,
      type: rle(type),
      tube_key: rle(tubeKey),
      phase: rle(phase),
      point: rle(point),
      ovr: rle(ovr),
      canon: rle(canon),
      lock: rle(lock),
      tf: rle(tf),
      station: rle(stIdx),
      grade_limit: rle(glim),
      struct: rle(struct),
      limit_tube: limTube,
      limit_box: limBox,
      solved: T
        ? {
            t: rle(T.t),
            z_matches_rail: T.z.every((v, i) => Math.abs(v - P.railAt(cAt(i))) < 1e-9),
            tube: rle(T.tube),
            part: rle(T.part),
          }
        : null,
      ground: {
        dem_dm: demDm,
        regraded: diffRuns(dem, reg),
        finished: diffRuns(reg, fin),
        surface: diffRuns(fin, surface),
        bed: diffRuns(fin, bed),
        made_bed: diffRuns(new Array(n).fill(Number.NaN), madeBed),
      },
    },
    ten: {
      radii: Array.from(P.radii(S.data), (v) => (Number.isFinite(v) ? v : null)),
      allowance: Array.from(P.curveAllowance(S.data)),
    },
    solve: T
      ? {
          bad: T.bad,
          platDef: T.platDef,
          stRole: T.stRole,
          shafts: T.shafts,
          flags: T.flags.map((f) => ({ ...f, plain: plain(f.text) })),
          approaches: T.approaches,
        }
      : null,
    eff_ovr: P.effOvr(),
    chr_segments: P.chrSegments(),
    canon: {
      secs: S.canonSecs,
      fixed: S.canonFixed,
      modes: S.canonModes,
      locks: S.canonLocks,
      piers: S.canonPiers || [],
      deck: S.canonDeck || [],
    },
    rivers: S.rivers.map((r) => ({
      ...r,
      bed: P.bedOf(r),
      navigable: P.navigable(r),
      along_shore: P.alongShore(r),
      bridge: P.bridgeOf(r),
      band: P.bridgeOf(r) ? null : P.riverBand(r),
    })),
    sunk_box: P.sunkBox(),
    river_bridges: P.riverBridges(),
    viaduct_spans: P.viaductSpansNow(),
    misfits: mis,
    crossings,
    context,
    roads: P.roadChecksNow(),
    gnd_cross: S.gndCross || [],
    gnd_checks: P.gndChecks(),
    drawing: P.drawingFlags(S.data),
    curve_grade: P.curveGradeRangesNow(),
    design: P.designChecks(),
    summary: strip(sm),
    issues: iss,
    issues_src_ok: srcOk,
    levels: { default_align: defaultAlign, reframe },
  };

  // ---- proposeFill on every issue that offers it (the drawn line it adds), each undone at once ----
  const proposals = [];
  const before = JSON.stringify(S.align.gnd || []);
  const seen = new Set();
  for (const x of iss) {
    if (!x.propose) continue;
    const k = `${x.propose.c0}|${x.propose.c1}`;
    if (seen.has(k)) continue;
    seen.add(k);
    const msg = P.proposeFill(x.propose.c0, x.propose.c1);
    S.dirty = false;
    const after = S.align.gnd || [];
    const old = new Set(JSON.parse(before).map((l) => JSON.stringify(l)));
    const added = after.filter((l) => !old.has(JSON.stringify(l)));
    proposals.push({ c0: x.propose.c0, c1: x.propose.c1, kind: x.kind, msg: plain(msg), added });
    S.align.gnd = JSON.parse(before);
    P.changed(false);
    S.dirty = false;
  }
  out.levels.propose_fill = proposals;
  // ---- Reset this line: alignFromDoc(null) (changes the page's state, so it runs last) ----
  out.levels.reset = P.alignFromDoc(null);
  return out;
}

// ---------------------------------------------------------------------------------------------------------------
const reviver = (_k, v) => {
  if (typeof v === "number" && !Number.isFinite(v)) return Number.isNaN(v) ? "__NaN__" : v > 0 ? "__Inf__" : "__-Inf__";
  if (ArrayBuffer.isView(v)) return Array.from(v);
  return v;
};

const browser = await chromium.launch();
try {
  const page = await (await browser.newContext({ viewport: { width: 1600, height: 1000 } })).newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(URL_);
  await page.waitForFunction(
    () => {
      const P = window.__P;
      return (
        P?.S.data &&
        P.MS &&
        P.CHR &&
        P.ST_PLAT &&
        P.ST_CPLX &&
        Object.keys(P.S.saved).length >= 40 &&
        document.querySelector("#statusText").textContent !== "Loading…"
      );
    },
    null,
    { timeout: 120000 },
  );
  await page.waitForTimeout(1500);
  const ids = await page.evaluate(() => window.__P.S.index.filter((l) => !l.id.startsWith("RER_")).map((l) => l.id));
  const want = ONLY || ids;
  // the page's text in a replacer that keeps NaN and Infinity, typed arrays as arrays
  await page.evaluate(`window.__dumpJSON = (v) => JSON.stringify(v, ${reviver.toString()})`);
  mkdirSync(OUT, { recursive: true });
  const sha = (t) => createHash("sha256").update(t).digest("hex");
  // what the dump was made from: the page as served less the harness line (equal to the repository's
  // data/profile/profiles.html when the copy is fresh), and the records the page read from the old hub
  const pageText = await page.evaluate(async (u) => (await fetch(u)).text(), URL_);
  const pageBody = pageText
    .replace('<script src="/hub/shim.js"></script>', "")
    .split("\n")
    .filter((l) => !l.startsWith("window.__P = {"))
    .join("\n");
  const inputs = await page.evaluate(() => {
    const P = window.__P;
    const sorted = (o) =>
      JSON.stringify(
        Object.keys(o)
          .sort()
          .map((k) => [k, o[k]]),
      );
    return {
      saved: sorted(P.S.saved),
      ms: JSON.stringify(P.MS),
      chr: JSON.stringify(P.CHR),
      plat: JSON.stringify(P.ST_PLAT),
      cplx: JSON.stringify(P.ST_CPLX),
      access: JSON.stringify(P.ST_ACCESS),
      apx: JSON.stringify(P.APX_EXTRA),
      context: JSON.stringify(P.CONTEXT),
      settings_metro: JSON.stringify(P.SYS.metro.settings),
    };
  });
  const sources = {
    page_sha256: sha(pageBody),
    harness_line: pageText.length !== pageBody.length,
    ...Object.fromEntries(Object.entries(inputs).map(([k, v]) => [`${k}_sha256`, sha(v)])),
    alignments: Object.keys(JSON.parse(inputs.saved)).length,
  };
  const index = [];
  for (const id of want) {
    const t0 = Date.now();
    const text = await page.evaluate(
      async ([fn, id]) => {
        const f = new Function(`return (${fn})`)();
        return window.__dumpJSON(await f(id));
      },
      [dumpLine.toString(), id],
    );
    const digest = sha(text);
    const file = join(OUT, PLAIN ? `${id}.json` : `${id}.json.gz`);
    writeFileSync(file, PLAIN ? text : gzipSync(Buffer.from(text), { level: 9 }));
    const obj = JSON.parse(text);
    index.push({
      line: id,
      file: file.split("/").pop(),
      json_sha256: digest,
      bytes: text.length,
      n: obj.n,
      issues: obj.issues.length,
      issues_src_ok: obj.issues_src_ok,
    });
    console.log(
      `${id}: n ${obj.n}, ${obj.issues.length} issues (sources ${obj.issues_src_ok ? "matched" : "NOT matched"}), ${(text.length / 1e6).toFixed(2)} MB, ${Date.now() - t0} ms`,
    );
  }
  if (errors.length) console.log("page errors:", errors);
  writeFileSync(
    join(OUT, "index.json"),
    `${JSON.stringify({ format: "old_page/1", sources, lines: index }, null, 2)}\n`,
  );
} finally {
  await browser.close();
}
