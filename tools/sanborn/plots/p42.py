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
        q.on("console", lambda m: logs.append(f"CONSOLE {m.type}: {m.text}") if m.type == 'error' else None)
        await q.route("**/cdn.jsdelivr.net/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=JSTS))
        await q.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=""))
        await q.add_init_script("window.__D = " + DATA + ";\n" + SHIM)
        async def goto(X, Y, s, tag):
            await q.goto(f"http://127.0.0.1:8765/index.html?debug&r={tag}#{X},{Y},{s}"); await q.wait_for_timeout(5500)
        async def click_world(X, Y):
            pt = await q.evaluate(f"(() => {{ const r = document.getElementById('cv').getBoundingClientRect(), v = __S.view; return [r.left + r.width / 2 + ({X} - v.cx) * v.s, r.top + r.height / 2 - ({Y} - v.cy) * v.s]; }})()")
            await q.mouse.click(pt[0], pt[1]); await q.wait_for_timeout(600)
            return (await q.inner_text('#selBody'))[:700].replace('\n', ' | ')
        shot = lambda nm: q.screenshot(path=SP + f'plots/v_c42_{nm}.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        await goto(702400, 4325600, 0.45, 'a'); await shot('term')
        print('stations cvx', await q.evaluate("__S.sf.filter(f => f.properties.sys === 'cvx').map(f => f.properties.name + ':' + f.properties.stops.map(s => s.type0 + '/' + s.L + '/o0=' + Math.round(s.o0) + '/lat=' + s.lat0.toFixed(1)).join(','))"))
        await goto(702620, 4325420, 1.1, 'b'); await shot('t24')
        print('click T2 dot ->', await click_world(702688.8, 4325308.6))
        # island
        btn = q.locator('#selBody .seg button', has_text='Island').first; await btn.click(); await q.wait_for_timeout(500)
        print('after island:', (await q.inner_text('#selBody'))[:160].replace('\n', ' | '))
        await shot('t2_island')
        # move with the range: 60 m one way
        rg = q.locator('#selBody input.offrange').first
        await rg.evaluate("(el) => { el.value = '60'; el.dispatchEvent(new Event('input')); el.dispatchEvent(new Event('change')); }"); await q.wait_for_timeout(500)
        print('after move:', (await q.inner_text('#selBody'))[:260].replace('\n', ' | '))
        await shot('t2_moved')
        print('edits', await q.evaluate("JSON.stringify(__S.edits.stations)"))
        # delete T4
        print('click T4 dot ->', (await click_world(702572.6, 4325547.4))[:120])
        await q.locator('#selBody button', has_text='Delete station').click(); await q.wait_for_timeout(500); await shot('t4_deleted')
        print('edits', await q.evaluate("Object.keys(__S.edits.stations)"))
        await goto(701700, 4326072, 0.9, 'c'); await shot('t1')
        await goto(702000, 4325600, 0.15, 'd'); await shot('cvg')
        print('\n'.join(logs) or 'no page errors'); await b.close()
asyncio.run(main())
