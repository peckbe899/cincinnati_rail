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
        await q.goto("http://127.0.0.1:8765/index.html?debug&r=3#714900,4332300,2")
        async def settle(word='plots', n=40):
            last = None
            for i in range(n):
                await q.wait_for_timeout(300); t = await q.inner_text('#plotNote')
                if t == last and t.endswith('.'): return t
                last = t
            return last
        print(await settle())
        R = await q.evaluate("(() => { const r = document.getElementById('cv').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
        async def view(cx, cy, s):
            await q.evaluate(f"(() => {{ __S.view.cx = {cx}; __S.view.cy = {cy}; __S.view.s = {s}; window.dispatchEvent(new Event('resize')); }})()"); await q.wait_for_timeout(300)
        def scr(x, y, cx, cy, s): return (R[0] + (x - cx) * s + R[2] / 2, R[1] + (cy - y) * s + R[3] / 2)
        sel = lambda: q.inner_text('#selBody')
        # a lot plot near the middle of OTR
        info = await q.evaluate("""(() => { const ps = __S.pl.plots.filter(p => p.properties.kind === 'lot' && p.area > 150 && p.area < 400 && Math.abs(p.bb[0] - 714900) < 120 && Math.abs(p.bb[1] - 4332300) < 120 && !p.properties.u0);
          const p = ps[0], r = p.geometry.coordinates[0], c = [r.reduce((a, q) => a + q[0], 0) / r.length, r.reduce((a, q) => a + q[1], 0) / r.length]; return { id: p.properties.id, c, bb: p.bb }; })()""")
        print('plot', info)
        cx, cy = info['c']; s = 3.0; await view(cx, cy, s)
        x, y = scr(cx, cy, cx, cy, s); await q.mouse.click(x, y); await q.wait_for_timeout(400)
        print('SEL1', (await sel())[:260].replace('\n', ' | '))
        await q.get_by_role('button', name='Commercial', exact=True).first.click(); await q.wait_for_timeout(400)
        print('SET C', (await sel())[:120].replace('\n', ' | '))
        await q.get_by_role('button', name='Split with a line').click(); await q.wait_for_timeout(200)
        bb = info['bb']; L = max(bb[2] - bb[0], bb[3] - bb[1]) + 10
        # drag a line across the middle, across the long axis
        w = bb[2] - bb[0]; h = bb[3] - bb[1]
        if w > h: a, c2 = (cx, cy + h), (cx, cy - h)
        else: a, c2 = (cx - w, cy), (cx + w, cy)
        x1, y1 = scr(a[0], a[1], cx, cy, s); x2, y2 = scr(c2[0], c2[1], cx, cy, s)
        await q.mouse.move(x1, y1); await q.mouse.down(); await q.mouse.move((x1 + x2) / 2, (y1 + y2) / 2); await q.mouse.move(x2, y2); await q.mouse.up()
        print(await settle())
        print('SPLIT', (await sel())[:200].replace('\n', ' | '))
        await q.screenshot(path=SP + 'plots/i_split.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        # merge the two halves back
        await q.get_by_role('button', name='Merge with neighbours').click(); await q.wait_for_timeout(200)
        other = await q.evaluate(f"(() => {{ const p = __S.pl.byId.get('{info['id']}.2'); const r = p.geometry.coordinates[0]; return [r.reduce((a, q) => a + q[0], 0) / r.length, r.reduce((a, q) => a + q[1], 0) / r.length]; }})()")
        x, y = scr(other[0], other[1], cx, cy, s); await q.mouse.click(x, y); print(await settle())
        print('MERGE', (await sel())[:200].replace('\n', ' | '))
        await q.keyboard.press('Escape'); await q.wait_for_timeout(200)
        # divide into 3
        await q.fill('#pDiv', '3'); await q.get_by_role('button', name='Divide along the street').click(); print(await settle())
        print('DIVIDE', (await sel())[:200].replace('\n', ' | '))
        await q.screenshot(path=SP + 'plots/i_divide.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        ops = await q.evaluate("JSON.stringify(__S.edits.plotOps)"); print('OPS', ops[:400])
        # undo three times
        for i in range(3): await q.click('#uUndo'); await q.wait_for_timeout(150)
        print(await settle()); print('UNDO3 ops', await q.evaluate("JSON.stringify(__S.edits.plotOps)"), 'plots edits', await q.evaluate("JSON.stringify(__S.edits.plots)"))
        # block: click twice to reach the block, set Residential for all
        x, y = scr(cx, cy, cx, cy, s); await q.mouse.click(x, y); await q.wait_for_timeout(700); await q.mouse.click(x, y); await q.wait_for_timeout(400)
        t = await sel(); print('BLOCK', t[:300].replace('\n', ' | '))
        if 'Land use for every plot' in t:
            await q.locator('.stop .btn.use', has_text='Residential').click(); await q.wait_for_timeout(400)
            print('BLOCK SET', (await sel())[:300].replace('\n', ' | '))
        await q.screenshot(path=SP + 'plots/i_block.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        await q.wait_for_timeout(1200)
        W = await q.evaluate("JSON.stringify(window.__W[window.__W.length - 1] ? { plots: window.__W[window.__W.length - 1].plots, plotOps: window.__W[window.__W.length - 1].plotOps, blocks: window.__W[window.__W.length - 1].blocks } : null)")
        print('SAVED', W[:600])
        print('\n'.join(logs[:30]) or 'no page errors'); await b.close()
asyncio.run(main())
