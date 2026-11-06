try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import asyncio
from playwright.async_api import async_playwright
SP = _ws.DATA
DATA = open(SP + 'plots/db_data_v46.json').read(); JSTS = open(_ws.CODE + 'jslib/package/dist/jsts.min.js').read()
SHIM = open(_ws.CODE + 'plots/ptest.py').read().split('SHIM = """')[1].split('"""')[0]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); q = await b.new_page(viewport={"width": 1400, "height": 1000}); logs = []
        q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        await q.route("**/cdn.jsdelivr.net/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=JSTS))
        await q.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=""))
        await q.add_init_script("window.__D = " + DATA + ";\n" + SHIM)
        await q.goto("http://127.0.0.1:8765/index.html?debug#712780,4331000,1.4"); await q.wait_for_timeout(7000)
        box = await q.locator('canvas').first.bounding_box()
        await q.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2); await q.wait_for_timeout(1200)
        await q.screenshot(path=SP + 'plots/v48_click.png')
        print('\n'.join(logs) or 'no page errors'); await b.close()
asyncio.run(main())
