try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import asyncio
from playwright.async_api import async_playwright
SP = _ws.DATA
DATA = open(SP + 'plots/db_data.json').read(); JSTS = open(_ws.CODE + 'jslib/package/dist/jsts.min.js').read()
SHIM = open(_ws.CODE + 'plots/ptest.py').read().split('SHIM = """')[1].split('"""')[0]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); logs = []
        q = await b.new_page(viewport={"width": 1400, "height": 1000})
        q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        q.on("console", lambda m: logs.append(f"CONSOLE {m.type}: {m.text}") if m.type == 'error' else None)
        await q.route("**/cdn.jsdelivr.net/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=JSTS))
        await q.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=""))
        await q.add_init_script("window.__D = " + DATA + ";\n" + SHIM)
        await q.goto("http://127.0.0.1:8765/index.html?debug&r=12#712800,4331900,0.5")
        await q.wait_for_timeout(6000)
        await q.click('#zCvg'); await q.wait_for_timeout(1500)
        await q.screenshot(path=SP + 'plots/v_c41_cvg.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        async def goto(X, Y, s):
            await q.goto(f"http://127.0.0.1:8765/index.html?debug&r={X}#{X},{Y},{s}"); await q.wait_for_timeout(5000)
        async def click_world(X, Y):
            pt = await q.evaluate(f"(() => {{ const r = document.getElementById('cv').getBoundingClientRect(), v = __S.view; return [r.left + r.width / 2 + ({X} - v.cx) * v.s, r.top + r.height / 2 - ({Y} - v.cy) * v.s]; }})()")
            await q.mouse.click(pt[0], pt[1]); await q.wait_for_timeout(500)
            return (await q.inner_text('#selBody'))[:420].replace('\n', ' | ')
        await goto(702400, 4325600, 0.45)
        await q.screenshot(path=SP + 'plots/v_c41_term.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        for X, Y in ((702849 + 6, 4324980 + 3), (702044, 4326072 + 7)):
            print(X, Y, '->', await click_world(X, Y))
        await goto(705600, 4324600, 0.25)
        await q.screenshot(path=SP + 'plots/v_c41_east.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        await goto(712700, 4331500, 0.6)
        print('panel search:', (await q.evaluate("document.body.innerText.includes('stations T3, T2, T4, T1B, T1A')")))
        print('\n'.join(logs) or 'no page errors'); await b.close()
asyncio.run(main())
