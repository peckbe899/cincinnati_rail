try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import asyncio, json, sys, time
from playwright.async_api import async_playwright
SP = _ws.DATA
DATA = open(SP + 'plots/db_data.json').read()
JSTS = open(_ws.CODE + 'jslib/package/dist/jsts.min.js').read()
SHIM = open(_ws.CODE + 'plots/ptest.py').read().split('SHIM = """')[1].split('"""')[0]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); q = await b.new_page(viewport={"width": 1400, "height": 1000})
        await q.route("**/cdn.jsdelivr.net/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=JSTS))
        await q.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=""))
        await q.add_init_script("window.__D = " + DATA + ";\n" + SHIM)
        await q.goto("http://127.0.0.1:8765/index.html?debug&r=5#714900,4332300,2")
        for i in range(60):
            await q.wait_for_timeout(300)
            if 'redrawn' in await q.inner_text('#plotNote'): break
        for (cx, cy, s) in [(714900, 4332300, 2), (714500, 4331900, 0.9), (714500, 4331900, 0.5), (713500, 4332500, 0.2), (712300, 4334600, 1.0)]:
            ms = []
            for k in range(4):
                await q.evaluate(f"(() => {{ __S.view.cx = {cx} + {k}; __S.view.cy = {cy}; __S.view.s = {s}; window.dispatchEvent(new Event('resize')); }})()"); await q.wait_for_timeout(250)
                ms.append(round(await q.evaluate("__S.drawMs"), 1))
            print(cx, cy, s, ms)
        await b.close()
asyncio.run(main())
