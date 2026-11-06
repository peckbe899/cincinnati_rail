const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1300, height: 950 } });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('http://localhost:8799/index.html?debug&x=1#712400,4334000,0.18'); await p.waitForTimeout(4000);
  await p.screenshot({ path: 's_d5.png' });
  // click the middle of the fan on the canvas
  const box = await p.locator('canvas').first().boundingBox();
  const pt = await p.evaluate(() => { const S = window.__S; const v = S.view; const r = document.querySelector('canvas').getBoundingClientRect(); return [r.width / 2 + (712420 - v.cx) * v.s, r.height / 2 - (4334300 - v.cy) * v.s]; });
  await p.mouse.click(box.x + pt[0], box.y + pt[1]); await p.waitForTimeout(800);
  await p.screenshot({ path: 's_d5sel.png' });
  console.log(await p.evaluate(() => window.__S.sel && window.__S.sel.f.properties.name), JSON.stringify(errs));
  await b.close();
})();
