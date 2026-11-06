const { chromium } = require('playwright');
(async () => { const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }); const p = await b.newPage({ viewport: { width: 1200, height: 900 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  for (const [n, h] of [['wide', '#708000,4334000,0.12'], ['westwood', '#707000,4335000,0.6'], ['region', '#717000,4334000,0.035']]) {
    const t0 = Date.now(); await p.goto('http://localhost:8765/index.html?v=' + n + h); await p.waitForTimeout(9000);
    const t = await p.evaluate(async () => { const t1 = performance.now(); window.dispatchEvent(new Event('resize')); await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))); return performance.now() - t1; });
    await p.screenshot({ path: 'wh/p_' + n + '.png', clip: { x: 0, y: 60, width: 1150, height: 840 } }); console.log(n, 'frame ms', Math.round(t)); }
  console.log(errs.slice(0, 3)); await b.close(); })();
