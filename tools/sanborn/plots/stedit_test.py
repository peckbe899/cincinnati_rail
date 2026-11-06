try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import asyncio
from playwright.async_api import async_playwright
SP = _ws.DATA
DATA = open(SP + 'plots/db_data_v91.json').read(); JSTS = open(_ws.CODE + 'jslib/package/dist/jsts.min.js').read()
SHIM = open(_ws.CODE + 'plots/ptest.py').read().split('SHIM = """')[1].split('"""')[0]
JS = r"""
() => {
  const { dupScan, streetRun, stName, stLabel, deleteStreets, select, feats, streetCoords, lenOf } = window.__fn; const r = {};
  const d = dupScan(); r.dups = d.length; r.sample = d.slice(0, 40).map(x => [stLabel(x.drop), x.drop.properties.id, x.keep.properties.id, Math.round(lenOf(streetCoords(x.drop))), Math.round(lenOf(streetCoords(x.keep)))]);
  const m1 = feats('street').filter(f => /^New street M1$/i.test(stName(f)));
  r.m1 = m1.length;
  if (m1.length) { const f = m1[0]; r.run = streetRun(f).length; select(f);
    const ni = document.getElementById('nIn'); ni.value = 'Test Avenue';
    const btns = [...document.querySelectorAll('#selBody button')].map(b => b.textContent); r.btns = btns.filter(t => /Rename|Delete/.test(t));
    const b2 = [...document.querySelectorAll('#selBody button')].find(b => b.textContent.startsWith('Rename the street')) || [...document.querySelectorAll('#selBody button')].find(b => b.textContent === 'Rename this piece');
    b2.click(); r.renamed = feats('street').filter(g => stName(g) === 'Test Avenue').length; r.head = document.querySelector('#selBody .sel-name').textContent;
    const nBefore = feats('street').length; deleteStreets([f]); r.deleted = nBefore - feats('street').length;
    r.tools = document.getElementById('stTools').textContent.slice(0, 200);
  }
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
        await q.goto("http://127.0.0.1:8765/index.html?debug#711950,4336200,1.4"); await q.wait_for_timeout(20000)
        print(await q.evaluate(JS)); await q.wait_for_timeout(3000)
        await q.screenshot(path=SP + 'plots/stedit.png')
        print('\n'.join(logs) or 'no page errors'); await b.close()
asyncio.run(main())
