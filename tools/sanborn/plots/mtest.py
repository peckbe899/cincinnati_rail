try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import asyncio, sys, json
from playwright.async_api import async_playwright
SP = _ws.DATA
DATA = open(SP + 'plots/db_now.json').read(); JSTS = open(_ws.CODE + 'jslib/package/dist/jsts.min.js').read()
SHIM = open(_ws.CODE + 'plots/ptest.py').read().split('SHIM = """')[1].split('"""')[0]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); q = await b.new_page(viewport={"width": 1400, "height": 1000}); logs = []
        q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        q.on("console", lambda m: logs.append(f"{m.type}: {m.text}"[:400]) if m.type in ('error', 'warning') else None)
        await q.route("**/cdn.jsdelivr.net/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=JSTS))
        await q.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=""))
        await q.add_init_script("window.__D = " + DATA + ";\n" + SHIM)
        await q.goto("http://127.0.0.1:8765/index.html?debug#" + sys.argv[1]); await q.wait_for_timeout(int(sys.argv[2]) if len(sys.argv) > 2 else 30000)
        r = await q.evaluate(sys.argv[3] if len(sys.argv) > 3 else "1")
        print(json.dumps(r)[:4000]); print('\n'.join(logs[:30]) or 'no page errors')
        await q.screenshot(path=SP + 'plots/m_0.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        await b.close()
asyncio.run(main())
