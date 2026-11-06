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
        await q.goto("http://127.0.0.1:8765/index.html?debug&r=6#714900,4332300,2")
        for i in range(60):
            await q.wait_for_timeout(300)
            if 'redrawn' in await q.inner_text('#plotNote'): break
        R = await q.evaluate("(() => { const r = document.getElementById('cv').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
        info = await q.evaluate("""(() => { const cut = __S.pl.plots.filter(p => /~[a-z]$/.test(p.properties.id)); const ext = __S.pl.plots.filter(p => p.adds && !/~/.test(p.properties.id));
          const joined = __S.pl.blockList.filter(f => f.properties.joined); const c = p => { const r = p.geometry.coordinates[0]; return [Math.round(r.reduce((a, q) => a + q[0], 0) / r.length), Math.round(r.reduce((a, q) => a + q[1], 0) / r.length)]; };
          return { ncut: cut.length, next: ext.length, cut: cut.slice(0, 6).map(p => [p.properties.id, c(p), Math.round(p.area)]), ext: ext.slice(0, 6).map(p => [p.properties.id, c(p), Math.round(p.area)]), joined: joined.map(f => [f.properties.id, f.properties.joined, f._bb.map(Math.round)]) }; })()""")
        print(json.dumps(info))
        views = json.loads(sys.argv[1]) if len(sys.argv) > 1 else []
        for nm, cx, cy, s, click in views:
            await q.evaluate(f"(() => {{ __S.view.cx = {cx}; __S.view.cy = {cy}; __S.view.s = {s}; window.dispatchEvent(new Event('resize')); }})()"); await q.wait_for_timeout(1500)
            if click:
                await q.mouse.click(R[0] + R[2] / 2, R[1] + R[3] / 2); await q.wait_for_timeout(400)
                for k in range(click - 1): await q.wait_for_timeout(500); await q.mouse.click(R[0] + R[2] / 2, R[1] + R[3] / 2); await q.wait_for_timeout(400)
                print(nm, (await q.inner_text('#selBody'))[:300].replace('\n', ' | '))
            await q.screenshot(path=SP + f'plots/f_{nm}.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        await b.close()
asyncio.run(main())
