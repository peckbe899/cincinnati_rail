// Close views of the CUT and Norwood Central structures: node test_context.js OUTDIR [snapshot.json] [view,view]
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const [outDir, snapFile = path.join(__dirname, 'cache/snapshot.json'), only] = process.argv.slice(2);
const three = path.join(__dirname, 'cache/t0.147.0/package');
const snap = JSON.parse(fs.readFileSync(snapFile)); const E0 = snap.origin.E, N0 = snap.origin.N;
const VIEWS = [   // name, UTM E, N, rail level at the target, facing, angle, distance
  ['cut_west', 712600, 4331890, 150, 80, 12, 520], ['cut_north_viaduct', 712450, 4333600, 160, 40, 14, 700],
  ['cut_dive', 712760, 4332750, 152, 300, 28, 380], ['cut_south', 712900, 4331300, 150, 300, 20, 700],
  ['cut_below', 712780, 4331900, 140, 30, -15, 450], ['norwood', 720140, 4337981, 176, 30, 22, 600], ['norwood_trench', 719100, 4337700, 172, 70, 25, 650]];
(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 860 } });
  await ctx.route('**/*', (route) => {
    const u = new URL(route.request().url());
    if (u.hostname === 'cdn.jsdelivr.net') return route.fulfill({ path: path.join(three, u.pathname.replace('/npm/three@0.147.0/', '')), contentType: 'text/javascript' });
    if (u.hostname === 'page.local') {
      if (u.pathname === '/snapshot.json') return route.fulfill({ body: fs.readFileSync(snapFile), contentType: 'application/json' });
      return route.fulfill({ body: '<!doctype html><html><head><meta charset="utf-8"></head><body>' + fs.readFileSync(path.join(__dirname, 'page/index.html'), 'utf8') + '</body></html>', contentType: 'text/html' });
    }
    return route.abort();
  });
  const page = await ctx.newPage();
  const errs = []; page.on('pageerror', (e) => errs.push(e.message));
  await page.goto('http://page.local/index.html');
  await page.waitForFunction(() => !document.getElementById('syncedAt').textContent.includes('loading'), null, { timeout: 180000 }); await page.waitForTimeout(2000);
  await page.$eval('#others', (c) => { c.checked = false; c.dispatchEvent(new Event('input')); });
  await page.$eval('#stSearch', (i) => { i.value = 'union terminal'; i.dispatchEvent(new Event('input')); });
  await page.$eval('#stList [data-st]', (b) => b.click()); await page.waitForTimeout(2000);
  for (const [nm, E, N, z, face, el, dist] of VIEWS.filter((v) => !only || only.split(',').includes(v[0]))) {
    if (nm === 'norwood' || (nm === 'norwood_trench' && only === 'norwood_trench')) { await page.$eval('#stSearch', (i) => { i.value = 'norwood central'; i.dispatchEvent(new Event('input')); }); await page.$eval('#stList [data-st]', (b) => b.click()); await page.waitForTimeout(2000); }
    await page.evaluate(([x, y, z, face, el, dist]) => { const W = window.__station3d; W.lookFrom(face, el, dist, new W.camera.position.constructor(x, W.Yp(x, y, z), -y)); }, [E - E0, N - N0, z, face, el, dist]);
    await page.waitForTimeout(2500); await page.screenshot({ path: path.join(outDir, nm + '.png'), timeout: 120000 });
  }
  console.log('errors:', errs.length ? errs : 'none'); await browser.close();
})();
