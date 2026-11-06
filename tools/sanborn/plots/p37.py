try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import asyncio, json
from playwright.async_api import async_playwright
SP = _ws.DATA
DATA = open(SP + 'plots/db_data.json').read(); JSTS = open(_ws.CODE + 'jslib/package/dist/jsts.min.js').read()
SHIM = open(_ws.CODE + 'plots/ptest.py').read().split('SHIM = """')[1].split('"""')[0]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); logs = []
        q = await b.new_page(viewport={"width": 1400, "height": 1000})
        q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        await q.route("**/cdn.jsdelivr.net/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=JSTS))
        await q.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=""))
        await q.add_init_script("window.__D = " + DATA + ";\n" + SHIM)
        await q.goto("http://127.0.0.1:8765/index.html?debug&r=7#712900,4331870,1.6")
        for i in range(60):
            await q.wait_for_timeout(500)
            if 'redrawn' in await q.inner_text('#plotNote'): break
        async def click_world(X, Y):
            pt = await q.evaluate(f"(() => {{ const r = document.getElementById('cv').getBoundingClientRect(), v = __S.view; return [r.left + r.width / 2 + ({X} - v.cx) * v.s, r.top + r.height / 2 - ({Y} - v.cy) * v.s]; }})()")
            await q.mouse.click(pt[0], pt[1]); await q.wait_for_timeout(400)
            return (await q.inner_text('#selBody'))[:200].replace('\n', ' | ')
        for X, Y in ((712930, 4331935), (712890, 4331870), (712760, 4331875), (713040, 4331870), (712780, 4331700)):
            print(X, Y, '->', await click_world(X, Y))
        await q.screenshot(path=SP + 'plots/v_c37_on.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        for cb in ('lCR', 'lCP', 'lCA', 'lCL', 'lCC'):
            await q.click('#' + cb)
        await q.wait_for_timeout(600)
        await q.screenshot(path=SP + 'plots/v_c37_off.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        print('summary', (await q.inner_text('#trkSummary'))[-700:].replace('\n', ' | ') if await q.query_selector('#trkSummary') else '')
        print('\n'.join(logs) or 'no page errors'); await b.close()
asyncio.run(main())
