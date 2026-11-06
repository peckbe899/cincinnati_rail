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
        await q.goto("http://127.0.0.1:8765/index.html?debug&r=3#712900,4331860,1.3")
        for i in range(60):
            await q.wait_for_timeout(500)
            if 'redrawn' in await q.inner_text('#plotNote'): break
        print('note:', (await q.inner_text('#plotNote'))[:120])
        print('layer label:', await q.evaluate("document.getElementById('lPlt').parentElement.textContent"))
        # click the Dalton underpass, then the plaza, then a plot
        for nm, (x, y) in (('underpass', (712900 + 0, 0)),):
            pass
        async def click_world(X, Y):
            pt = await q.evaluate(f"(() => {{ const r = document.getElementById('cv').getBoundingClientRect(), v = __S.view; return [r.left + r.width / 2 + ({X} - v.cx) * v.s, r.top + r.height / 2 - ({Y} - v.cy) * v.s]; }})()")
            await q.mouse.click(pt[0], pt[1]); await q.wait_for_timeout(400)
            return (await q.inner_text('#selBody'))[:260].replace('\n', ' | ') if True else (await q.evaluate("document.body.innerText.slice(0, 300)"))
        for X, Y in ((713015.5, 4331860), (713060, 4331905), (713200, 4331850), (712700, 4331880)):
            print(X, Y, '->', await click_world(X, Y))
        await q.click('#zReg'); await q.wait_for_timeout(1500)
        print('view', await q.evaluate("JSON.stringify(__S.view)"))
        await q.screenshot(path=SP + 'plots/v_regbtn.png', clip={"x": 0, "y": 85, "width": 1060, "height": 915})
        print('\n'.join(logs) or 'no page errors'); await b.close()
asyncio.run(main())
