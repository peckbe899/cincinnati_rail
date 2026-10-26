// Local render check: node test_page.js OUTDIR [snapshot.json]
// Serves page/index.html with a snapshot.json beside it (the page's no-database fallback) and three.js from cache/.
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const [outDir, snapFile = path.join(__dirname, 'cache/snapshot.json')] = process.argv.slice(2);
const three = path.join(__dirname, 'cache/t0.147.0/package');
(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  for (const scheme of ['light', 'dark']) {
    const ctx = await browser.newContext({ viewport: { width: 1400, height: 860 }, colorScheme: scheme });
    await ctx.route('**/*', (route) => {
      const u = new URL(route.request().url());
      if (u.hostname === 'cdn.jsdelivr.net') return route.fulfill({ path: path.join(three, u.pathname.replace('/npm/three@0.147.0/', '')), contentType: 'text/javascript' });
      if (u.hostname === 'page.local') {
        const f = u.pathname === '/snapshot.json' ? snapFile : path.join(__dirname, 'page/index.html');
        const body = u.pathname === '/snapshot.json' ? fs.readFileSync(f) : '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>' + fs.readFileSync(f, 'utf8') + '</body></html>';
        return route.fulfill({ body, contentType: u.pathname.endsWith('.json') ? 'application/json' : 'text/html' });
      }
      return route.abort();
    });
    const page = await ctx.newPage();
    const errs = []; page.on('pageerror', (e) => errs.push(e.message)); page.on('console', (m) => m.type() === 'error' && errs.push(m.text()));
    await page.goto('http://page.local/index.html');
    await page.waitForFunction(() => !document.getElementById('syncedAt').textContent.includes('loading'), null, { timeout: 120000 }); await page.waitForTimeout(3000);
    const presets = scheme === 'light' ? ['region', 'plan', 'republic', 'sw229', 'below'] : ['sw229'];
    for (const p of presets) {
      await page.$eval(`[data-p="${p}"]`, (b) => b.click()); await page.waitForTimeout(4000);
      await page.screenshot({ path: path.join(outDir, `${scheme}_${p}.png`), timeout: 120000 });
    }
    if (scheme === 'light') {
      await page.$eval('#level', (s) => { s.selectedIndex = 1; s.dispatchEvent(new Event('change')); }); await page.$eval('#cutNear', (c) => { c.checked = true; }); await page.waitForTimeout(4000);
      await page.screenshot({ path: path.join(outDir, 'light_level1_cut.png') });
      await page.$eval('#level', (s) => { s.selectedIndex = 0; s.dispatchEvent(new Event('change')); }); await page.$eval('#cutNear', (c) => { c.checked = false; });
      await page.$eval('#stSearch', (i) => { i.value = 'union terminal'; i.dispatchEvent(new Event('input')); });
      await page.$eval('#stList [data-st]', (b) => b.click()); await page.waitForTimeout(4000);
      await page.screenshot({ path: path.join(outDir, 'light_union_terminal.png') });
      await page.setViewportSize({ width: 400, height: 800 }); await page.waitForTimeout(3000);
      await page.screenshot({ path: path.join(outDir, 'phone.png') });
    }
    console.log(scheme, 'errors:', errs.length ? errs : 'none');
    await ctx.close();
  }
  await browser.close();
})();
