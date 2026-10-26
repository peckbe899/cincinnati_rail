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

async function open(browser, root, docs, url) {
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  await ctx.addInitScript(stubScript(docs));
  await ctx.route('http://editor.local/**', (route) => {
    const p = path.join(root, decodeURIComponent(new URL(route.request().url()).pathname.slice(1) || 'index.html'));
    if (!fs.existsSync(p)) return route.fulfill({ status: 404, body: '' });
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
  // job: [{ id, c0, c1 }], the chainage ranges to sample (from sync.py)
  for (const j of job.lines) {
    const { ctx, page } = await open(browser, path.join(cache, 'profiles'), pdocs, `http://editor.local/index.html#${j.id}`);
    await page.waitForFunction((id) => window.railProfile && window.railProfile.line() === id, j.id, { timeout: 60000 });
    await page.waitForTimeout(1000);   // the saved alignment arrives just after the line loads
    result.profiles[j.id] = await page.evaluate((j) => {
      const P = window.railProfile, samples = [];
      for (let c = j.c0; c <= j.c1 + 1e-9; c += 2) samples.push([+c.toFixed(1), +P.railAt(c).toFixed(3), P.typeAt(c)]);
      return { saved: P.saved(), align: P.align(), platforms: P.platforms(), samples };
    }, j);
    await ctx.close();
  }

  // Mill Creek Deck: its own GeoJSON export (the Export button), captured from the downloads stand-in
  if (job.deck) {
    const ddocs = {}; for (const [id, d] of Object.entries(readDocs(path.join(cache, 'db/deck_db/deck')))) ddocs['deck/' + id] = d;
    const { ctx, page } = await open(browser, path.join(cache, 'deck'), ddocs, 'http://editor.local/index.html?debug');
    await page.waitForFunction(() => window.__S && window.__S.sf && window.__S.edits && window.__S.ver > 0, null, { timeout: 120000 });
    await page.waitForTimeout(1500);
    await page.evaluate(() => document.getElementById('xGeo').click());
    await page.waitForFunction(() => window.__dl.length > 0, null, { timeout: 120000 });
    result.deck = JSON.parse(await page.evaluate(() => window.__dl[0].data));
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(out, JSON.stringify(result));
})();
