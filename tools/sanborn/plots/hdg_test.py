try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import asyncio
from playwright.async_api import async_playwright
SP = _ws.DATA
DATA = open(SP + 'plots/db_data_live.json').read(); JSTS = open(_ws.CODE + 'jslib/package/dist/jsts.min.js').read()
SHIM = open(_ws.CODE + 'plots/ptest.py').read().split('SHIM = """')[1].split('"""')[0]
JS = r"""
() => {
  const { select, stLabel, streetCoords } = window.__fn, S = window.__S, r = {};
  const all = S.deck.features.filter(f => f.properties.layer === 'street');
  const fo = all.filter(f => /^Follett/.test(f.properties.name)), di = all.filter(f => /^Dirr/.test(f.properties.name));
  r.fo = fo.map(f => [f.properties.id, f.properties.name, streetCoords(f).length]); r.di = di.map(f => [f.properties.id, f.properties.name, streetCoords(f).length]);
  if (!fo.length || !di.length) return r;
  const b = (a, c) => ((Math.atan2(c[0] - a[0], c[1] - a[1]) * 180 / Math.PI) + 360) % 180;
  const F = fo[0], D = di[0]; const cf = streetCoords(F), cd0 = streetCoords(D);
  r.before = [b(cf[0], cf[cf.length - 1]), b(cd0[0], cd0[cd0.length - 1])];
  select(F); [...document.querySelectorAll('#selBody button')].find(x => x.textContent === 'Copy heading').click();
  select(D); const bt = [...document.querySelectorAll('#selBody button')].find(x => x.textContent.startsWith('Match ')); r.btn = bt && bt.textContent; bt.click();
  const cd = streetCoords(S.streetById.get(D.properties.id)); r.after = b(cd[0], cd[cd.length - 1]); r.pivotKept = [cd0[0], cd[0]];
  r.panel = document.querySelector('#selBody .stop') ? [...document.querySelectorAll('#selBody .stop')].map(x => x.textContent).find(t => t.startsWith('Heading')) : null;
  return r;
}
"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); q = await b.new_page(viewport={"width": 1400, "height": 1000}); logs = []
        q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        await q.route("**/cdn.jsdelivr.net/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=JSTS))
        await q.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=""))
        await q.add_init_script("window.__D = " + DATA + ";\n" + SHIM)
        await q.goto("http://127.0.0.1:8765/index.html?debug#712500,4337500,1.4"); await q.wait_for_timeout(20000)
        print(await q.evaluate(JS)); await q.wait_for_timeout(1500)
        await q.screenshot(path=SP + 'plots/hdg.png', clip={'x':1050,'y':100,'width':350,'height':900})
        print('\n'.join(logs) or 'no page errors'); await b.close()
asyncio.run(main())
