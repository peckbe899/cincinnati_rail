// Runs the two editors headless from their published files and saved records, and reads the
// geometry from their own code. Usage: node harness.js CACHE_DIR JOB.json OUT.json
// CACHE_DIR holds profiles/ and deck/ (published files) and db/ (saved records, one JSON per doc).
// The db stand-in only serves the saved records: writes are dropped, so the editors are never changed.
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');

const [cache, jobFile, out] = process.argv.slice(2);
const job = JSON.parse(fs.readFileSync(jobFile, 'utf8'));
const readDocs = (dir) => fs.existsSync(dir) ? Object.fromEntries(fs.readdirSync(dir).filter((f) => f.endsWith('.json'))
  .map((f) => [f.slice(0, -5), JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'))])) : {};

// window.claude stand-in: collections and docs from `docs` ({ 'coll/id': data }), read-only
function stubScript(docs) {
  return `(() => {
    const DOCS = ${JSON.stringify(docs)};
    const snapDoc = (p) => ({ id: p.split('/').pop(), exists: p in DOCS, data: () => DOCS[p] && JSON.parse(JSON.stringify(DOCS[p])), metadata: { hasPendingWrites: false } });
    const doc = (p) => ({ onSnapshot: (cb) => { setTimeout(() => cb(snapDoc(p)), 0); return () => {}; }, get: async () => snapDoc(p), set: async () => {}, update: async () => {}, delete: async () => {} });
    const collection = (c) => ({ onSnapshot: (cb) => { const docs = Object.keys(DOCS).filter((p) => p.slice(0, p.lastIndexOf('/')) === c).map(snapDoc);
      setTimeout(() => cb({ docs, metadata: { hasPendingWrites: false } }), 0); return () => {}; }, doc: (id) => doc(c + '/' + id) });
    window.__dl = [];
    const api = { db: { doc, collection }, user: { can: async () => false, me: async () => null },
      downloads: { save: async (o) => { window.__dl.push(o); } } };
    window.claude = { use: async (k) => api[k] || null };
  })();`;
}

// The Deck's internal functions, exposed at boot as design/platform_track/extract/deck_headless.py does, so its
// extract.js can read the platform and track design (trackPair, stopBands ...) through the page's own code
const DECK_EXPOSE = 'window.__D = { currentFeatures, transitFeatures, trackPair, stopRings, stopBands, stopType, stopOff, stopLive, '
  + 'stopFrame, stopEdit, stDeleted, liveLines, baseH, hAt, H0, EDGE, PW, TAPER, H_TUBE, H_BOX, SLIDE_M, geomOf, '
  + 'frameAt, projectOn, featLabel, utmToLL, CVX, chainOf, resampleLine, lineCoords };';
const JSTS_CDN = 'https://cdn.jsdelivr.net/npm/jsts@2.12.1/dist/jsts.min.js';
const DECK_EXTRACT = path.join(__dirname, '../../design/platform_track/extract/extract.js');

async function open(browser, root, docs, url, html = (h) => h) {
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  await ctx.addInitScript(stubScript(docs));
  await ctx.route('http://editor.local/**', (route) => {
    const rel = decodeURIComponent(new URL(route.request().url()).pathname.slice(1) || 'index.html');
    // repo files in place of published ones (job.overlay, from sync.py: lines re-pathed in the repo)
    const p = (root.endsWith('profiles') && (job.overlay || {})[rel]) || path.join(root, rel);
    if (p.endsWith('jsts.min.js')) return route.fulfill({ status: 200, body: fs.readFileSync(path.join(cache, 'jsts/package/dist/jsts.min.js')), contentType: 'application/javascript' });
    if (!fs.existsSync(p)) return route.fulfill({ status: 404, body: '' });
    if (p.endsWith('index.html')) return route.fulfill({ status: 200, body: html(fs.readFileSync(p, 'utf8')), contentType: 'text/html' });
    const type = p.endsWith('.html') ? 'text/html' : p.endsWith('.json') ? 'application/json' : 'application/octet-stream';
    route.fulfill({ status: 200, body: fs.readFileSync(p), contentType: type });
  });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => console.error('page error:', e.message));
  await page.goto(url);
  return { ctx, page };
}

(async () => {
  const browser = await chromium.launch();
  const result = { profiles: {}, deck: null };

  // Rail Profiles: one load per line (its line is picked from the hash); rail level and type every 2 m
  const pdocs = {}; for (const [id, d] of Object.entries(readDocs(path.join(cache, 'db/profiles_db/alignments')))) pdocs['alignments/' + id] = d;
  for (const [id, d] of Object.entries(readDocs(path.join(cache, 'db/profiles_db/config')))) pdocs['config/' + id] = d;
  // the shared records (hub: params/metro_structure), for both editors
  const params = {}; for (const [id, d] of Object.entries(readDocs(path.join(cache, 'db/params_db/params')))) params['params/' + id] = d;
  for (const [id, d] of Object.entries(readDocs(path.join(cache, 'db/params_db/chronology')))) params['chronology/' + id] = d;   // the Chronology record
  Object.assign(pdocs, params);
  // repo profiles for lines the editor has not saved (job.extra_docs, from sync.py)
  for (const [k, d] of Object.entries(job.extra_docs || {})) if (!(k in pdocs)) pdocs[k] = d;
  // saved profiles moved onto re-pathed lines (job.override_docs)
  Object.assign(pdocs, job.override_docs || {});
  // job: [{ id, c0, c1 }], the chainage ranges to sample (from sync.py)
  for (const j of job.lines) {
    const { ctx, page } = await open(browser, path.join(cache, 'profiles'), pdocs, `http://editor.local/index.html#${j.id}`);
    await page.waitForFunction((id) => window.railProfile && window.railProfile.line() === id, j.id, { timeout: 60000 });
    await page.waitForTimeout(1000);   // the saved alignment arrives just after the line loads
    result.profiles[j.id] = await page.evaluate((j) => {
      const P = window.railProfile, samples = [];
      const step = j.step || 2; for (let c = j.c0; c <= j.c1 + 1e-9; c += step) samples.push([+c.toFixed(1), +P.railAt(c).toFixed(3), P.typeAt(c)]);
      return { saved: P.saved(), align: P.align(), platforms: P.platforms(), approaches: P.approaches ? P.approaches() : [], samples };
    }, j);
    await ctx.close();
  }

  // Mill Creek Deck: its own GeoJSON export (the Export button), captured from the downloads stand-in
  if (job.deck) {
    const ddocs = { ...params }; for (const [id, d] of Object.entries(readDocs(path.join(cache, 'db/deck_db/deck')))) ddocs['deck/' + id] = d;
    const hook = (h) => {
      h = h.replace(`<script src="${JSTS_CDN}" async></script>`, '<script src="jsts.min.js"></script>');
      const n = h.replace(/indexLayers\(\); if \(\/\[\?&\]debug/, (m) => 'indexLayers(); ' + DECK_EXPOSE + m.slice('indexLayers();'.length));
      if (n === h) throw new Error('Deck boot hook not found: the page changed');
      return n;
    };
    const { ctx, page } = await open(browser, path.join(cache, 'deck'), ddocs, 'http://editor.local/index.html?debug', hook);
    // wait for the saved edits themselves (the page boots with empty edits; the layout arrives just after)
    const lay = ddocs['deck/layout'] || {};
    const want = ['transit', 'stations', 'streets', 'blocks'].map((k) => Object.keys(lay[k] || {}).length);
    await page.waitForFunction((want) => window.__D && window.__S && window.__S.sf && window.__S.edits && window.__S.ver > 0
      && ['transit', 'stations', 'streets', 'blocks'].every((k, i) => Object.keys(window.__S.edits[k] || {}).length === want[i]), want, { timeout: 120000 });
    await page.waitForTimeout(1500);
    await page.evaluate(() => document.getElementById('xGeo').click());
    await page.waitForFunction(() => window.__dl.length > 0, null, { timeout: 120000 });
    result.deck = JSON.parse(await page.evaluate(() => window.__dl[0].data));
    // platform and track design (stops, bands, track pairs) through platform_track's extract.js, run as is
    const ex = await page.evaluate(`(${fs.readFileSync(DECK_EXTRACT, 'utf8').trim()})()`);
    result.deck_design = { constants: ex.constants, meta: ex.meta, stations: ex.stations, lines: ex.lines, tracks: ex.all_tracks };
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(out, JSON.stringify(result));
})();
