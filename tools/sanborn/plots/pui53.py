try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import asyncio, json
from playwright.async_api import async_playwright
SP = _ws.DATA
DATA = open(SP + 'plots/db_data_v53.json').read(); JSTS = open(_ws.CODE + 'jslib/package/dist/jsts.min.js').read()
SHIM = open(_ws.CODE + 'plots/ptest.py').read().split('SHIM = """')[1].split('"""')[0]
c = json.loads(DATA)['streets']['SB0595']['c']; A = c[105]; M = c[104]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); q = await b.new_page(viewport={"width": 1400, "height": 1100}); logs = []
        q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}")); q.on("console", lambda m: logs.append('CONSOLE ' + m.text) if m.type == 'error' else None)
        await q.route("**/cdn.jsdelivr.net/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=JSTS))
        await q.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=""))
        await q.add_init_script("window.__D = " + DATA + ";\n" + SHIM)
        await q.goto(f"http://127.0.0.1:8765/index.html?debug#{A[0]},{A[1]+20},3"); await q.wait_for_timeout(12000)
        def scr(pt):
            return q.evaluate(f"(() => {{ const v = window.__S.view, r = document.querySelector('canvas').getBoundingClientRect(); return [({pt[0]} - v.cx) * v.s + r.left + r.width/2, (v.cy - {pt[1]}) * v.s + r.top + r.height/2]; }})()")
        await q.click('#tEdit'); await q.wait_for_timeout(400)
        await q.evaluate("(() => { const S = window.__S; S.sel = { f: S.streetById.get('SB0595') }; })()"); await q.wait_for_timeout(300)
        pa = await scr(A); await q.mouse.click(pa[0], pa[1]); await q.wait_for_timeout(1500)
        print(await q.evaluate("JSON.stringify({sel: window.__S.sel && window.__S.sel.f.properties.id, rng: window.__S.rng})"))
        await q.screenshot(path=SP + 'plots/ui53a.png')
        await q.evaluate("(() => { const s = document.querySelector('input[type=range]'); s.value = s.max * 0.7; s.dispatchEvent(new Event('input')); s.dispatchEvent(new Event('change')); })()")
        await q.wait_for_timeout(15000); await q.screenshot(path=SP + 'plots/ui53b.png')
        print(await q.evaluate("JSON.stringify(window.__S.edits.streets.SB0595.jo)"))
        print('\n'.join(logs[:10]) or 'no errors'); await b.close()
asyncio.run(main())
