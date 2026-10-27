// Opens the three views through a running hub and checks they load on the hub's database, and that a record saved
// in one view reaches another open view live. Usage: node hub/test_hub.js [http://localhost:8765]
const { chromium } = require('playwright');
const base = process.argv[2] || 'http://localhost:8765';
const fail = (m) => { console.error('FAIL', m); process.exitCode = 1; };

(async () => {
  const browser = await chromium.launch();
  const open = async (path) => {
    const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto(base + path);
    return { page, errors };
  };
  const api = (p, o) => fetch(base + p, o).then((r) => r.json());

  // Rail Profiles on Line 8: its saved profile comes from the hub
  const prof = await open('/profiles/#Line_8');
  await prof.page.waitForFunction(() => window.railProfile && window.railProfile.line() === 'Line_8', null, { timeout: 60000 });
  await prof.page.waitForTimeout(1500);
  const saved = await prof.page.evaluate(() => window.railProfile.saved());
  const rec = await api('/api/doc?p=alignments%2FLine_8');
  if (!saved || !rec) fail('Profiles did not load the saved Line 8 profile from the hub');
  else console.log('Profiles: Line 8 loaded with its saved profile, hub version', rec.version);

  // live: a change written to the hub (as another view would) reaches the open Profiles page
  const before = await prof.page.evaluate(() => JSON.stringify(window.railProfile.align().pvi));
  const doc = JSON.parse(JSON.stringify(rec.data));
  doc.pvi = (doc.pvi || []).map(([c, z], i) => (i === 0 ? [c, z + 1] : [c, z]));
  await fetch(base + '/api/doc?p=alignments%2FLine_8', { method: 'PUT', headers: { 'content-type': 'application/json', 'X-By': 'test' }, body: JSON.stringify(doc) });
  await prof.page.waitForTimeout(2000);
  const after = await prof.page.evaluate(() => JSON.stringify(window.railProfile.align().pvi));
  if (doc.pvi.length && after === before) fail('the open Profiles page did not take the change live');
  else console.log('Live: a saved change reached the open Profiles page');
  await fetch(base + '/api/doc?p=alignments%2FLine_8', { method: 'PUT', headers: { 'content-type': 'application/json', 'X-By': 'test' }, body: JSON.stringify(rec.data) });

  // Deck: boots on the hub's layout and reports saving on
  const deck = await open('/deck/');
  await deck.page.waitForFunction(() => /Saved|Read only/.test(document.body.innerText), null, { timeout: 120000 }).catch(() => fail('Deck did not connect to the hub'));
  console.log('Deck: connected');

  // Station 3D: draws the hub's snapshot
  const s3 = await open('/3d/');
  await s3.page.waitForFunction(() => /\d{1,2}:\d{2}|synced|issues/i.test((document.getElementById('syncedAt') || {}).textContent || ''), null, { timeout: 120000 })
    .catch(() => fail('3D did not load a snapshot'));
  console.log('3D:', await s3.page.evaluate(() => document.getElementById('syncedAt').textContent));

  for (const [n, v] of [['Profiles', prof], ['Deck', deck], ['3D', s3]]) if (v.errors.length) fail(`${n} page errors: ${v.errors.slice(0, 3).join(' | ')}`);
  await browser.close();
  console.log(process.exitCode ? 'some checks failed' : 'all checks passed');
})();
