try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import asyncio, json, sys
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
        await q.goto("http://127.0.0.1:8765/index.html?debug&r=11#714500,4330370,3")
        for i in range(60):
            await q.wait_for_timeout(300)
            if 'redrawn' in await q.inner_text('#plotNote'): break
        for nm, cx, cy, s in json.loads(sys.argv[1]):
            for plt in (True, False):
                await q.evaluate(f"(() => {{ __S.layers.plt = {str(plt).lower()}; __S.layers.lab = true; __S.layers.met = false; __S.layers.rer = false; __S.layers.trk = false; __S.op.blk = {0.55 if plt else 0}; __S.colorBy = 'type'; __S.view.cx = {cx}; __S.view.cy = {cy}; __S.view.s = {s}; window.dispatchEvent(new Event('resize')); }})()"); await q.wait_for_timeout(2500)
                await q.screenshot(path=SP + f'plots/c_{nm}_{"p" if plt else "s"}.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        await b.close()
asyncio.run(main())
