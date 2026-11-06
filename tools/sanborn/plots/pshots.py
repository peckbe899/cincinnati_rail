try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import asyncio, json, sys, time
from playwright.async_api import async_playwright
SP = _ws.DATA
DATA = open(SP + 'plots/db_data.json').read()
JSTS = open(_ws.CODE + 'jslib/package/dist/jsts.min.js').read()
SHIM = open(_ws.CODE + 'plots/ptest.py').read().split('SHIM = """')[1].split('"""')[0]
VIEWS = json.loads(sys.argv[1])
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); logs = []
        q = await b.new_page(viewport={"width": 1400, "height": 1000})
        q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        q.on("console", lambda m: logs.append(f"{m.type}: {m.text}"[:300]) if m.type in ('error', 'warning') else None)
        await q.route("**/cdn.jsdelivr.net/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=JSTS))
        await q.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=""))
        await q.add_init_script("window.__D = " + DATA + ";\n" + SHIM)
        await q.goto("http://127.0.0.1:8765/index.html?r=2#713100,4331300,0.5")
        for i in range(60):
            await q.wait_for_timeout(500); t = await q.inner_text('#plotNote')
            if 'redrawn' in t: break
        for nm, cx, cy, s in VIEWS:
            await q.evaluate(f"location.hash = '#{cx},{cy},{s}'"); await q.reload(); 
            for i in range(60):
                await q.wait_for_timeout(500); t = await q.inner_text('#plotNote')
                if 'redrawn' in t: break
            await q.wait_for_timeout(1200)
            await q.screenshot(path=SP + f'plots/v_{nm}.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        print('\n'.join(logs[:30]) or 'no page errors'); await b.close()
asyncio.run(main())
