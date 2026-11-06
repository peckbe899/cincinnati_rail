try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import asyncio
from playwright.async_api import async_playwright
SP = _ws.DATA
DATA = open(SP + 'plots/db_data.json').read(); JSTS = open(_ws.CODE + 'jslib/package/dist/jsts.min.js').read()
SHIM = open(_ws.CODE + 'plots/ptest.py').read().split('SHIM = """')[1].split('"""')[0]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); logs = []; q = await b.new_page(viewport={"width": 1400, "height": 1000})
        q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        await q.route("**/cdn.jsdelivr.net/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=JSTS))
        await q.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=""))
        await q.add_init_script("window.__D = " + DATA + ";\n" + SHIM)
        for X, Y, tag in ((712772, 4335354, 'fb'), (712684, 4333694, 'b25'), (712900, 4331630, 'j')):
            await q.goto(f"http://127.0.0.1:8765/index.html?debug&r={tag}#{X},{Y},0.9"); await q.wait_for_timeout(9000)
            r = await q.evaluate("(() => { const c = document.getElementById('cv').getBoundingClientRect(); return [c.left + c.width / 2, c.top + c.height / 2]; })()")
            await q.mouse.click(r[0], r[1]); await q.wait_for_timeout(700)
            print(tag, (await q.inner_text('#selBody'))[:300].replace('\n', ' | '))
            await q.screenshot(path=SP + f'plots/v_c43_{tag}.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        print('\n'.join(logs) or 'no page errors'); await b.close()
asyncio.run(main())
