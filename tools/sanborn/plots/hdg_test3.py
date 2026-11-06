try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import asyncio
from playwright.async_api import async_playwright
SP = _ws.DATA
DATA = open(SP + 'plots/db_data_live.json').read(); JSTS = open(_ws.CODE + 'jslib/package/dist/jsts.min.js').read()
SHIM = open(_ws.CODE + 'plots/ptest.py').read().split('SHIM = """')[1].split('"""')[0]
JS1 = r"""() => { const S = window.__S, fn = window.__fn; const F = S.streetById.get('SB0720'); fn.select(F);
  [...document.querySelectorAll('#selBody button')].find(x => x.textContent === 'Copy heading').click();
  const B = S.streetById.get('SBW002'), e = S.edits.streets['SBW002'], v = (e && e.c) || B.geometry.coordinates;
  document.getElementById('tEdit').click(); fn.select(B); S.rng = { id: 'SBW002', n: v.length, a: 3, b: 4 }; fn.select(B); S.rng = { id: 'SBW002', n: v.length, a: 3, b: 4 };
  return { n: v.length, before: v.slice(2, 6) }; }"""
JS2 = r"""() => { const S = window.__S, fn = window.__fn, B = S.streetById.get('SBW002');
  const b = (a, c) => ((Math.atan2(c[0] - a[0], c[1] - a[1]) * 180 / Math.PI) + 360) % 180;
  const bt = [...document.querySelectorAll('#selBody .stop')].find(x => x.textContent.startsWith('Between two points'));
  const m = [...bt.querySelectorAll('button')].find(x => x.textContent.startsWith('Match ')); const txt = m.textContent; m.click();
  const v = S.edits.streets['SBW002'].c; return { txt, seg: b(v[3], v[4]), after: v.slice(2, 6) }; }"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); q = await b.new_page(viewport={"width": 1400, "height": 1000}); logs = []
        q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        await q.route("**/cdn.jsdelivr.net/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=JSTS))
        await q.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=""))
        await q.add_init_script("window.__D = " + DATA + ";\n" + SHIM)
        await q.goto("http://127.0.0.1:8765/index.html?debug#711700,4335200,1.4"); await q.wait_for_timeout(20000)
        print(await q.evaluate(JS1)); await q.evaluate("() => window.__fn.select(window.__S.streetById.get('SBW002'))")
        await q.evaluate("() => { const S = window.__S, e = S.edits.streets['SBW002'], v = (e && e.c) || S.streetById.get('SBW002').geometry.coordinates; S.rng = { id: 'SBW002', n: v.length, a: 3, b: 4 }; window.__fn.select(S.streetById.get('SBW002')); }")
        await q.evaluate("() => { const S = window.__S, e = S.edits.streets['SBW002'], v = (e && e.c) || S.streetById.get('SBW002').geometry.coordinates; S.rng = { id: 'SBW002', n: v.length, a: 3, b: 4 }; document.getElementById('tEdit').click(); }")
        await q.wait_for_timeout(500)
        print(await q.evaluate(JS2)); await q.wait_for_timeout(800)
        await q.screenshot(path=SP + 'plots/hdg3.png', clip={'x':1050,'y':100,'width':350,'height':900})
        print('\n'.join(logs) or 'no page errors'); await b.close()
asyncio.run(main())
