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
        b = await p.chromium.launch(); logs = []
        q = await b.new_page(viewport={"width": 1400, "height": 1000})
        q.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        q.on("console", lambda m: logs.append(f"{m.type}: {m.text}"[:300]) if m.type in ('error', 'warning') else None)
        await q.route("**/cdn.jsdelivr.net/**", lambda r: r.fulfill(status=200, content_type="application/javascript", body=JSTS))
        await q.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=""))
        await q.add_init_script("window.__D = " + DATA + ";\n" + SHIM)
        await q.goto("http://127.0.0.1:8765/index.html?debug&r=4#714900,4332300,2")
        async def settle(n=60, need=''):
            last = None
            for i in range(n):
                await q.wait_for_timeout(300); t = await q.inner_text('#plotNote')
                if t == last and t.endswith('.') and need in t: return t
                last = t
            return last
        print(await settle(need='redrawn')); print('STATS0', await q.evaluate('JSON.stringify(__S.pl.stats) + " ms " + __S.pl.ms'))
        R = await q.evaluate("(() => { const r = document.getElementById('cv').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
        async def view(cx, cy, s):
            await q.evaluate(f"(() => {{ __S.view.cx = {cx}; __S.view.cy = {cy}; __S.view.s = {s}; window.dispatchEvent(new Event('resize')); }})()"); await q.wait_for_timeout(300)
        def scr(x, y, cx, cy, s): return (R[0] + (x - cx) * s + R[2] / 2, R[1] + (cy - y) * s + R[3] / 2)
        sel = lambda: q.inner_text('#selBody')
        opens = await q.evaluate("__S.pl.open.map(o => [o.properties.id, Math.round(o.area), o.properties.q, o.properties.street])")
        print('OPEN', opens)
        oid, area, oq, ost = max(opens, key=lambda o: o[1])
        s = 2.5; await view(oq[0], oq[1], s)
        await q.screenshot(path=SP + 'plots/o_before.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        x, y = scr(oq[0], oq[1], oq[0], oq[1], s); await q.mouse.click(x, y); await q.wait_for_timeout(400)
        t = await sel(); print('OPEN SEL', t[:400].replace('\n', ' | '))
        btn = q.locator('#selBody .also .btn').first
        if await btn.count():
            await btn.click(); print(await settle()); print('ADDED', (await sel())[:200].replace('\n', ' | '))
            await q.screenshot(path=SP + 'plots/o_added.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
            await q.click('#uUndo'); print(await settle())
        x, y = scr(oq[0], oq[1], oq[0], oq[1], s); await q.mouse.click(x, y); await q.wait_for_timeout(400)
        await q.fill('#oDiv', '4'); await q.get_by_role('button', name='Divide into lots').click(); print(await settle())
        print('LOTS', (await sel())[:200].replace('\n', ' | '))
        await q.screenshot(path=SP + 'plots/o_lots.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        # drag a street point: pick New street W (S045) end, move it 30 m
        st = await q.evaluate("(() => { const f = __S.streetById.get('S045'); const e = __S.edits.streets['S045']; return e.c; })()")
        print('S045', st)
        p0 = st[0]; s = 1.5; await view(p0[0], p0[1] + 150, s)
        # select street by clicking its middle
        mid = [(st[0][0] * 0.9 + st[1][0] * 0.1), (st[0][1] * 0.9 + st[1][1] * 0.1)]
        await q.click('#tEdit'); x, y = scr(mid[0], mid[1], p0[0], p0[1] + 150, s); await q.mouse.click(x, y); await q.wait_for_timeout(400)
        print('ST SEL', (await sel())[:80].replace('\n', ' | '))
        x0, y0 = scr(p0[0], p0[1], p0[0], p0[1] + 150, s); t0 = time.time()
        await q.mouse.move(x0, y0); await q.mouse.down(); 
        for k in range(1, 11): await q.mouse.move(x0 + 3 * k * s, y0 - 4 * k * s); await q.wait_for_timeout(40)
        await q.mouse.up(); print(await settle(), round(time.time() - t0, 1), 's'); print('LOG', await q.evaluate('JSON.stringify(__S.plLog.slice(-8))'))
        await q.screenshot(path=SP + 'plots/s_drag.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        print('\n'.join(logs[:30]) or 'no page errors'); await b.close()
asyncio.run(main())
