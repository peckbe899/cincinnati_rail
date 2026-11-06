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
        b = await p.chromium.launch(); q = await b.new_page(viewport={"width": 1400, "height": 1000}); logs = []
        q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        q.on("console", lambda m: logs.append(f"{m.type}: {m.text}"[:300]) if m.type in ('error', 'warning') else None)
        await q.route("**/cdn.jsdelivr.net/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=JSTS))
        await q.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=""))
        await q.add_init_script("window.__D = " + DATA + ";\n" + SHIM)
        await q.goto("http://127.0.0.1:8765/index.html?debug&r=7#711874,4331153,1.6")
        async def settle(n=60, need=''):
            last = None
            for i in range(n):
                await q.wait_for_timeout(300); t = await q.inner_text('#plotNote')
                if t == last and t.endswith('.') and need in t: return t
                last = t
            return last
        print(await settle(need='redrawn'))
        R = await q.evaluate("(() => { const r = document.getElementById('cv').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
        X, Y = R[0] + R[2] / 2, R[1] + R[3] / 2
        await q.mouse.click(X, Y); await q.wait_for_timeout(500); print('1', (await q.inner_text('#selBody'))[:80].replace('\n', ' | '))
        await q.wait_for_timeout(450); await q.mouse.click(X, Y); await q.wait_for_timeout(500); print('2', (await q.inner_text('#selBody'))[:200].replace('\n', ' | '))
        await q.get_by_role('button', name='Re-divide', exact=True).click(); print(await settle())
        print('3', (await q.inner_text('#selBody'))[:300].replace('\n', ' | '))
        await q.screenshot(path=SP + 'plots/r_redo.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        print('\n'.join(logs[:20]) or 'no page errors'); await b.close()
asyncio.run(main())
