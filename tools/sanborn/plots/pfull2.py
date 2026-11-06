try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import asyncio, json, sys, time
from playwright.async_api import async_playwright
SP = _ws.DATA
DATA = open(SP + 'plots/db_data.json').read()
JSTS = open(_ws.CODE + 'jslib/package/dist/jsts.min.js').read()
SHIM = open(_ws.CODE + 'plots/ptest.py').read().split('SHIM = """')[1].split('"""')[0].replace("if (n === 'user')", "if (n === 'downloads') return { save: async (o) => { window.__DL = (window.__DL || []).concat([[o.filename, (o.data.size || o.data.length)]]); } };\n  if (n === 'user')")
async def run(b, scheme, vw, vh, name):
    q = await b.new_page(viewport={"width": vw, "height": vh}, color_scheme=scheme); logs = []
    q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
    q.on("console", lambda m: logs.append(f"{m.type}: {m.text}"[:300]) if m.type in ('error', 'warning') else None)
    await q.route("**/cdn.jsdelivr.net/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=JSTS))
    await q.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=""))
    await q.add_init_script("window.__D = " + DATA + ";\n" + SHIM)
    await q.goto("http://127.0.0.1:8765/index.html?debug&r=9#714831.4,4332187.9,2.6")
    for i in range(80):
        await q.wait_for_timeout(300)
        if 'redrawn' in await q.inner_text('#plotNote'): break
    R = await q.evaluate("(() => { const r = document.getElementById('cv').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
    await q.mouse.click(R[0] + R[2] / 2, R[1] + R[3] / 2); await q.wait_for_timeout(600)
    await q.screenshot(path=SP + f'plots/full2_{name}.png', full_page=(vw < 600))
    await q.wait_for_timeout(500); await q.mouse.click(R[0] + R[2] / 2, R[1] + R[3] / 2); await q.wait_for_timeout(600)
    await q.evaluate("document.querySelector('aside').scrollTop = 0")
    await q.screenshot(path=SP + f'plots/full3_{name}.png')
    if False:
        t0 = time.time(); await q.click('#xGeo'); await q.wait_for_timeout(500); t1 = time.time(); await q.click('#xKmz'); await q.wait_for_timeout(500)
        for i in range(40):
            dl = await q.evaluate("window.__DL || []")
            if len(dl) >= 2: break
            await q.wait_for_timeout(500)
        print('downloads', dl, round(t1 - t0, 1), round(time.time() - t1, 1))
    print(name, '\n'.join(logs[:20]) or 'no page errors'); await q.close()
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        await run(b, 'light', 1400, 1000, 'light')
        await b.close()
asyncio.run(main())
