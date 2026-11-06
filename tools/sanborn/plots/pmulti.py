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
        await q.goto("http://127.0.0.1:8765/index.html?debug&r=10#714831.4,4332187.9,2.6")
        async def settle(n=60, need=''):
            last = None
            for i in range(n):
                await q.wait_for_timeout(300); t = await q.inner_text('#plotNote')
                if t == last and t.endswith('.') and need in t: return t
                last = t
            return last
        print(await settle(need='redrawn'))
        R = await q.evaluate("(() => { const r = document.getElementById('cv').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
        V = [714831.4, 4332187.9, 2.6]
        async def view(cx, cy, s):
            V[:] = [cx, cy, s]; await q.evaluate(f"(() => {{ __S.view.cx = {cx}; __S.view.cy = {cy}; __S.view.s = {s}; window.dispatchEvent(new Event('resize')); }})()"); await q.wait_for_timeout(400)
        def scr(x, y): return (R[0] + (x - V[0]) * V[2] + R[2] / 2, R[1] + (V[1] - y) * V[2] + R[3] / 2)
        sel = lambda: q.inner_text('#selBody')
        mid = lambda pid: q.evaluate(f"(() => {{ const p = __S.pl.byId.get('{pid}'); const r = p.geometry.coordinates[0]; return [r.reduce((a, q) => a + q[0], 0) / r.length, r.reduce((a, q) => a + q[1], 0) / r.length]; }})()")
        # 1. shift-click two neighbouring plots
        a = await mid('SBB0256-005'); bb = await mid('SBB0256-006')
        x, y = scr(*a); await q.mouse.click(x, y); await q.wait_for_timeout(300)
        await q.keyboard.down('Shift'); x, y = scr(*bb); await q.mouse.click(x, y); await q.keyboard.up('Shift'); await q.wait_for_timeout(400)
        print('MULTI2', (await sel())[:300].replace('\n', ' | '))
        # 2. shift-drag a box over more plots in the same block
        await q.keyboard.down('Shift'); x1, y1 = scr(a[0] - 4, a[1] + 30); x2, y2 = scr(a[0] + 6, a[1] - 40)
        await q.mouse.move(x1, y1); await q.mouse.down(); await q.mouse.move((x1 + x2) / 2, (y1 + y2) / 2); await q.mouse.move(x2, y2); await q.screenshot(path=SP + 'plots/m_box.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915}); await q.mouse.up(); await q.keyboard.up('Shift'); await q.wait_for_timeout(500)
        t = await sel(); print('BOX', t[:400].replace('\n', ' | '))
        await q.screenshot(path=SP + 'plots/m_sel.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        await q.locator('#selBody .btn', has_text='Merge into').first.click(); print(await settle())
        print('MERGED', (await sel())[:240].replace('\n', ' | '))
        await q.screenshot(path=SP + 'plots/m_merged.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        print('OPS', await q.evaluate("JSON.stringify(__S.edits.plotOps)"))
        # 3. streets: Dalton SB0630 + SB0633
        await view(713035, 4332230, 1.4); await q.keyboard.press('Escape')
        x, y = scr(713028, 4332080); await q.mouse.click(x, y); await q.wait_for_timeout(300); print('S1', (await sel())[:60].replace('\n', ' | '))
        await q.keyboard.down('Control'); x, y = scr(713038.5, 4332276); await q.mouse.click(x, y); await q.keyboard.up('Control'); await q.wait_for_timeout(400)
        t = await sel(); print('S2', t[:500].replace('\n', ' | '))
        await q.locator('#selBody .btn', has_text='Merge into').first.click(); print(await settle())
        print('SMERGED', (await sel())[:500].replace('\n', ' | '))
        print('EDITS', await q.evaluate("JSON.stringify({a: __S.edits.streets['SB0630'], b: __S.edits.streets['SB0633']}).slice(0, 600)"))
        await q.screenshot(path=SP + 'plots/m_street.png', clip={"x": 8, "y": 85, "width": 1043, "height": 915})
        await q.get_by_role('button', name='Unmerge').click(); print(await settle())
        print('UNMERGED', await q.evaluate("JSON.stringify({a: __S.edits.streets['SB0630'] || null, b: __S.edits.streets['SB0633'] || null})"))
        # 4. Ben's W 8th pieces SB0992 + SB0994 (overlapping)
        await q.evaluate("(() => { const a = __S.streetById.get('SB0994'), b = __S.streetById.get('SB0992'); __S.multi = null; })()")
        plan = await q.evaluate("(() => { return null; })()")
        await q.keyboard.press('Escape')
        print('\n'.join(logs[:20]) or 'no page errors'); await b.close()
asyncio.run(main())
