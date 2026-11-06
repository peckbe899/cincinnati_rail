const { chromium } = require('playwright');
const _path = require('path'), _repo = _path.resolve(__dirname, '..', '..', '..');   // data/sanborn (was the workspace root): configs/sanborn_paths.json
const _D = _path.resolve(_repo, JSON.parse(require('fs').readFileSync(_path.join(_repo, 'configs', 'sanborn_paths.json'), 'utf8')).workspace);
(async () => {
  const views = JSON.parse(process.argv[2]); const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1300, height: 950 } });
  const errs = []; p.on('pageerror', e => errs.push(String(e))); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  for (const [name, e, n, s, offs] of views) {
    await p.goto(`http://localhost:8799/index.html?debug&n=${name}#${e},${n},${s}`); await p.waitForTimeout(3500);
    for (const id of (offs || [])) { await p.click('#' + id); await p.waitForTimeout(200); }
    await p.waitForTimeout(1500); await p.screenshot({ path: _path.join(_D, 'yard', `s_${name}.png`) });
  }
  console.log(JSON.stringify(errs.slice(0, 10))); await b.close();
})();
